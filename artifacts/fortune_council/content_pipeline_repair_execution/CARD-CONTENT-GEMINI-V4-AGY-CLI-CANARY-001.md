---
card_id: CARD-CONTENT-GEMINI-V4-AGY-CLI-CANARY-001
chain_id: CONTENT-GEMINI-V4-AGY-CLI-CANARY-001
status: CARD_DRAFTED
role: canary_executor
ownership: exactly_once_external_canary
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 真實外部model呼叫、exactly-once、無retry且需驗證production runner／broker／trusted executable邊界
integrated_base_sha: f2008e42c40c13e6f089d3b912be6621f432fa3d
reviewed_candidate_sha: 5740ed7670d69e0866a77d599c4a4cd341bfd608
reviewer_thread_id: 019f8cad-92ed-7993-8584-285e70214202
review_verdict: GO
executable: ~/.antigravity/bin/agy
executable_version: 1.1.5
executable_sha256: 6509d6ca54a66e3eaf61dfe35308ba1dfa1e6b552ef5c4f5f861562c6811ecaf
model_id: gemini-3.5-flash
model_label: Gemini 3.5 Flash (Low)
max_external_calls: 1
allowlist:
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_agy_cli_canary_001/**
forbidden_scope:
  - scripts/**, tests/**, docs/**, app/** and all production code/config
  - articles, registry, metadata and publishing files
  - second call, retry, fallback or alternate model
  - private/unpublished content, credentials or local paths in external prompt
  - merge, push, deploy, publish or content-line recovery
verification:
  - executable version and SHA-256 match before call
  - one deterministic outbox request and one process_once invocation
  - ledger replay COMPLETE/1 and inbox result matches strict schema
  - no failed record, no second EXEC_CONFIRMED, no retry/fallback
  - evidence contains hashes/status/count only; no credential or private payload
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_agy_cli_canary_001/
worktree_path: PENDING
cwd: PENDING
main_cwd: <repo-root>
thread_id: PENDING
thread_status: CARD_DRAFTED
---

# Gemini V4 agy CLI｜Exactly-once 真實 Canary

## 外部工具 Gate

- Service：既有本機 Antigravity `agy` CLI；不安裝、不登入、不修改 credential/config。
- Operation：`external_generation`，一次模型用量；使用者已在得知 `GO → 單次真實 Gemini canary` 後明確要求繼續。
- Connection：只用既有本機登入狀態；只傳 closed allowlist environment，不讀、不複製、不記錄憑證。
- Target：`gemini-3.5-flash` → `Gemini 3.5 Flash (Low)`。
- Stop rule：呼叫開始後，任何 nonzero、timeout、JSON/schema、ledger/replay、receipt或inbox失敗都立即 `BLOCKED`，不得第二次呼叫。

## 唯一公開 payload

Prompt（精確文字）：

```text
你是傳輸層 canary。只回傳單一 JSON 物件，不要 Markdown、說明或其他欄位。ok 必須是 true；transport 必須是字串 agy-v4-canary。精確格式：{"ok":true,"transport":"agy-v4-canary"}
```

Schema：

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "ok": {"type": "boolean", "enum": [true]},
    "transport": {"type": "string", "enum": ["agy-v4-canary"]}
  },
  "required": ["ok", "transport"]
}
```

## 執行契約

1. 使用 operation-local temporary queue，先以 `create_external_request` 建立一個 deterministic outbox job。
2. 設定 `AGY_GEMINI_V4_BROKER=1`、實際 executable與固定 trusted SHA-256。
3. 只呼叫一次 `process_once`；禁止 `drain`、loop、retry或例外後再送。
4. 保存 job/request/prompt/schema SHA、runner status、ledger event types、replay status/process count、inbox result與 CLI exit outcome；不得保存 credential或 CLI 私密 log。
5. 成功只表示 trusted executable 的 transport completion；不宣稱可獨立證明供應商內部 model call provenance。

## 交付狀態

- 成功：`CANARY_GO`，附唯一 job ID、ledger `COMPLETE/1`、strict inbox result、worktree clean。
- 任一失敗：`BLOCKED_NO_RETRY`，附一次 attempt 的非敏感證據；不得自行修 code、重送或改模型。
