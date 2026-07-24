# Decision

status: `DELIVERED_CANDIDATE / READY_FOR_RE_REVIEW`

P1與P2的離線修復、synthetic rehearsal、mutation controls及受影響 tests均已轉綠。依 Repair卡
治理契約取得主卡明確授權後，唯一一次真實 agy/Gemini canary已成功；離線 verifier重算
closed receipt、command/control、canonical ledger、ledger SHA、final anchor、inbox/result schema
與 executable binding均通過。

## 已消耗的唯一外部 canary

- 工具：既有本機 Antigravity `agy 1.1.5`
- 授權 executable identity：SHA-256
  `6509d6ca54a66e3eaf61dfe35308ba1dfa1e6b552ef5c4f5f861562c6811ecaf`
- 模型：`gemini-3.5-flash`，對應 `Gemini 3.5 Flash (Low)`
- profile：`antigravity_cli_v1`
- payload：固定公開 synthetic canary指令，只要求回傳
  `{"ok": true, "transport": "agy-v4-mainline-repair-canary"}` 的 closed JSON；不含文章、
  私有路徑、credential或內部資料。
- 預期影響：一個 target process、最多一次外部 generation；不登入、不改 credential/config、
  不寫文章、不 publish、不 retry、不 fallback。
- 實際結果：`COMPLETE/1`、五個 canonical events、一個 `EXEC_CONFIRMED`、strict schema PASS。
- executable SHA：
  `6509d6ca54a66e3eaf61dfe35308ba1dfa1e6b552ef5c4f5f861562c6811ecaf`
- ledger SHA：
  `ce52cc41e295f8a9bd88835a892d11e130f6dea8a1703998e85d1a33404cc49d`
- final anchor：
  `d2130f32d3d88c0d9f0b5b39f4b7cf15e4ec9731db04833265362a5d7ce1b601`
- 外部 generation總數：1；授權已消耗，不得再呼叫。

未自審 GO；原 Reviewer thread負責 re-review與關 finding。
