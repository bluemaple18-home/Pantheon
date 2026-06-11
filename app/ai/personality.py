from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from app.ai.report import UnifiedReport


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
AI_CORE_ENV_FILES = [
    Path.home() / ".config" / "ai-core" / "legacy_review.env",
    Path.home() / ".config" / "ai-core" / "env.sh",
]


def generate_personality_interpretation(chart: dict[str, Any], report: UnifiedReport) -> dict[str, Any]:
    """Generate a bounded personality reading from questionnaire evidence."""
    fallback = _local_interpretation(chart)
    if chart.get("status") not in {"scored", "scored_core"}:
        return {
            **fallback,
            "mode": "local_fallback",
            "provider": "none",
            "reason": "insufficient_personality_scores",
        }
    if os.environ.get("PANTHEON_PERSONALITY_AI", "1").strip().lower() in {"0", "false", "off"}:
        return {
            **fallback,
            "mode": "local_fallback",
            "provider": "none",
            "reason": "disabled_by_env",
        }

    keys = _load_gemini_keys()
    if not keys:
        return {
            **fallback,
            "mode": "local_fallback",
            "provider": "none",
            "reason": "missing_gemini_key",
        }

    prompt = _build_prompt(chart, report)
    model = os.environ.get("PANTHEON_PERSONALITY_GEMINI_MODEL") or os.environ.get("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
    errors = []
    for key in keys:
        try:
            payload = _call_gemini(key, model, prompt)
            return {
                **_normalize_ai_payload(payload, fallback),
                "mode": "gemini",
                "provider": "gemini",
                "model": model,
                "reason": "generated_from_questionnaire_evidence",
            }
        except Exception as error:  # noqa: BLE001 - keep endpoint resilient.
            errors.append(type(error).__name__)

    return {
        **fallback,
        "mode": "local_fallback",
        "provider": "gemini",
        "model": model,
        "reason": "gemini_unavailable",
        "errors": errors[:3],
    }


def _load_gemini_keys() -> list[str]:
    keys = _split_keys(os.environ.get("GEMINI_API_KEYS") or os.environ.get("GEMINI_API_KEY") or "")
    for env_file in AI_CORE_ENV_FILES:
        if env_file.exists():
            keys.extend(_keys_from_env_file(env_file))
    deduped = []
    for key in keys:
        if key and key not in deduped:
            deduped.append(key)
    return deduped


def _keys_from_env_file(path: Path) -> list[str]:
    keys: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, raw_value = line.split("=", 1)
        name = name.replace("export ", "").strip()
        if name in {"GEMINI_API_KEY", "GEMINI_API_KEYS"}:
            keys.extend(_split_keys(raw_value))
    return keys


def _split_keys(value: str) -> list[str]:
    clean = value.strip().strip('"').strip("'")
    return [item.strip() for item in clean.split(",") if item.strip()]


def _build_prompt(chart: dict[str, Any], report: UnifiedReport) -> str:
    evidence = {
        "type": chart.get("type"),
        "core_type": chart.get("core_type"),
        "branch_code": chart.get("branch_code"),
        "answer_count": chart.get("answer_count"),
        "dimensions": chart.get("dimensions", {}),
        "signals": [signal.model_dump(mode="json") for signal in report.signals if signal.system == "mbti"],
        "combo_cards": [card.model_dump(mode="json") for card in report.combo_cards],
    }
    return "\n".join(
        [
            "你是繁體中文人格測驗顧問。只根據輸入的問卷統計 evidence 解讀，不可宣稱心理診斷。",
            "語氣要像真人顧問，具體、克制、不要 AI 腔，不要玄學化。",
            "請輸出 JSON object，格式固定：",
            '{"summary":"一段 70 字內摘要","sections":[{"title":"決策風格","body":"..."},{"title":"互動模式","body":"..."},{"title":"壓力反應","body":"..."},{"title":"工作節奏","body":"..."},{"title":"盲點提醒","body":"..."}],"advice":["...","...","..."],"limitations":"一句限制聲明"}',
            "每個 body 40 到 80 字。advice 3 條，每條 24 字內。",
            "輸入 evidence：",
            json.dumps(evidence, ensure_ascii=False),
        ]
    )


def _call_gemini(key: str, model: str, prompt: str) -> dict[str, Any]:
    url = GEMINI_ENDPOINT.format(model=urllib.parse.quote(model, safe="")) + f"?key={urllib.parse.quote(key)}"
    body = {
        "systemInstruction": {
            "parts": [{"text": "輸出必須是 JSON，不要 markdown，不要多餘說明。"}],
        },
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.55,
            "responseMimeType": "application/json",
        },
        "store": False,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    timeout = float(os.environ.get("PANTHEON_PERSONALITY_AI_TIMEOUT", "12"))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")[:300]
        raise RuntimeError(f"Gemini HTTP {error.code}: {detail}") from error

    text = _extract_gemini_text(response_payload)
    return json.loads(text)


def _extract_gemini_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        raise ValueError("Gemini response missing candidates")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(str(part.get("text", "")) for part in parts).strip()
    if not text:
        raise ValueError("Gemini response missing text")
    return text


def _normalize_ai_payload(payload: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    sections = payload.get("sections")
    if not isinstance(sections, list):
        sections = fallback["sections"]
    normalized_sections = []
    for item in sections[:5]:
        if isinstance(item, dict):
            normalized_sections.append(
                {
                    "title": str(item.get("title") or "解讀"),
                    "body": str(item.get("body") or ""),
                }
            )
    advice = payload.get("advice")
    if not isinstance(advice, list):
        advice = fallback["advice"]
    return {
        "summary": str(payload.get("summary") or fallback["summary"]),
        "sections": normalized_sections or fallback["sections"],
        "advice": [str(item) for item in advice[:3]],
        "limitations": str(payload.get("limitations") or fallback["limitations"]),
    }


def _local_interpretation(chart: dict[str, Any]) -> dict[str, Any]:
    dimensions = chart.get("dimensions", {})
    labels = [
        str(item.get("preferred_label") or item.get("preferred") or key)
        for key, item in dimensions.items()
        if isinstance(item, dict) and item.get("preferred")
    ]
    type_label = chart.get("type") or chart.get("core_type") or "未定型"
    summary = f"你的自評結構目前偏向 {type_label}；主要訊號落在{_join_labels(labels)}。"
    return {
        "summary": summary,
        "sections": [
            {
                "title": "決策風格",
                "body": "你比較適合把問題拆成可判斷的訊號，再決定下一步；低信心軸向仍建議保留彈性。",
            },
            {
                "title": "互動模式",
                "body": "這份結果只反映問卷偏好，不代表固定人格；真正互動仍會受情境、關係與壓力影響。",
            },
            {
                "title": "工作節奏",
                "body": "可先用目前高分偏好安排節奏，再觀察哪些場合會讓你明顯耗能或卡住。",
            },
        ],
        "advice": ["先驗證高分軸向", "低分軸不要寫死", "用情境修正判斷"],
        "limitations": "此結果為自我探索，不是心理診斷。",
    }


def _join_labels(labels: list[str]) -> str:
    if not labels:
        return "尚未形成足夠偏好"
    return "、".join(labels[:6])
