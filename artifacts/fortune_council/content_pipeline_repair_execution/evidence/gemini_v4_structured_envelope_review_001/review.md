# Gemini V4 Structured-envelope Independent Review

## Findings

### [P2] Validated outbox task 加上 envelope 後可超過 broker prompt 上限

- path／line:
  `scripts/agy_gemini_runner.py:145`
- related contract:
  `scripts/agy_gemini_outbox.py:22` 允許 raw task 到 256 KiB；
  `scripts/agy_gemini_v4_broker.py:570` 將完整 effective prompt 上限設為 256 KiB。
- 觸發:
  建立一筆 prompt bytes 正好為 `262144`、schema 合法且公開的 external request。
  Outbox validation 接受該 request；runner 再加入 role、policy 與 canonical schema
  後，effective prompt 成為 `262509` bytes。
- 證據:
  直接 broker validation 回報 `agy prompt size is invalid`；end-to-end
  `process_once` 將原本有效 request 寫成 `failed / ValueError`，ledger 不存在，
  legacy call 維持 0。
- 風險:
  Candidate 將一部分符合既有 outbox public payload contract 的 request 變成
  flag-on transport failure。Request 已從 queue claim 並 archive，無法以同一
  identity 正常完成。
- 建議:
  在 request 建立／驗證前，以與 production 相同的 deterministic renderer 計算
  effective UTF-8 bytes，對 combined task＋schema＋envelope 套用共享上限；補
  最大可接受值、超一 byte、large schema 與 multibyte task regression。不可只在
  runner claim 後才失敗。

## Spec axis

- Activation-002 durable evidence 是 `COMPLETE/1/PROCESS_TERMINAL=SUCCESS` 加
  `JSON_INVALID`；broker／ledger exactly-once 正常。
- Candidate 修補的 runner adapter defect 可由 RED-capable capture 重現：舊路徑
  只傳 user task，新路徑傳 closed structured envelope。
- Writer／reviewer role instruction 正確且互斥。
- No-tool／no-workspace、single JSON object、no-code-fence、canonical compact
  schema 與 sanitized task exact bytes 均通過。
- CommandFrame 綁 effective prompt digest／byte count；receipt 綁 original
  external request SHA，兩個 digest distinct 且同時成立。
- Size contract 不完整，因此 Spec axis 不通過。

## Standards axis

- Flag-off 完全 bypass V4 renderer。
- Flag-on failure 維持 fail-closed 與 no legacy fallback。
- Candidate 未修改 broker、ledger、anchor、replay、publisher、文章、registry
  或 automation production code。
- Schema insertion order、nested property order與含 newline 的 schema string
  均 deterministic；newline 在 canonical JSON string 內被 escape。
- Unknown role fail closed；writer/reviewer instructions 不互相滲入。
- Production diff 沒有新增 prompt、raw stdout／stderr、response body、
  credential 或完整環境持久化。

## Remaining risk

即使 size finding 修復，synthetic envelope tests 仍不能證明真實 agy 一定遵守
structured instructions。此 H3 只能由另行授權的新 canary 驗證，本 Review 不授權
第三次真實外呼。

## Review 結論

有 `1 x P2`，因此不是 GO。

Verdict:
`DELIVERED_CANDIDATE / NO_GO`
