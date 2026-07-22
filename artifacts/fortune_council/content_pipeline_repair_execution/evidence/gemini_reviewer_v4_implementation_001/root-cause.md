# Gemini Reviewer V4 implementation｜Root cause

## Root question

既有 `scripts/agy_gemini_runner.py:process_once` 直接呼叫 legacy `generate_json(...)`。該路徑沒有 broker-owned durable ledger、exec-confirmed process accounting、external anchor CAS 或 replay-only fail-closed boundary，因此不能可靠區分 preflight 0、exec failure 0、confirmed 1 與 crash-window `UNKNOWN`。

## Implementation boundary

- 新增單一 production entrypoint `scripts.agy_gemini_v4_broker:run_single_shot`。
- runner 僅在 `AGY_GEMINI_V4_BROKER=1` 時切入 broker；其他值維持 legacy 單次 callsite。
- broker 是唯一 ledger writer 與 target launcher；coordinator parent 只建立 FD、執行 external anchor `load/compare_and_swap`，不寫 ledger event。
- target 只收到 raw public prompt stdin，argv 只有 executable，環境為空，且固定 `close_fds=True`、`pass_fds=()`。
- 既有 ledger 一律 replay，不啟動 target、不補 event、不自動重送。

## Fail-closed decision

只有 `COMPLETE/1/SUCCESS`、receipt 完整綁定 operation/item/attempt/request/model，且 stdout JSON 符合 caller schema 時，runner 才寫 inbox。其餘狀態與 caller-contract mismatch 都寫 failed record並 archive；不呼叫 legacy generator。

## Known baseline issue

全套測試的兩個紫微 provider assertions 在未修改的 `ef5b813` archive 也同樣失敗：環境回傳 `pantheon_ziwei`，測試期望 `iztro`。此問題不在本卡 allowlist，未修改。
