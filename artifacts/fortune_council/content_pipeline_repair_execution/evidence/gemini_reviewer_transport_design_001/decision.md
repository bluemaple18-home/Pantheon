# Gemini Reviewer transport design 001｜Decision

## Status

`GO_GEMINI_CLI_MACHINE_GATE`

這是 architecture candidate GO，不是 production recovery GO。未修改、整合或啟用任何正式 pipeline。

## Facts

- CLI capability 已驗證：版本、binary SHA-256、兩個明確 model label 均記錄於 `matrix.json`。
- 模型呼叫：3 configurations × 3 fresh processes = 9，等於卡片上限，沒有第 10 次。
- 三組皆達成 3/3：CLI exit 0、strict JSON parse、schema validation、rubric validation。
- 九次 verdict/hard-failure 都一致為 `REJECT / true`。
- Probe 未保存 raw response、prompt、stderr、秘密或本機絕對路徑。

## Interpretation

Gemini CLI 在 bounded sanitized case 上適任 machine-gate candidate。推薦 `minimal_mapper_pro_low`，因其在相同成功率下縮小模型輸出責任，並讓 deterministic mapper 只搬移已驗證 judgment。Baseline 成功不能消除歷史長 prompt／深 schema 風險，因此不建議直接恢復現況 nested transport。

## Waiting conditions

- Gate 4：獨立 Reviewer 審查固定 candidate commit。
- 新 implementation chain 實作 interface 並擴大 sanitized corpus。
- Corpus 未過前，三條內容線維持停止。
