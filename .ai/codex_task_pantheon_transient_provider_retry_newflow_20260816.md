# Pantheon 暫時性 provider 失敗有界自動重試

- 目標：同一已授權 run 遇到 Gemini 429／503 時，自動建立新 transport attempt。
- 邊界：最多沿用既有 2 次 retry；429 仍由 credential pool cooldown 控制；API_QUOTA、AUTH、MODEL_UNAVAILABLE 維持終止。
- 可改：`scripts/agy_gemini_outbox.py`、`tests/test_agy_gemini_outbox.py` 與必要交付證據。
- 禁止：重用已消耗 job identity、重複 publish、放寬 publication fail-closed。
- 驗收：429／503 retry 測試、quota 終止測試、受影響測試、`git diff --check`；部署後續跑原 correlation 到完整鏈路或明確 retry budget exhausted。
