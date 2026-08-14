# APF-004-GATE2-LAUNCHCTL-PATH-INDENT-INTEGRATION-001 Evidence

## 結論

- base：`2a073ad57e6799383236d743bcc0567f0a2d3d72`
- reviewed candidate：`1005385a88868a90ff310e6e2edefa00e2fb5f74`
- review verdict：`REVIEW_GO`
- integrated repair commit：`02b1a4dbf1`
- production mutation：`false`
- push：`false`
- 結果：`INTEGRATION_PASS`

## 整合鏈

- `970e55ff62`：先建立實體整合卡並鎖定邊界。
- `02b1a4dbf1`：cherry-pick exact reviewed candidate。
- root dirty checkout 未被修改。
- promotion worktree 在驗證前後無未追蹤 source／config drift。

## 驗證結果

- exact positive + 13 zero-mutation negatives + rollback／normal authority isolation：`17 passed in 48.14s`
- affected coordinator suite：`48 passed, 113 deselected in 93.89s`
- runtime manifest suite：`42 passed in 2.12s`
- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`：PASS
- `bash -n scripts/install_agy_content_publisher_launchd.sh`：PASS
- `bash -n scripts/install_pantheon_content_capacity_guard_launchd.sh`：PASS
- `git show --check --oneline --no-ext-diff 02b1a4dbf1`：PASS
- `git diff --check 2a073ad57e6799383236d743bcc0567f0a2d3d72..02b1a4dbf1`：PASS
- binary numstat：PASS，全部為文字檔。

## 精確變更

- installer 僅允許 `launchctl print` 的 `path =` key 前縮排。
- key／equals／value spacing、absolute non-whitespace path、raw／canonical／target equality 均未放寬。
- positive fixture 改為真實的四格縮排輸出。
- 除 repair card、repair evidence、integration card／evidence 外，沒有其他 source／config／workflow 變更。

## 停線點

- 本證據只證明本機整合與 regression gates 通過。
- 尚未 push、merge 或執行 production realignment／activation-only。
- 下一階段必須以 exact promotion SHA 取得授權，並在任何 live mutation 前一次通過完整 exact-live mechanical preflight。
