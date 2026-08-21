# G8 Cycle 17 canonical Python contract re-review

## 目標

複審 `7e30deb3f8` 是否只修正 Cycle 17 parameter/card contract，並完整保留 canonical-realpath 與 production fail-closed 邊界。

## Review authority

- repair card：`f78d8c0b13`
- repair commit：`7e30deb3f8`
- prior blocker evidence：`68fdc5569e`
- candidate card：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-REPAIRED-SOURCE-PROMOTION-STAGING-CYCLE-17-20260821.md`
- repair evidence：`.work/CARD-PANTHEON-G8-CYCLE17-CANONICAL-PYTHON-CONTRACT-REPAIR-20260821/`

## Review questions

1. `<repo-root>/.venv/bin/python` 是否只作 discovery，正式 identity 是否鎖 canonical realpath。
2. Python `3.12.12`、regular executable、binary SHA256 是否成為 immutable evidence。
3. plan、apply、manifest、postcheck、formal preflight argv／authorization 是否要求同一 canonical literal。
4. source canonical-realpath check 是否完全未弱化。
5. 是否新增 production authority、執行 runtime 或遺漏 fail-closed 停止條件。
6. evidence hash、diff scope、`git diff --check` 是否一致。

## 邊界

- 唯讀 review；不得修改 candidate、source、runtime 或 evidence。
- 禁止 Gate A、push、promotion、preflight、restage、install、activation、canary。
- production mutation 必須為 `0`。

## 交付

- `ACCEPT` 或 `REJECT`。
- P0／P1／P2／P3 findings counts。
- evidence hashes、scope、remaining risk、下一拍唯一入口。

