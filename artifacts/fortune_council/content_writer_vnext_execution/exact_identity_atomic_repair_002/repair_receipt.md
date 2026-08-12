---
id: CARD-CONTENT-WRITER-VNEXT-EXACT-IDENTITY-ATOMIC-REPAIR-002-RECEIPT
status: delivered_candidate
parent_candidate_sha: f69f14f0046eaa529c896425d22ce5c46689d2c7
finding_id: WRITER-VNEXT-EXACT-ID-ATOMICITY-002
---

# Exact Identity Atomic Repair 002 Receipt

## Root cause

前一版在正式 run directory 直接產生 brief，queue reservation 的 cleanup 與 activation 又各自採用 check-then-act。即使 ownership mismatch 已 fail closed，prepare 後仍可能留下正式 partial brief；foreign state 也可能在 ownership check 與 unlink／replace 之間被誤刪或覆寫。

被證偽假說：只要 queue state 綁定 correlation 與 token，prepare 後再驗 ownership 即足夠。Reviewer RED 證明 queue ownership 雖可拒絕，正式 brief 仍會殘留，因此 identity closure 必須涵蓋 filesystem staging 與 queue transition。

## Transaction transition

1. `reserved`：在 per-identity `flock` 內確認正式 run directory 與 stale marker 不存在，並以 exclusive create 寫入 token-owned queue reservation。
2. `staged`：正式 pipeline 只把 exact brief 寫入 `.exact-run-staging/<token>/<exact-id>/brief.json`；正式 run directory 尚不存在。
3. `activating`：在同一 identity lock 內把 reservation 原子移到 token transition marker，重驗 exact ID、run dir、correlation、token 與 staging brief closure。
4. `active`：原子發布 staging run directory，清除空 staging，再以 exclusive create 建立 active queue state；foreign state 先到時不覆寫並回滾本次正式 directory。
5. `abort`：cleanup 在 identity lock 內先把 state 原子移到 token cleanup marker，再驗 ownership；只刪本次 reservation。foreign replacement 會移回原 state path且 bytes 不變。

process crash 若留下 reservation、transition、cleanup marker或正式 directory，下一次 reservation 固定 fail closed；本卡未新增 recovery daemon。

## RED / GREEN

- RED：`.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_seed_new_matrix_runs_rejects_foreign_state_inserted_after_prepare -q`
  - 結果：`1 failed`。
  - 失敗點：foreign queue state 已保留，但 `run_root/<exact-id>/brief.json` 仍存在。
- GREEN：同一指令重跑。
  - 結果：`1 passed`。
- Transaction focused：`.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -q -k "exact_run or seed_new_matrix_runs or activate_run_reservation or register_run_is_idempotent"`
  - 結果：`18 passed, 81 deselected`。
- 完整受影響回歸：`.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py tests/test_agy_seo_copy_pipeline.py -q`
  - 結果：`235 passed in 143.80s`。
- `.venv/bin/python -m py_compile scripts/agy_gemini_coordinator.py`：PASS。
- `git diff --check`：PASS。
- allowlist 與 debug marker 搜尋：PASS，無越界檔案或殘留 marker。

## Matrix evidence

- prepare 後 foreign state：exception、foreign bytes 不變、零正式 brief、零 staging、零 outbox。
- cleanup interleaving：foreign replacement bytes 不變，未被 unlink。
- activation interleaving：active exclusive create 拒絕 foreign state，正式 directory 回滾，foreign bytes 不變。
- prepare／publish failure：只清本次 reservation與 token staging，零正式 run directory。
- foreign directory：sentinel bytes 不變。
- success：brief path與內容皆為 exact ID，queue state 為 active，無 reservation token與 staging residue。
- stale transition：prepare 前 fail closed。
- 未提供 exact ID 的既有自動 sweep 回歸包含於完整 coordinator 測試。

## Scope

Source/test 修改限於：

- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`

Evidence 限於本卡 evidence path。未執行 production run、provider call、enqueue、publish、transaction、tag、push、merge或 deploy。
