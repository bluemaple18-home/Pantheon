# G8 production canary preactivation decision

## Decision

`NO-GO`

本卡完成 activation 後唯讀 preactivation slice，沒有建立 canary、沒有 production mutation、沒有 fetch/pull/push/tag、沒有 launchctl mutation，也沒有鎖定或消耗 production queue run。

## Why NO-GO

1. **Source authority drift**：本 task local HEAD 與 required base 是 `fe2221bd9cf0ca98848eca811eb08fa083ddf5bd`，但 `git ls-remote origin refs/heads/main` 回傳 `b8a34451e7a2b10a9e7ce1f11f366250cc67d87b`；production actor checkout 也在 `b8a34451e7a2b10a9e7ce1f11f366250cc67d87b`。本候選不能代表 current production authority。
2. **Live/staged runtime identity mixed**：live Publisher plist 仍是 `g8-b74646c4d9-20260818T055847Z` / manifest digest `f78faa3743bcd1ead4687dedfe093c9b11f1507461787f794c281ce201cec6a6`，stage 與 `runtime-manifest.json` 是 `g13-b8a34451e7-20260818T123555Z` / manifest digest `1b064cc10cf1de804523441fa4b7d6c173665fc5d78a723287e3d7286281447c`。這不是單一 coherent live identity。
3. **Selector evidence not current enough**：既有 `exact-rewrite-dry-run.json` 是 `status=dry-run` 且 `ready_runs` 恰好一筆，但它鎖的是 `legacy-auto-sweep-v1-astrology-0003-astro-base-03`、`base_sha=aab1eec46a2315a2648cc0d1495f958dcc098b9b`。stage plist 的 exact run 是 `auto-i18n-en-614aa4dc3542ab2c5637`，沒有找到與目前 authority 綁定、且不需 lock/mutation 的 current selector dry-run receipt。
4. **CodeGraph readiness**：已先跑 CodeGraph query，但此 worktree 未初始化 CodeGraph；按卡片契約改用限域 `rg`，但 CodeGraph readiness 本身仍是 `NOT_READY`。

## Passing Evidence That Is Not Sufficient

- APF-004 readiness summary：`READY`，`canary_created=false`，`production_mutation=false`。
- Official ai-core readiness gate rerun：`READY`，return code `0`。
- Missing-step fixture：`BLOCKED`。
- Capacity receipt：`PASS`，兩週期，10 個 negative cases，cleanup 每週期回收 `33367` bytes / `36` files。
- `0343bb7199b90794c10ce28cc4aff7ebbd0242b4..HEAD` 的 source/config/code diff 為空；只看到 APF-004 readiness evidence/package 與本卡 lineage。
- transaction directory count：`0`。
- `launchctl list | rg 'pantheon|agy|content'` 沒有 loaded rows。

## Evidence Files

- `preactivation-receipt.json`
- `preactivation-decision.md`

## Stop Condition

停止在 `NO-GO`。下一步必須回主線做 source-authority reconciliation；本卡不得自行啟動 production、建立 canary、consume run、建立 tag、push、apply/finalize promotion 或修改 LaunchAgent/runtime/source/config。
