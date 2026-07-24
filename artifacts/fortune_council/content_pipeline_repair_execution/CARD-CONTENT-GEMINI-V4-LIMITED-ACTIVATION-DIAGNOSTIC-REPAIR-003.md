# CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-DIAGNOSTIC-REPAIR-003

- card_id: `CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-DIAGNOSTIC-REPAIR-003`
- chain_id: `CONTENT-GEMINI-V4-LIMITED-ACTIVATION-DIAGNOSTIC-REPAIR-003`
- ownership: `v4_safe_schema_diagnostics_only`
- strictness: `strict`
- risk: `high`
- status: `DELIVERED_CANDIDATE`
- decision: `READY_FOR_REVIEW`

## 基準

- structured-envelope Repair-2:
  `bccd800ebf06348449d718c33036ad1c712dbef7`
- structured-envelope Review-2:
  `534b50dff98b0f836a83889d32b807211fe3377d`
- Activation-003 blocked evidence:
  `3249ce87546f4c17659f40a944ac47bdeac6b802`
- blocked job:
  `35b808faa055a70ba92d40f5186535de6ea5590f`

## 已知事實

- agy／Gemini target process 恰好執行一次並以 `SUCCESS` 結束。
- Durable replay 為 `COMPLETE / 1`，exactly-once ledger／anchor 契約正常。
- Structured envelope 已讓真實輸出從前一輪 `JSON_INVALID` 前進到
  `SCHEMA_MISMATCH`。
- 現有 closed diagnostic 只保存分類，無法定位是哪個 schema path 或 validator
  keyword 不符。
- Activation-003 不得重送；本卡不得呼叫 Gemini／agy。

## 可證偽假說

1. 若 blocker 是可局部修正的欄位型別／必填欄位差異，加入 bounded、
   allowlisted 的 schema error keyword 與 JSON path 後，synthetic mismatch
   應能在不保存值的前提下精確定位。
2. 若 validator 本身沒有可安全抽取的結構化錯誤，本修正不得猜測或保存 raw
   response；應維持 `SCHEMA_MISMATCH` 並封閉為空 diagnostics。
3. 若新增 diagnostics 可能洩漏任意 schema key／instance value，privacy RED
   必須失敗，production 不得接受該設計。

## 目標

- 在正確 validation seam 增加最小、bounded、closed 的 schema mismatch
  diagnostics，只允許：
  - 固定 validator keyword allowlist
  - 只含 array index 或已在 response schema `properties`／`items` 中定義的 path
  - 固定最大錯誤數、path 深度與字串長度
- 不保存 instance value、raw response、prompt、stdout／stderr、credential、
  完整 environment 或任意 validator message。
- Runner failed record 只能持久化通過 closed sanitizer 的 diagnostics。
- 維持 flag-on fail-closed／no legacy fallback、flag-off legacy 與 exactly-once
  ledger／anchor／replay 契約。

## 可修改

- `scripts/agy_gemini_v4_broker.py`
- `scripts/agy_gemini_runner.py`
- `tests/test_agy_gemini_v4_broker.py`
- `tests/test_agy_gemini_outbox.py`
- 本卡
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_limited_activation_diagnostic_repair_003/**`

## 禁止

- 不修改 SEO pipeline、publisher、文章、registry、metadata、sitemap、feed、
  prerender、automation、登入、憑證或全域 CLI 設定。
- 不保存或輸出 prompt、raw stdout／stderr、response body、instance value、
  credential、完整 environment 或任意 validator message。
- 不呼叫 Gemini／agy，不 retry 前次 job，不建立新真實 payload。
- 不修改 response schema 或 structured envelope；本卡只建立安全診斷能力。
- 不 push、deploy、publish、activation、default promotion 或 legacy removal。
- 不重寫 broker。

## 執行

1. 以 CodeGraph 定位 result validation 與 failed-record persistence seam。
2. 先補 RED：定位 keyword／path、未知 key、instance value、超長／過深／過多錯誤、
   forged diagnostics 與非 mismatch 結果。
3. 做最小 production 修正，一次只驗證一個假說。
4. 跑 focused tests、完整 V4 affected matrix、privacy scan、py_compile 與
   `git diff --check`。
5. 建立單一 Repair-3 candidate commit，交獨立 Review；Review GO 前不得規劃新
   canary。

## Evidence

`artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_limited_activation_diagnostic_repair_003/`

必須包含：

- `root-cause.md`
- `red-green.txt`
- `verification.txt`
- `changed-files.txt`
- `decision.md`

## 交付

只能：

- `DELIVERED_CANDIDATE / READY_FOR_REVIEW`
- `BLOCKED`

本卡不授權真實外呼。

## 執行結果

- CodeGraph initial index:
  `129 files / 2154 nodes / 4482 edges / up to date`
- initial diagnostics RED:
  `4 failed`
- initial diagnostics GREEN:
  `4 passed`
- bounded array-index RED／GREEN:
  `1 failed -> 1 passed`
- broker／runner focused:
  `76 passed`
- final V4 matrix:
  `102 passed`
- legacy:
  `57 passed`
- coordinator／publisher／web:
  `74 passed / 2 existing warnings`
- unique affected total:
  `233 passed`
- production schema path coverage:
  `safe token names / observed maximum depth 6 < limit 8`
- prompt／raw stdout／stderr／response value retained:
  `false`
- Gemini／agy invocation during repair:
  `0`
- decision:
  `DELIVERED_CANDIDATE / READY_FOR_REVIEW`

本候選只建立下一筆 schema mismatch 的安全定位能力，不代表 V4 已打通、可放量、
可成為預設 transport 或可移除 legacy。獨立 Review GO 前不得建立新 canary。
