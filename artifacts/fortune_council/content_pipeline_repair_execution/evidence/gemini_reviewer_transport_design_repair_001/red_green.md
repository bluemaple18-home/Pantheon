# Repair 001 red-green evidence

## Red

- 測試檔：`tests/test_agy_gemini_transport_probe.py`
- 結果：`6 failed, 5 passed`
- Duplicate keys：top-level verdict 與 nested finding code 均被舊 parser 錯誤接受。
- APPROVE interface：`APPROVE + false + []` 被舊 schema 的 `minItems` 錯誤拒絕。
- Blank message：空字串與純空格均被舊 rubric 錯誤接受。
- Invocation accounting：舊 matrix 實際建立 9 rows，且只提供不可成立的 `model_calls/call_budget` 欄位。

第一次直接呼叫全域 `pytest` 因指令不存在，未進入測試；上述 red 結果由既有 project venv 執行，未安裝任何套件。

## Green

- 受影響測試：`15 passed in 0.02s`。
- `py_compile scripts/agy_gemini_transport_probe.py`：PASS。
- Duplicate keys 由 pairs-level hook 在任一 object depth fail closed。
- Structural schema 允許空 findings；deterministic rubric 強制 APPROVE/REJECT 雙向交叉條件。
- Empty message 由 `minLength` 拒絕；trim 後空白由 rubric 拒絕。
- Matrix 固定 2 corpora × 3 fresh Reviewer processes，並分離外部 process 與不可觀測 provider call 計數。
