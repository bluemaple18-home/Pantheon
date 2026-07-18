# CARD-CONTENT-GEMINI-REWRITE-BATCH-002｜Candidate evidence

## Preflight 與來源

- source HEAD：`8c9dc6b97e138f278babbc3cdcc417a6d1a142ba`
- 開始時 worktree / staged index：乾淨
- 開始時 `index.lock`：不存在
- audit commit：`00d13eb51c1ffbc19572f8378fac7090da93765d`
- audit queue blob 與目前 queue blob：皆為 `d896fe0b81e9390f9b7ed85f84ff7726647f9739`
- Batch 2 五篇 ID、slot、順序、serial、slug、title、primaryKeyword、`GEMINI_REWRITE` verdict 與 issue codes：已由 strict prepare gate 鎖定

## Gemini 執行

- Writer：`gemini-3.5-flash` / Gemini 3.5 Flash Low
- Reviewer：`gemini-3.1-pro-preview` / Gemini 3.1 Pro Low
- Attempt 1：5 個 fresh sandboxed headless Writer process，各只收到單篇 public brief 與該篇 variation contract；1 個 fresh Gemini Pro Reviewer 同時審五篇
- Attempt 1：五篇皆 REJECT；deterministic quality findings 5、uniqueness findings 2
- Internal repair：只重跑 Attempt 1 的五篇 REJECT；5 個 fresh sandboxed headless Writer process
- Attempt 2：1 個 fresh Gemini Pro Reviewer 同時審五篇
- internal repair 使用量：1 / 1；未啟動第 3 輪
- 總計 Writer processes：10；Reviewer processes：2
- 未安裝、未登入、未修改工具設定；operation receipts 不含 prompt 明文或金鑰

## Final candidate

- 固定順序：`THEME-INTERPERSONAL-04`、`THEME-CAREER-05`、`THEME-LIFE-05`、`THEME-WEALTH-05`、`THEME-INTERPERSONAL-05`
- 正文字數：1432、1449、1564、1428、1408
- candidate SHA-256：`fe56a986d1dfb9c1c6180e4da9eb88c752224805a7e5a5c04e5781b6a6066e2b`
- identity 與 current-body SHA：相對 brief 全部不變
- deterministic quality findings：1（`THEME-WEALTH-05` 缺少第 3 個不同具體行動動詞）
- uniqueness / abstract-pattern findings：2（`THEME-CAREER-05` 與 `THEME-INTERPERSONAL-05` 共用 `not_but_frame` 抽象句型）
- Reviewer：2 APPROVE / 3 REJECT
- APPROVE：`THEME-INTERPERSONAL-04`、`THEME-LIFE-05`
- REJECT：`THEME-CAREER-05`、`THEME-WEALTH-05`、`THEME-INTERPERSONAL-05`
- approval：未建立
- apply / 正式正文 / registry / metadata / prerender / sitemap / feed / redirects / deploy / publish：均未執行

## Acceptance

- status：`BLOCKED`
- blocker：唯一 internal repair 額度已用完，最終 deterministic findings 非 0 且 Gemini Pro Reviewer 僅 2/5 APPROVE
- next step：需新的明確授權與新 repair card；本卡不得再重跑
