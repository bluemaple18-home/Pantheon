# APF-001 Verification Receipt

狀態：`DELIVERED_CANDIDATE`

## 範圍

- Base SHA：`3fafa941569e0eb736c1333eb2eac843e30f9c14`
- Campaign version：`apf-001-v1`
- 未啟動 Publisher、LaunchAgent、scheduler 或 production runtime。

## 乾跑結果

`dry_run_workset.json` 由空 queue/state fixture 連跑兩次產生，兩次檔案以 `cmp` 相同。

| Lane | Work count |
| --- | ---: |
| new | 1464 |
| rewrite | 353 |
| i18n-new | 4392 |
| i18n-rewrite | 1059 |

共 7268 項，所有項目都有 source kind、article id、locale、campaign version、work id、lane 與 reason。空 fixture 的既有 queue 去重為 0；create 仍以 article identity 去重，rewrite 與 translation 則只排除同一個 trim 後 campaign version 的既有 identity；舊版或缺 campaign version 的 run 不會阻擋新 campaign。

## 驗證命令

- `.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -q`
- `.venv/bin/python -m scripts.agy_gemini_coordinator ... dry-run-campaign ... --output ...`（兩次後 `cmp`）

## 已知 gap 與下一 frontier

本 source commit 沒有可追溯的正式產品 spec；本 receipt 明示此缺口，未宣稱已提交 spec。下一 frontier 是由既有 coordinator 在明確授權下消費 workset；不在本卡範圍。
