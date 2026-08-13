# APF-001 Verification Receipt

狀態：`DELIVERED_CANDIDATE`

## 範圍

- Source SHA：`af1d00b6721e32e3e1aefb55371ac6e3617d25a1`
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

共 7268 項，所有項目都有 source kind、article id、locale、campaign version、work id、lane 與 reason。空 fixture 的既有 queue 去重為 0；實際 caller 傳入既有 queue/state 時會排除所有已存在 create/rewrite/translation identity。

## 驗證命令

- `.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -k campaign_dry_run_workset -q`
- `.venv/bin/python -m scripts.agy_gemini_coordinator ... dry-run-campaign ... --output ...`（兩次後 `cmp`）

## 已知 gap 與下一 frontier

本 source commit 沒有可追溯的正式產品 spec；本 receipt 明示此缺口，未宣稱已提交 spec。下一 frontier 是由既有 coordinator 在明確授權下消費 workset；不在本卡範圍。
