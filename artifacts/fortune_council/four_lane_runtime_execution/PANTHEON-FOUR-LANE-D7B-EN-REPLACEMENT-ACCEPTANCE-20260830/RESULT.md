# D7B EN replacement production acceptance

## 裁決

`BLOCKED_ZERO_MUTATION_LEGACY_BRIEF_VALIDATION_GAP`

正式 actor `d7b09a99bd006544dd703a49f4ce774d32554c66`、generation
`g74-d7b09a99-exact-replacement-repair-20260830` 已核對。只針對 source run
`auto-i18n-en-aa637e1bf05d3ad21429` 執行 exact replacement plan-only；未執行
replacement、normal coordinator cycle、runner、provider 或 publisher。

## Exact authority

- source registry canonical digest（含 canonical JSON 尾端換行）：
  `7b98f9c9eb11f32bce7768046dcd48a51c4ca4c4edd9f28dfae8b8bbf736cff8`
- source run dir：
  `/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue/translation-runs/auto-i18n-en-aa637e1bf05d3ad21429`
- source status：`failed`
- source error：`LocalePlanValidationError`
- source brief file SHA-256：
  `bcd31d23f5d8455ea21fea205827afd267a29f4c4533b0064a80154fbd8d12f3`
- expected replacement：
  `auto-i18n-en-aa637e1bf05d3ad21429-replacement-01`

## Plan-only 結果

使用正式 `scripts.agy_gemini_coordinator replace-failed-translation-run` exact
入口、exact run id、registry digest、run dir、repo root 與 queue root。

結果：

```json
{"status":"rejected","error":"translation brief fields are strict"}
```

production 0.3.368 brief 的欄位為：
`articles, lane, mode, run_id, schema_version`，其中 `lane=i18n-rewrite`。D7B exact
replacement preflight 直接將這份 legacy brief 交給 strict validator，因此在任何寫入前
拒絕；此入口未沿用既有 trusted registry-bound legacy brief compatibility seam。

## Mutation seal

- replacement run dir：不存在
- replacement registry：不存在
- replacement execute：0
- runner／provider／publisher：0
- normal coordinator cycle：0
- 四 lane outbox／processing：全部 0
- KO／JA mutation：0
- service load：0
- source／test 修改：0

依任務契約的任何 drift 即停止條件，本驗收不開 RCA、不開 Repair、不放寬 validator。
