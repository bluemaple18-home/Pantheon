# Pantheon publish durable identity root-cause closure

## Verdict

`ROOT_CAUSE_CLOSED / REPAIR_READY`

## 最後成功邊界

- `6dc98725e671b17cdc5c0e17e38cca75a24f5a71^` 的 promotion 只接受空的 `runs`／`gsc-copy`；active run 不會跨 actor replacement。
- 過去能發文，是先完成 promotion，再在當時 actor 內建立並跑完文章；沒有「actor-local active run 跨 promotion」的生命週期。

## 回歸起點與機制

- `6dc98725e671b17cdc5c0e17e38cca75a24f5a71` 新增 `preserved_run_ids`，但只驗 registry 的 `run_id/status` 與 queue digest。
- 該版測試的 preserved active state 沒有 `run_dir`，所以沒有覆蓋 production 的 actor-local `.work/gsc-copy/<run-id>`。
- `_promote_actor()` 會把整個 actor root 移到 rollback bundle，再以新 clone 取代；actor-local run payload 因此不在新 actor。
- `3e6eaee777e1d89c0a140713e6bc6c14a8943688` 才把新 installer 的 GSC root 固定到 `<queue-root>/gsc-copy` 並要求 promotion 驗 durable run_dir，但既有 V0391 已經 dangling，無法被這個 forward guard 修復。

## 被破壞的 durable invariant

Registry 是 durable state authority，但 article identity 仍只存在可被 actor replacement 移除的 `run_dir/brief.json`。因此 registry、article identity 與 run payload 沒有共同 durable owner；terminalization 將 state 轉成 failed 後，automatic sweep 又無法從 missing brief 取得 exclusion identity。

## 必須先紅的 regression

1. 建立 `run_dir=<actor-root>/.work/gsc-copy/<run-id>` 的 active registry，執行 promotion；必須在 mutation 前拒絕，不能留下 dangling registry。
2. `register_run`／exact reservation activation 必須把 immutable `mode/lane/article_ids` identity envelope 與 digest 寫入 registry；後續 dedupe 不依賴 brief 存活。
3. dangling active terminalize 後立即執行 `new_matrix_sweep`／`legacy_sweep`；不得建立相同 article identity、run、job 或 replacement。
4. 舊 registry 缺 identity envelope 時必須 fail closed；只接受可驗 source request／replacement receipt 衍生的 exact identity，禁止猜測或手寫 production JSON。

## 修復邊界

- 只修 durable identity authority、legacy fail-closed recovery seam、terminalization 與 sweep dedupe。
- 不執行 production mutation、promotion、Gemini、publish、push 或 tag。
- Candidate 必須由原 V0399 `c13557c89e1d3b5ff2b8e50db1c0040731f7f1d8` 取其 terminalization seam 作 prior art，但不得直接把該 NO-GO candidate 當 accepted base。
