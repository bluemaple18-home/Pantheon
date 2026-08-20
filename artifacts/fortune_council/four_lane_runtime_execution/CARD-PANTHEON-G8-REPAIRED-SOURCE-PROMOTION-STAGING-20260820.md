---
id: CARD-PANTHEON-G8-REPAIRED-SOURCE-PROMOTION-STAGING-20260820
chain_id: PANTHEON-FOUR-LANE-PRODUCTION-RECOVERY-20260818
parent_card_id: CARD-PANTHEON-G8-LEGACY-BARRIER-ACTIVATION-REVIEW-2-20260820
supersedes:
  - CARD-PANTHEON-G8-ACTIVATION-FOUR-LANE-BOUNDED-CANARY-20260820
role: implementation
cycle: 13
status: ready
type: repaired_source_runtime_convergence
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 修復已獨立複驗，操作契約固定；production push與runtime promotion回退成本高。
production_authority_sha: c05929f2a7dac86e94aaeaa5ab6c5455892f5f77
ownership:
  - .work/CARD-PANTHEON-G8-REPAIRED-SOURCE-PROMOTION-STAGING-20260820/**
  - 唯一一次 origin/main fast-forward push至production authority
  - 唯一一次正式 promotion transaction與seven-service純staging
forbidden_scope:
  - activation、launchctl load/kickstart/reload、canary或lane run
  - Publisher transaction、publish、content commit、tag、第二次push、force push
  - source/tests修補、手改queue/state/plist/barrier/manifest、刪除或跨專案清理
verification:
  - exact source/remote/actor/manifest/stage/live與容量基線
  - current capability READY、capacity PASS、canary_created=false
  - release/pre-push gate PASS且remote fast-forward精確等於production authority
  - promotion plan/apply/postcheck/finalize完整receipt
  - staged seven coherent；legacy live seven保持原狀
  - queue/transaction/tag/launchctl/content mutation delta為零
  - git diff --check、evidence完整、worktree clean
evidence_path: .work/CARD-PANTHEON-G8-REPAIRED-SOURCE-PROMOTION-STAGING-20260820/
---

# G8 修復版 source promotion 與 staging

## 工作名稱 → 正在做什麼 → 現在狀態

G8 修復版 runtime convergence → 推送已複驗 source並重建seven-service stage → `READY / USER AUTHORIZED`

## Root Question

能否在零 activation、零 canary、零發文下，將已複驗的 `c05929f2a7dac86e94aaeaa5ab6c5455892f5f77` 收斂為 origin/main、actor、runtime manifest與staged seven的唯一authority？

## 已知事實與授權

- 修復 commits 已整合到 main：`f34974c040`、`c05929f2a7`。
- 原 Reviewer targeted re-review：`GO`；30/30、`bash -n`、`git diff --check` PASS；evidence `cb1bc1d404db8246d59a55b6c1d88c1f7883266c`。
- 舊 activation authority `88c6c0a95a...` 已失效；本卡不得沿用舊 generation 或舊 staged payload做 activation。
- 使用者於 2026-08-20 明確授權開卡派工監工，承接主線前一拍的 production promotion 授權。
- 授權只含一次普通 fast-forward push與正式 promotion/staging；不含 activation、canary、Publisher transaction、tag或publish。

## 執行契約

1. 核對 cwd、dispatch HEAD、clean/registered worktree；CodeGraph query失敗才限域 `rg`。
2. 唯讀保存 production authority、origin/main、actor HEAD、runtime manifest、private stage、live/staged seven、queue/transaction/tag/launchctl/content與主機容量基線。
3. 以 current正式 gate重驗 capability receipt、兩週期capacity與`canary_created=false`；任何非 READY/PASS立即`BLOCKED / NO CANARY`。
4. 讀 toolchain paths；使用task-local可寫`UV_CACHE_DIR`與`.venv`。不得變更lockfile或tracked source。
5. 先跑正式 release/pre-push零remote mutation預驗。緊鄰push前重讀remote；只准remote為production authority祖先。
6. 只執行一次普通 fast-forward `c05929f2a7dac86e94aaeaa5ab6c5455892f5f77:main`；禁止force與第二次有效push。結果不確定即停。
7. 以正式promotion governance建立plan、一次性authorization、apply、postcheck；失敗走同transaction rollback，PASS才finalize。
8. 只用正式installers產生new generation seven-service stage；禁止load/kickstart/reload與activation child I/O。
9. 用已修復正式preactivation入口驗證new staged seven coherent、legacy live seven coherent且未變；不得用舊shared manifest內容冒充old authority。
10. 驗actor、manifest、private stage與staged seven同一source/identity/generation/digest；保存零非授權mutation delta。

## 停損與交付

- 每個外部write入口只允許一次；不盲retry。同blocker第三次立即停止。
- remote漂移、capacity非PASS、promotion非READY、old live或new stage不coherent：零activation停止。
- 不建立canary、不產生lane run、不消耗Publisher run。
- 最終只可 `STAGED / NO CANARY` 或附唯一blocker的 `BLOCKED / NO CANARY`。
- 回報remote before/after、promotion receipts、new generation、identity matrix、stage/live結果、production mutation清單與evidence commit SHA。

## 短派工提示

你負責本卡，role=implementation、cycle=13。完整讀卡後只做一次已授權fast-forward push與正式promotion/restaging。production authority固定為`c05929f2a7dac86e94aaeaa5ab6c5455892f5f77`；dispatch card commit不是runtime source。禁止activation、canary、Publisher transaction、tag、publish與source修補。任何current gate非PASS即零mutation停止；只交`STAGED / NO CANARY`或`BLOCKED / NO CANARY`及完整evidence。
