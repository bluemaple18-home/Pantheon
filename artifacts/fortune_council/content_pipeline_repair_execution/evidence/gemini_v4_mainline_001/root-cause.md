# Root cause

## Current production truth

- Source of truth：目前 source branch commit `ea7308bf14533c22bc83809bd72faeddcdeed6d0`。
- Production opt-in：只有 `AGY_GEMINI_V4_BROKER=1` 會讓 `scripts.agy_gemini_runner.process_once` 呼叫 `scripts.agy_gemini_v4_broker.run_single_shot`；flag off 維持 legacy `generate_json`。
- Production profile：runner 固定選 `antigravity_cli_v1`，要求 deployment-provided executable SHA-256，且只接受 profile、digest、operation、request、model 全綁定的 receipt。
- CLI identity：既有本機 binary 自報 `agy 1.1.5`；唯讀 `--help` 顯示非互動介面是 `--print <prompt>`。目前檔案 SHA-256 為 `6509d6ca54a66e3eaf61dfe35308ba1dfa1e6b552ef5c4f5f861562c6811ecaf`。
- Baseline：`uv run --frozen pytest tests/test_agy_gemini_v4_broker.py tests/test_agy_gemini_outbox.py tests/test_agy_gemini_v4_architecture_probe.py -q` 為 `68 passed`。

## 舊 evidence 判定

可採信：

- `gemini_v4_agy_cli_compatibility_001` 已用 fake CLI 證明 closed argv、model mapping、empty stdin、environment/FD allowlist 與 privacy preflight。
- `gemini_v4_agy_cli_compatibility_repair_001` 已用 public seams 證明 production profile/digest binding、verified executable snapshot、post-fork cleanup 與 receipt provenance。
- 現行 source tests 可重現 strict replay legal table、partial/binding/hash-chain/anchor rejection、success/nonzero/timeout 與 flag-on no-fallback。

過期或不足：

- 舊 compatibility evidence 明確未執行真實 Gemini；不能證明目前 binary 的 runtime completion。
- 舊 verification 的 test count、base commit 與 isolated-worktree dependency 狀態不是目前 source branch 的驗證結果。
- 舊 canary 卡只是執行契約，不是 durable canary evidence。
- 舊 evidence 沒有 deterministic concurrent-create duplicate control，也沒有本卡要求的單一 synthetic matrix artifact。

## 排序假說

1. Concurrent-create loser 在 `FileExistsError` 分支以競爭後載入的 anchor 做 replay，卻把競爭前的 `existing_anchor` 放進 `BrokerResult.final_anchor`。若競爭前無 anchor、競爭後 ledger/anchor 已完整，結果可能是 `COMPLETE/1` 但 `final_anchor=null`。
2. 真實 `agy` snapshot 或 closed environment 仍可能與 `agy 1.1.5` runtime 不相容；version/help 只能證明 parser identity，不能證明 transport completion。
3. 若假說 1 被否證，production code 可能不需修改，剩餘缺口只在 matrix 與真實 canary evidence。

## 唯一目前 blocker

已以 public `run_single_shot` seam 建立 deterministic concurrent-create RED。重現結果是 replay 為 `COMPLETE/1`，但 `BrokerResult.final_anchor` 為 `null`；實際 durable external anchor 則是非空 SHA-256。根因是 `FileExistsError` 分支以競爭後載入值 replay，卻把競爭前的 stale `existing_anchor` 傳給 `_failure_result`。

最小修正讓 replay 與結果共用同一個 `replay_anchor`。單一測試由 RED 轉 GREEN，完整 focused suite 由 baseline `68 passed` 變為 `69 passed`；補上 malformed-output control 後 synthetic acceptance matrix 為 `21 passed`。

唯一真實 `agy 1.1.5` canary 隨後得到 durable `COMPLETE/1`、一個 `EXEC_CONFIRMED`、strict schema結果與無 failed record。技術 blocker 已解除；尚存治理邊界是獨立 Review、shadow run 與另立 migration commit，因此本卡不切預設、不放量。
