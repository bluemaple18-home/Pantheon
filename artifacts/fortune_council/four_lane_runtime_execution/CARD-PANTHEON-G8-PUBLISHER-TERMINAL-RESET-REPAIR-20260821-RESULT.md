---
id: CARD-PANTHEON-G8-PUBLISHER-TERMINAL-RESET-REPAIR-20260821-RESULT
card_id: CARD-PANTHEON-G8-PUBLISHER-TERMINAL-RESET-REPAIR-20260821
status: delivered_candidate
---

# Publisher terminal reset repair RESULT

## 結論

已補上正式 `--reset-publisher-activation-only` 入口，處理 Publisher one-shot terminal 後留下 normal/absent、其他六服務仍為 activation-only 的混合狀態。此入口只替換與 bootstrap Publisher；其他六服務只讀驗證，不做 mutation。

## 根因

既有 `--activate-publisher-only` 會把 live Publisher 換成 normal one-shot plist，但 child terminal 後沒有正式復位 seam。下一次 Capacity preactivation 要求七個 live plist 全為 activation-only，因此必然以 `plist activation mode mismatch` fail-closed；aggregate `--activate-only` 又需要尚未能建立的 Capacity stage，形成循環依賴。

## 修復

- 驗 matching manifest、generation、one-shot stage、exact-run receipt。
- stage 只驗證下一代 Publisher one-shot authority；reset 候選則由現有 live Publisher 轉換，保留舊 live cohort 的 generation 與 identity，避免跨代混接。
- 將 Publisher 與其他六服務逐欄比對 live cohort identity，並驗證各自 service label、activation mode 與 launchctl 實際載入路徑。
- reset 前的 normal live、轉換後候選與 bootstrap 後 live 都走同一份 Publisher structural receipt，驗 barrier-exec 外層、child module、`max-runs=1` 與 exact-run-id 格式。
- 拒絕任何 live PID、identity/path/mode drift 或無效 stage。
- reset candidate 移除 `StartInterval`／`KeepAlive`，保留 `RunAtLoad=true`，避免週期性 child。
- mutation 僅限 Publisher plist與 Publisher launchctl target。
- bootstrap/postcheck 失敗會恢復原 Publisher plist與原 loaded/absent 狀態，並寫 failure receipt。
- 成功後保留 private stage，供 Capacity preactivation 與後續 Publisher-only canary使用。

## RED / GREEN

- RED：新增 reset public action 測試，原入口回 usage exit 2。
- GREEN：Publisher reset、live identity drift、argv drift、launchctl path drift、任一服務 PID、bootstrap rollback共 7 passed。
- Publisher-only bounded regression（含 reset）：19 passed，228 deselected。
- Runtime manifest regression：48 passed。
- Capacity preactivation transition：10 passed，41 deselected。
- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`：PASS。
- `git diff --check`：PASS。

## 變更檔

- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `scripts/pantheon_content_runtime_manifest.py`
- `tests/test_agy_gemini_coordinator.py`

## 未做

- 未 promotion、未修改 live plist、未執行 reset、Capacity、readiness、Publisher activation、transaction、tag 或 push。

## 殘餘風險

- production 使用前仍須固定最終 candidate SHA 做原 reviewer thread 的針對性 re-review。
- review GO 後須先 promotion candidate，再以 host 正式入口執行一次 reset；reset PASS 後才能接既有 Capacity/readiness 與唯一 exact-run canary。
