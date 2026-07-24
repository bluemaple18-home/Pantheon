# CARD-CONTENT-GEMINI-V4-MAINLINE-REPAIR-001

status: DELIVERED_CANDIDATE
owner: Gemini V4 Mainline Repair-1 Engineer
source_thread: `019f8d25-e23b-7ac2-ac3f-894574bc49ec`
canonical_review_thread: `019f8d89-a3dd-7011-875d-22e8799cc773`
review_commit: `16a5a9c9dc4af8099650fb3b6106772b2093dcba`
review_verdict: `NO_GO`
repair_generation: `1/2`
routing: `strict/high`
model: `gpt-5.6-sol high`

## 固定 identity

- base：`ea7308bf14533c22bc83809bd72faeddcdeed6d0`
- candidate／啟動 HEAD：`6c4931c1da63257cd70bd0abe5776dc1758e4557`
- candidate 唯一 parent：`ea7308bf14533c22bc83809bd72faeddcdeed6d0`
- Repair 只關閉 canonical Review 的固定 P1／P2；不得新增 finding、重置 chain、回原 implementation、換 Reviewer或自審 GO。

## 固定 findings

### P1 `P1_CANARY_BINDING_EVIDENCE`

舊 `real-canary.json` 只有摘要，fresh Reviewer 無法驗證 operation／item／attempt／request／model／profile／executable identity、closed receipt、result schema、canonical ledger/control、ledger SHA與 final anchor 的同一性。

修復契約：

- 先建立 RED verifier，舊 summary 必須 rejected。
- evidence-owned recorder/verifier 不保存 runtime prompt、credential、完整環境或 CLI log。
- 新 bundle 必須包含 closed receipt、redacted canonical ledger frames、control metadata、inbox/result schema與 executable identity。
- verifier 必須離線重算 ledger hash、hash-chain anchor、event schema/order/count及 receipt/binding/digest/result schema/no-fallback。
- wrong operation/item/attempt/request/model/profile/digest、broken chain、partial ledger、duplicate event、wrong anchor、wrong result schema皆 fail closed。
- 不得以人工補摘要變綠。

### P2 `P2_RACE_ANCHOR_ERROR_CONTRACT`

public `run_single_shot` 的 `FileExistsError` concurrent-create race branch 遇 malformed、wrong-binding或 unreadable anchor 時會逸出 `AnchorError`。

修復契約：

- 先建立 deterministic RED。
- 最小修正只捕捉 race branch 的 `AnchorError`。
- 回傳 `INVALID/UNKNOWN + EXTERNAL_ANCHOR_INVALID`。
- caller false、result none、resend false、target spawn 0、無 legacy fallback。
- 禁止重寫 broker。

## Allowlist

- `artifacts/fortune_council/content_pipeline_repair_execution/CARD-CONTENT-GEMINI-V4-MAINLINE-REPAIR-001.md`
- `scripts/agy_gemini_v4_broker.py`
- `tests/test_agy_gemini_outbox.py`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_repair_001/**`

## Forbidden

- runner、architecture probe、broker tests、architecture probe tests、docs、app。
- implementation evidence、fixed Review evidence、文章、registry、metadata、sitemap、feed、prerender。
- 依賴與設定。
- retry、fallback、merge、push、deploy、publish、切預設或恢復內容線。
- 真實 canary 未獲主卡明確授權前不得執行；失敗不得 retry/fallback。

## Verification

依序執行：

1. P1 舊 summary rejection RED，再 recorder/verifier與 mutation matrix GREEN。
2. P2 public `run_single_shot` deterministic RED，再最小 GREEN。
3. synthetic rehearsal。
4. focused tests。
5. canonical Reviewer 27-test selector。
6. `py_compile`。
7. privacy scan、allowlist檢查、`[DBG-` 清除檢查與 `git diff --check`。

## Evidence

root：`artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_repair_001/`

required：

- `root-cause.md`
- `red-green.txt`
- `canary-recorder.py`
- `canary-verifier.py`
- `synthetic-verifier-matrix.json`
- `verification.txt`
- `changed-files.txt`
- `decision.md`

取得授權後另含：

- `real-canary-bundle.json`
- `real-canary-verification.json`

## External canary gate

external_canary_authorization: `AUTHORIZED_AND_CONSUMED`
current_gate: `READY_FOR_RE_REVIEW`

離線準備全綠後必須停在 `BLOCKED / EXTERNAL_CANARY_AUTHORIZATION`，列出最終工具、模型、公開 payload 摘要、預期影響與唯一一次命令契約。只有主卡 follow-up 明確授權後，才可最多一次呼叫真實 `agy 1.1.5` canary；任何失敗不重試、不 fallback。

## Delivery

交付狀態只允許：

- `DELIVERED_CANDIDATE / READY_FOR_RE_REVIEW`
- `BLOCKED`

獲授權完成 canary後建立單一 Repair candidate commit，回報完整 SHA、changed files、RED/GREEN、test counts、canary與剩餘風險。原 Reviewer thread 負責 re-review與關 finding。
