# Pantheon Acceptance B：gen05 runtime promotion apply

## 工作名稱

Pantheon Acceptance B：gen05 runtime promotion apply

## 正在做什麼

依已驗收且已推送的 promotion plan，將 production runtime authority 從
`6766fff999de7af09efc227230e69efd25795108` 原子收斂到
`2ce431ec41f5187531d88b52dfa91cef0373d8b5`。

## 現在狀態

`AUTHORIZED_TO_APPLY`。Owner 已明確授權本卡完整
`apply → postcheck → finalize`，失敗時授權執行既定 fail-closed rollback；
不得把此授權擴張到 gen05 provider、publish、額外 tag、push 或 deploy。

## 唯一 authority

- Plan result：`artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION-PLAN-2CE-20260828.md`
- Exact argv：`artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_runtime_promotion_plan_2ce_20260828/exact-plan-argv-2ce.json`
- Plan digest：`2ff333ae34c1fcda2af919aa70c1c6428a8817672b4c1fb996f9d35a5d0409cf`
- Capacity digest：`a7e02bc880390b8f65f31150a5bfef36efc0073d8d684b37cf9bc8be486ee93f`
- Target manifest digest：`7dbedf4e8544675f6203c2d40f96afa561d961a2c7e5a445c8d1f821f0d369f9`

## 執行契約

1. Fresh 核對 `origin/main` 含 target SHA，current actor／manifest／stage 與 plan authority 仍一致，transaction root 不存在。
2. 從 committed exact argv 重建參數；只把 subcommand 改為 `apply` 並附上 exact expected plan digest，不得手改其他參數。
3. 執行 official promotion apply；若未到 `POSTCHECK_PASSED`，保存 receipt 並依 transaction rollback boundary 執行 rollback，禁止自行修補 production。
4. apply 成功後執行 official finalize，要求 transaction `COMMITTED`。
5. Fresh 驗證 actor HEAD、manifest digest、stage digest／generation、queue/state protected snapshot、transaction journal 與 rollback metadata。
6. 驗證 provider、generation transition、publish、tag、push、deploy、service mutation 均為 0。

## 可修改範圍

- 既定 production actor／manifest／private stage。
- 既定 transaction root 與本卡唯一 execution evidence 目錄。
- 本卡 RESULT 與 receipts。

## 禁止範圍

- 不得執行 gen04→gen05 transition 或 gen05 provider。
- 不得 publish、建立或修改 tag、push、deploy其他內容。
- 不得刪 queue/state、猜測 authority、改寫 plan 或換 target SHA。
- 不得放寬任何 precondition；authority drift 一律 `BLOCKED`。

## 交付

- 唯一 verdict：`PROMOTION_COMMITTED`、`PROMOTION_ROLLED_BACK` 或 `PROMOTION_BLOCKED`。
- 回傳 exact transaction state、actor SHA、manifest/stage digest、protected bytes 結果與 mutation counters。
- code／config 不得修改；若發現缺口，只回報 finding，不開 Repair。
