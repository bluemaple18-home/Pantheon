from __future__ import annotations

from typing import Any

from app.ai.report import UnifiedReport


SYSTEM_PROMPT = """你是一個謹慎的命理分析助理。請把傳統術數結果視為文化解讀，不做醫療、法律、投資或重大人生決策承諾。"""


def build_interpretation_prompt(
    user_data: dict[str, Any],
    charts: dict[str, Any],
    report: UnifiedReport | None = None,
    school_policy: dict[str, Any] | None = None,
) -> str:
    """把多個算力結果組裝成單一 AI 解盤提示詞。"""
    sections = [
        SYSTEM_PROMPT,
        "",
        "輸出規則：",
        "- 每個結論都必須追溯到 report.signals 或 report.combo_cards。",
        "- 固定使用：命盤訊號 -> 組合牌 -> 白話翻譯 -> 適合/不適合 -> 建議。",
        "- 禁止直接說「你很適合某某」而不交代依據。",
        "- 必須遵守 metadata.school_policy；只能說「依本次算法設定」，不可說成唯一正統答案。",
        "- 不可自行重排命盤、補未計算的神煞/吉凶表，或把候選旺衰寫成唯一用神。",
        "- MBTI / 64 分支人格只可視為個人自評偏好與溝通語言，不可寫成心理診斷或固定人格命令。",
        "- MBTI low_margin 維度必須降級描述為情境彈性，不可當成強結論。",
        "",
        "使用者資料：",
        f"- 姓名：{user_data.get('name') or '未提供'}",
        f"- 生日：{user_data.get('birth_date')}",
        f"- 時間：{user_data.get('birth_time')}",
        f"- 性別：{user_data.get('gender')}",
        f"- 時區：{user_data.get('timezone')}",
        "",
        "排盤資料：",
    ]
    for name, chart in charts.items():
        sections.append(f"## {name}")
        sections.append(str(chart))
    if report:
        sections.extend(["", "統一語法報告資料：", str(report.model_dump(mode="json"))])
    if school_policy:
        sections.extend(["", "本次算法設定 metadata.school_policy：", str(school_policy)])
    sections.extend(
        [
            "",
            "請輸出：",
            "1. 命盤重點摘要",
            "2. 八字與紫微交叉觀察",
            "3. 需要更多資料才能判定的地方",
            "4. 溫和、可行的行動建議",
        ]
    )
    return "\n".join(sections)
