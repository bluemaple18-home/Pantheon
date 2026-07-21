# Gemini Reviewer transport design repair 001

status: `DELIVERED_CANDIDATE`

這不是 `GO`。新 candidate 必須送回原 Reviewer thread 固定 SHA 重新審查；不授權 merge、push、deploy、publish 或恢復 production 內容線。

## Corpus result

- External CLI Reviewer process invocations：精確 6。
- REJECT corpus：3/3 exit、strict parse、schema、rubric、verdict consistency 全部通過。
- APPROVE corpus：3/3 exit、strict parse、schema、rubric、verdict consistency 全部通過。
- Retry：未執行；沒有第 7 個 Reviewer process。
- Provider model calls：`unobservable/unknown`。不得宣稱上限或精確值。
- Sanitized receipts：`matrix.json`；未保存 prompt、raw response、stderr payload、秘密或本機絕對路徑。

## Finding closure mapping

1. Duplicate keys：`json.loads(..., object_pairs_hook=...)` 在每層 object 檢查 pairs，重複時回 `STRICT_JSON_DUPLICATE_KEY`，不採後值、不修補。
2. APPROVE interface：`findings` structural schema 允許空陣列；rubric 只接受 `APPROVE + false + []` 或 `REJECT + true + non-empty`。
3. Invocation claim：移除 `model_calls/call_budget`；改用 `external_cli_process_invocations=6`、`external_cli_process_budget=6` 與 `provider_model_calls=unobservable/unknown`。
4. Blank message：schema 拒絕 empty string，rubric 以 trim 後非空驗證 code/message。

## Root cause

原 probe 混合 structural schema 與單一 REJECT 代表案例的 rubric，導致合法 APPROVE 無法表示；同時使用 permissive JSON object materialization，並把外層 process counter 誤命名為 model-call counter。修復把四層責任拆清：pairs-level parse、structural schema、cross-field deterministic rubric、observable-only accounting。
