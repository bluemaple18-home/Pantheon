#!/usr/bin/env python3
"""CARD-CONTENT-GEMINI-USER-FIT-REVIEW-001 evidence builder."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

for parent in Path(__file__).resolve().parents:
    if (parent / "scripts" / "agy_gemini_outbox.py").exists():
        sys.path.insert(0, str(parent))
        break

from scripts import agy_seo_copy_pipeline as pipeline
from scripts.agy_gemini_outbox import build_external_request, create_external_request


EVIDENCE_ROOT = Path("artifacts/fortune_council/content_rewrite_execution/evidence/gemini_user_fit_review_001")
QUEUE_ROOT = Path(".work/gemini-runner")
RUN_ID = "gemini_user_fit_review_001"
REVIEWER_MODEL = pipeline.DEFAULT_REVIEWER_MODEL
WRITER_MODEL = pipeline.DEFAULT_WRITER_MODEL
MAX_BATCH = 5


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def body_text(body: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for section in body or []:
        heading = str(section.get("heading") or "")
        paragraphs = [str(value) for value in section.get("paragraphs") or []]
        chunks.extend([heading, *paragraphs])
    return "\n".join(value for value in chunks if value)


def body_sha(body: list[dict[str, Any]]) -> str:
    return hashlib.sha256(_json_bytes(body)).hexdigest()


def load_runtime_inventory(repo_root: Path) -> list[dict[str, Any]]:
    script = """
import { getArticlePath, listArticleRecords } from './app/web/static/article-registry.js';
import { buildArticleContent } from './app/web/static/article-meta.js';
const origin = 'https://mysticpantheon.com';
const rows = listArticleRecords().map((record) => {
  const canonicalPath = getArticlePath(record);
  const content = buildArticleContent(canonicalPath, origin, {});
  return {
    id: record.id,
    product: record.product,
    section: record.section,
    serial: record.serial,
    slug: record.urlSlug,
    canonicalPath,
    title: record.title,
    primaryKeyword: record.primaryKeyword,
    description: record.description,
    answer: record.answer,
    faq: record.faq,
    tags: record.tags,
    published: content.published,
    updated: content.updated,
    bodySections: content.bodySections || []
  };
});
console.log(JSON.stringify(rows));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    rows = json.loads(result.stdout)
    rows.sort(key=lambda item: (serial_number(str(item.get("serial") or "")), str(item.get("product") or ""), str(item.get("id") or "")))
    return rows


def serial_number(serial: str) -> int:
    match = re.search(r"(\d+)$", serial)
    return int(match.group(1)) if match else 999999


def infer_user_context(row: dict[str, Any], text: str) -> dict[str, str]:
    product = str(row.get("product") or "")
    keyword = str(row.get("primaryKeyword") or row.get("title") or "")
    title = str(row.get("title") or "")
    path = str(row.get("canonicalPath") or "")
    if product == "tarot":
        role = "正在用塔羅整理感情、工作或選擇卡點的一般讀者"
        situation = f"搜尋「{keyword}」時，通常想先知道這張牌或問法能不能回答眼前問題。"
        real_question = "這個塔羅線索現在能提醒我什麼，哪些結論不能只靠單篇文章決定？"
    elif product == "personality":
        role = "想用 MBTI 或人格分類理解自己與互動模式的一般讀者"
        situation = f"搜尋「{keyword}」時，多半想快速對照自己或某段關係，而不是讀理論課。"
        real_question = "這個人格概念能幫我看見哪種偏好，哪些地方不能當成固定標籤？"
    elif product == "astrology":
        role = "用星盤或星座落點理解情緒、關係或生活節奏的一般讀者"
        situation = f"搜尋「{keyword}」時，想知道星盤語言和生活情境怎麼連起來。"
        real_question = "這個星座或行星落點能說明哪一層，哪些不能推成命運結論？"
    elif product == "fortune":
        role = "想用命盤、八字或紫微整理人生課題的一般讀者"
        situation = f"搜尋「{keyword}」時，想先搞懂單一概念可看什麼，不想被玄學術語淹沒。"
        real_question = "這個命盤概念能提供哪個觀察角度，哪些仍要回到完整個人資料？"
    else:
        role = "正在用 Pantheon 公開文章整理生活問題的一般讀者"
        situation = f"搜尋「{keyword or title}」時，想快速找到和自己狀況相關的整理方式。"
        real_question = "我現在卡住的是哪一層，讀完後下一步可以先確認什麼？"
    quick_answer = "YES" if keyword and keyword in text[:160] and len(str(row.get("answer") or "")) <= 55 else "PARTIAL"
    next_step = "把問題改寫成一句具體情境，分清楚當下狀態、可觀察線索與不能代表的限制。"
    if "/wealth/" in path:
        next_step = "先分清收入、支出、風險感與安全感，不把文章當成投資建議。"
    if "/love/" in path:
        next_step = "先分清是在等回覆、怕失去、想復合，還是不確定要不要繼續。"
    return {
        "user_role": role,
        "search_situation": situation,
        "real_question": real_question,
        "quick_answer": quick_answer,
        "natural_tone": "PENDING_GEMINI_REVIEW",
        "actionable_next_step": next_step,
    }


def heuristic_issues(row: dict[str, Any], text: str) -> list[str]:
    issues: list[str] = []
    keyword = str(row.get("primaryKeyword") or "")
    if keyword and keyword not in text[:180]:
        issues.append("SEARCH_INTENT_LAG")
    if len(text) < 1200:
        issues.append("SHORT_BODY")
    headings = [str(section.get("heading") or "") for section in row.get("bodySections") or []]
    joined_headings = " / ".join(headings)
    if re.search(r"真正要整理的是什麼|有哪些可觀察線索|變成下一步|不能代表什麼", joined_headings):
        issues.append("TEMPLATE_STRUCTURE")
    if re.search(r"核心不是找一句立刻生效的答案|公開文章能提供整理框架|先把問題縮小", text):
        issues.append("REPEATED_BATCH_COPY")
    verbs = re.findall(r"等訊息|守住|補作品集|談分工|收尾|試探|拒絕|停下來|核對|記錄|比較|拆開|詢問|觀察|回覆", text)
    if len(set(verbs)) < 3:
        issues.append("LOW_SCENARIO_DENSITY")
    if re.search(r"全面解析|深度解析|不可或缺|賦能|總而言之|值得注意的是|必看|保證|注定", text):
        issues.append("BANNED_PHRASE")
    return issues or ["NONE"]


def preliminary_verdict(issues: list[str]) -> str:
    if issues == ["NONE"]:
        return "KEEP"
    serious = {"SEARCH_INTENT_LAG", "SHORT_BODY", "TEMPLATE_STRUCTURE", "REPEATED_BATCH_COPY"}
    if len(serious.intersection(issues)) >= 2:
        return "GEMINI_REWRITE"
    return "HUMAN_LIGHT_EDIT"


def make_inventory(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, row in enumerate(rows, start=1):
        key = (str(row["id"]), str(row["product"]), str(row["slug"]))
        duplicate = key in seen
        seen.add(key)
        text = body_text(row["bodySections"])
        context = infer_user_context(row, text)
        issues = heuristic_issues(row, text)
        verdict = preliminary_verdict(issues)
        if duplicate:
            verdict = "BLOCKED"
            issues = ["DUPLICATE_ID_PRODUCT_SLUG"]
        inventory.append(
            {
                "row": index,
                "id": row["id"],
                "product": row["product"],
                "section": row.get("section", ""),
                "serial": row["serial"],
                "slug": row["slug"],
                "canonical_path": row["canonicalPath"],
                "title": row["title"],
                "primary_keyword": row["primaryKeyword"],
                "body_chars": len(text),
                "body_sha256": body_sha(row["bodySections"]),
                "old_baseline_verdict": "BASELINE_ONLY_NOT_EVIDENCE",
                "new_verdict": "BLOCKED_EXTERNAL_REVIEW_PENDING",
                "preliminary_verdict": verdict,
                "issue_codes": "|".join(issues),
                **context,
                "batch": f"reviewer_batch_{((index - 1) // MAX_BATCH) + 1:03d}",
            }
        )
    return inventory


def write_inventory_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def reviewer_schema() -> dict[str, Any]:
    finding = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"code": {"type": "string"}, "evidence": {"type": "string"}},
        "required": ["code", "evidence"],
    }
    article = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "slot": {"type": "string"},
            "verdict": {"type": "string", "enum": ["KEEP", "HUMAN_LIGHT_EDIT", "GEMINI_REWRITE", "BLOCKED"]},
            "evidence": {"type": "array", "items": finding, "minItems": 2, "maxItems": 6},
            "reason": {"type": "string"},
        },
        "required": ["slot", "verdict", "evidence", "reason"],
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {"articles": {"type": "array", "items": article, "minItems": 1, "maxItems": 5}},
        "required": ["articles"],
    }


def public_review_prompt(batch: list[dict[str, Any]], source_rows: dict[str, dict[str, Any]]) -> str:
    articles = []
    for index, item in enumerate(batch, start=1):
        source = source_rows[str(item["id"])]
        sections = source["bodySections"]
        articles.append(
            {
                "slot": f"article-{index:02d}",
                "identity": {
                    "id": item["id"],
                    "product": item["product"],
                    "slug": item["slug"],
                    "serial": item["serial"],
                    "title": item["title"],
                    "primaryKeyword": item["primary_keyword"],
                    "canonicalPath": item["canonical_path"],
                },
                "userFit": {
                    "userRole": item["user_role"],
                    "searchSituation": item["search_situation"],
                    "realQuestion": item["real_question"],
                    "quickAnswer": item["quick_answer"],
                    "actionableNextStep": item["actionable_next_step"],
                    "preliminaryIssueCodes": item["issue_codes"].split("|"),
                },
                "currentBodySections": sections,
            }
        )
    return "\n".join(
        [
            "你是 Pantheon 公開文章使用者適配 Reviewer。請逐篇輸出 KEEP / HUMAN_LIGHT_EDIT / GEMINI_REWRITE / BLOCKED。",
            "判斷讀者角色、搜尋情境、真正問題、是否快速回答、口吻是否像真人、讀完是否知道下一步。",
            "非 KEEP 至少兩項文章專屬證據；不得只寫模板感、不夠口語或泛泛評論。",
            "檢查：搜尋意圖延遲、真人口吻、模板句、空泛段落、過度抽象、重複骨架、可行下一步、危險或過度斷言。",
            "只輸出 JSON；slot 必須逐字複製。",
            "public articles:",
            json.dumps({"articles": articles}, ensure_ascii=False),
        ]
    )


def build_reviewer_outbox(repo_root: Path, evidence_root: Path, inventory: list[dict[str, Any]], source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    receipts_dir = evidence_root / "receipts"
    source_by_id = {str(row["id"]): row for row in source_rows}
    receipts: list[dict[str, Any]] = []
    for batch_index in range(0, len(inventory), MAX_BATCH):
        batch_no = batch_index // MAX_BATCH + 1
        batch = inventory[batch_index : batch_index + MAX_BATCH]
        namespace = f"ufit001_review_{batch_no:03d}"
        prompt = public_review_prompt(batch, source_by_id)
        schema = reviewer_schema()
        request = build_external_request(
            namespace=namespace,
            role="reviewer",
            model=REVIEWER_MODEL,
            prompt=prompt,
            response_schema=schema,
        )
        create_external_request(repo_root / QUEUE_ROOT, namespace=namespace, role="reviewer", model=REVIEWER_MODEL, prompt=prompt, response_schema=schema)
        receipt = {
            "batch": batch_no,
            "role": "reviewer",
            "model": REVIEWER_MODEL,
            "status": "pending_external_runner",
            "job_id": request["job_id"],
            "request_sha256": request["request_sha256"],
            "prompt_sha256": request["prompt_sha256"],
            "schema_sha256": request["schema_sha256"],
            "response_sha256": None,
            "article_ids": [item["id"] for item in batch],
        }
        write_json(receipts_dir / f"reviewer-batch-{batch_no:03d}.json", receipt)
        receipts.append(receipt)
    return receipts


def write_queue(path: Path, inventory: list[dict[str, Any]]) -> None:
    queued = [item for item in inventory if item["preliminary_verdict"] == "GEMINI_REWRITE"]
    lines = [
        "# Gemini Queue",
        "",
        "Status: BLOCKED_EXTERNAL_REVIEW_PENDING. Only Gemini Reviewer can promote items into final GEMINI_REWRITE writer queue.",
        "",
        "| Batch | ID | Product | Slug | Public brief | Immutable fields | User need | Evidence |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in queued:
        evidence = item["issue_codes"].replace("|", ", ")
        lines.append(
            f"| {item['batch']} | `{item['id']}` | {item['product']} | `{item['slug']}` | {item['primary_keyword']} | id/product/serial/slug/title/metadata unchanged | {item['real_question']} | {evidence} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_audit(path: Path, inventory: list[dict[str, Any]], receipts: list[dict[str, Any]]) -> None:
    preliminary = Counter(item["preliminary_verdict"] for item in inventory)
    final = Counter(item["new_verdict"] for item in inventory)
    issues = Counter(code for item in inventory for code in item["issue_codes"].split("|"))
    lines = [
        "# Gemini User Fit Review 001 Audit",
        "",
        f"- status: BLOCKED_EXTERNAL_REVIEW_PENDING",
        f"- generated_at: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- runtime_inventory_rows: {len(inventory)}",
        f"- unique_id_product_slug: {len({(i['id'], i['product'], i['slug']) for i in inventory})}",
        f"- reviewer_outbox_jobs: {len(receipts)}",
        f"- writer_jobs: 0",
        f"- body_apply: 0",
        "",
        "## Verdict Distribution",
        "",
        "| Verdict | Count |",
        "|---|---:|",
    ]
    for key, value in sorted(final.items()):
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Preliminary Local Triage", "", "| Verdict | Count |", "|---|---:|"])
    for key, value in sorted(preliminary.items()):
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Issue Signals", "", "| Issue | Count |", "|---|---:|"])
    for key, value in issues.most_common():
        lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "Reviewer jobs were created through the sanitized outbox with SHA-bound requests, but no Gemini response was available yet. Per card contract, Gemini candidates are not replaced by Codex judgment; all current final verdicts remain BLOCKED_EXTERNAL_REVIEW_PENDING and no Writer run or body apply was executed.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_apply_verification(path: Path, inventory: list[dict[str, Any]]) -> None:
    payload = {
        "schema_version": 1,
        "status": "NO_APPLY_BLOCKED_EXTERNAL_REVIEW_PENDING",
        "article_count": len(inventory),
        "applied_count": 0,
        "metadata_drift": 0,
        "articles": [
            {
                "id": item["id"],
                "product": item["product"],
                "slug": item["slug"],
                "original_body_sha256": item["body_sha256"],
                "candidate_body_sha256": None,
                "formal_body_sha256": item["body_sha256"],
                "metadata_invariant": True,
                "applied": False,
            }
            for item in inventory
        ],
    }
    write_json(path, payload)


def write_browser_summary(path: Path, inventory: list[dict[str, Any]]) -> None:
    products: dict[str, dict[str, Any]] = {}
    for item in inventory:
        products.setdefault(str(item["product"]), item)
    selected = list(products.values())[:5]
    payload = {
        "status": "NOT_RUN_NO_BROWSER_RUNTIME_IN_THIS_EVIDENCE_STEP",
        "required_representatives": 5,
        "selected_representatives": [
            {
                "id": item["id"],
                "product": item["product"],
                "path": item["canonical_path"],
                "desktop": "pending browser verification after Gemini review/apply",
                "mobile": "pending browser verification after Gemini review/apply",
            }
            for item in selected
        ],
    }
    write_json(path / "browser-acceptance.json", payload)


def write_verification(path: Path, inventory: list[dict[str, Any]], receipts: list[dict[str, Any]]) -> None:
    changed_allowlist = [
        "artifacts/fortune_council/content_rewrite_execution/evidence/gemini_user_fit_review_001/**",
    ]
    lines = [
        "status=BLOCKED_EXTERNAL_REVIEW_PENDING",
        f"inventory_rows={len(inventory)}",
        f"unique_id_product_slug={len({(i['id'], i['product'], i['slug']) for i in inventory})}",
        f"reviewer_request_receipts={len(receipts)}",
        "writer_request_receipts=0",
        "applied_bodies=0",
        "deterministic_findings=not_run_no_candidate",
        "uniqueness_findings=not_run_no_candidate",
        "metadata_drift=0",
        "browser=not_run_no_candidate_apply",
        "git_diff_check=pending",
        "affected_pytest=pending",
        "changed_file_allowlist=" + ",".join(changed_allowlist),
        "",
        "repro:",
        "python artifacts/fortune_council/content_rewrite_execution/evidence/gemini_user_fit_review_001/tools/user_fit_review_001.py build --repo-root .",
        "python -m scripts.agy_gemini_runner --queue-root .work/gemini-runner process-once",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(repo_root: Path) -> None:
    evidence_root = repo_root / EVIDENCE_ROOT
    evidence_root.mkdir(parents=True, exist_ok=True)
    rows = load_runtime_inventory(repo_root)
    inventory = make_inventory(rows)
    write_inventory_csv(evidence_root / "inventory.csv", inventory)
    receipts = build_reviewer_outbox(repo_root, evidence_root, inventory, rows)
    write_queue(evidence_root / "gemini_queue.md", inventory)
    write_audit(evidence_root / "audit.md", inventory, receipts)
    write_apply_verification(evidence_root / "apply-verification.json", inventory)
    write_browser_summary(evidence_root / "browser", inventory)
    write_verification(evidence_root / "verification.txt", inventory, receipts)
    write_json(
        evidence_root / "summary.json",
        {
            "schema_version": 1,
            "status": "BLOCKED_EXTERNAL_REVIEW_PENDING",
            "run_id": RUN_ID,
            "inventory_rows": len(inventory),
            "unique_id_product_slug": len({(i["id"], i["product"], i["slug"]) for i in inventory}),
            "reviewer_outbox_jobs": len(receipts),
            "writer_outbox_jobs": 0,
            "applied_bodies": 0,
            "inventory_sha256": sha256_text((evidence_root / "inventory.csv").read_text(encoding="utf-8")),
        },
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "build":
        build(args.repo_root.resolve())
        return 0
    raise ValueError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
