# CARD-CONTENT-GEMINI-REWRITE-BATCH-001-REPAIR-001｜Repair candidate evidence

## Preflight

- source HEAD：`274cad03fb760a25f6baa10ae31f4391a073ce08`
- worktree / staged index：開始時乾淨
- index.lock：不存在
- 前卡 exact finding：五篇皆只有 `TEMPLATE_USAGE`，內容為跨篇句型或結構相似
- 前卡 deterministic findings：0

## Isolated Gemini operation

- Writer：`gemini-3.5-flash` / Gemini 3.5 Flash Low
- Reviewer：`gemini-3.1-pro-preview` / Gemini 3.1 Pro Low
- 每個 Writer process 只收到單篇 public brief、該篇 finding 與專屬 variation contract
- Attempt 1：5 個 fresh sandboxed Writer process + 1 個 fresh independent Reviewer process
- Internal repair：只重跑 4 篇 REJECT 候選，共 4 個 fresh sandboxed Writer process
- Attempt 2：1 個新的 fresh independent Reviewer process 同時審查五篇
- internal repair 使用量：1 / 1；未執行第 3 輪
- 未安裝、未登入、未修改工具設定；receipts 不含 prompt 明文或金鑰

## Final candidate

- 固定順序：`MBTI-BASE-01`、`THEME-LIFE-03`、`THEME-INTERPERSONAL-03`、`THEME-LIFE-04`、`THEME-WEALTH-04`
- 正文字數：1421、1472、1432、1408、1449
- identity、immutable fields 與 current-body SHA：相對前卡 brief 全部不變
- 完整句、共用 H2、24-char long n-gram、段落前 10 字聚合檢查：0 finding
- Reviewer：3 APPROVE / 2 REJECT
- `MBTI-BASE-01`：第 5 節第 2 段 89 字，低於 90 字下限
- `THEME-LIFE-03`：命中禁詞「保證」
- approval：未建立
- apply / 正式正文 / metadata / registry / deploy / publish：均未執行

## Acceptance

- status：`BLOCKED`
- blocker：唯一一次 internal repair 後仍有 2 個 deterministic findings
- remaining allowance：0
- candidate、review、兩輪 external outputs、operation receipts 與 findings 均保存在本目錄
