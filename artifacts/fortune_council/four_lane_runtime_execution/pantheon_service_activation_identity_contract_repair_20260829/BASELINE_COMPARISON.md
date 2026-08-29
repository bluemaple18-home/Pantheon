# Parent Baseline Comparison

## Final fact

`BASELINE_IDENTICAL`

- parent：detached exact `779fb96434c15013d82833788a6795119730daad`保存baseline。
- command：candidate與parent使用同一interpreter、四個pytest檔案、`-q`參數與同一environment contract；command SHA記於`baseline_identical.json`。
- parent：`442 passed / 8 failed`，exit `1`。
- final candidate：`442 passed / 8 failed`，exit `1`。
- failure node set：exact identical。
- 逐node normalized error digest：exact identical。
- production/live mutation：`0`。

## Withdrawn first candidate

第一次candidate為 `406 passed / 44 failed`；新增36個G8 failures由shared actor-prefix parser拒絕合法opaque `g8-live`／`g8-staged` identity觸發。DESIGN_GO revision已完整撤回parser與embedded actor validation，沒有加入identity白名單。
