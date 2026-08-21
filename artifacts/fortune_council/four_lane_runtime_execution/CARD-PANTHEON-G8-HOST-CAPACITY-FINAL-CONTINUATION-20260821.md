---
id: CARD-PANTHEON-G8-HOST-CAPACITY-FINAL-CONTINUATION-20260821
chain_id: PANTHEON-G8-PUBLISHER-CANARY
parent_card_id: CARD-PANTHEON-G8-PUBLISHER-CANARY-FINAL-SHIP-20260821
role: implementation
cycle: 31
status: ready
type: production_ship
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 根因與執行序已固定，但包含 host capacity、production promotion、單筆 transaction、tag 與 push；採 strict/core-bounded 跑道。
promotion_source_sha: 4c16a2f4ab81865ba854cff6cf79a82dfe700c71
authorized_exact_run_id: auto-i18n-en-614aa4dc3542ab2c5637
authorized_target: ASTRO-BASE-01:en
ownership:
  - .work/CARD-PANTHEON-G8-HOST-CAPACITY-FINAL-CONTINUATION-20260821/**
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-HOST-CAPACITY-FINAL-CONTINUATION-20260821-RESULT.md
  - bounded host capacity receipt
  - authorized promotion, one-shot stage and exact-run publication receipts
forbidden_scope:
  - 修改 source、tests、rules、容量門檻或 telemetry parser
  - 全 repo 重掃、重跑 release test suite、重做已通過的修復驗證
  - sandbox 內先跑 capacity exercise、mock swap、手改 receipt 或 production artifact
  - 第二次 capacity exercise、第二次 activation、第二個 Publisher child、替代 run
  - normal aggregate activation、其他六服務 business child I/O、force push
  - 新建 Repair、Reviewer、Cycle 或 replacement thread
evidence_path: .work/CARD-PANTHEON-G8-HOST-CAPACITY-FINAL-CONTINUATION-20260821/
---

# G8 host capacity 單點續跑與正式開通

## 工作名稱 → 正在做什麼 → 現在狀態

G8 host capacity 單點續跑與正式開通 → 修正執行邊界後直接完成正式閘門與單筆 Publisher canary → READY / USER AUTHORIZED

## Root Question

能否不再重掃或補洞，將唯一一次 bounded capacity exercise 直接跑在已授權 host execution，通過後沿既有正式入口完成 `4c16a2f4...` promotion、one-shot stage 與指定 exact run 的 transaction → annotated tag → ordinary fast-forward push？

## 已證實根因與 authority

- 上一卡 RESULT commit：`e33a149cf570d1fff6a48a8814977143ab42a030`。
- sandbox 內 `/usr/sbin/sysctl -n vm.swapusage`：exit 1，`Operation not permitted`。
- 同一指令在授權 host execution：exit 0，成功取得 total／used／free；根因是 sandbox 權限邊界，不是 parser、容量不足或 production drift。
- promotion source authority：`4c16a2f4ab81865ba854cff6cf79a82dfe700c71`。
- current remote/main 與 runtime actor 上一卡終態：`b1719c0d6243c7ec6372889405a846ccd1b666ed`，production mutation=0。
- exact run：`auto-i18n-en-614aa4dc3542ab2c5637`；target：`ASTRO-BASE-01:en`。
- 使用者已明確授權本卡；上一卡已封存、worktree 已回收。本卡是必要的 forward continuation，不是自動 retry。

## 唯一執行序

1. BOOTSTRAP 只驗正式 thread、獨立 clean worktree、exact HEAD、card blob 與 CodeGraph；等待 ACTIVATE。
2. ACTIVATE 後只做 bounded current-invariant check：source/origin/actor exact SHA、authorized run 未發布且唯一、七服務 no-PID、必要 manifest/stage/barrier identity。禁止全 repo 掃描或 release tests。
3. 第一次就以 host escalation 執行唯一一次正式 `bounded-synthetic-dry-run` capacity exercise；不得先在 sandbox 試跑。receipt 必須為 `PASS`，兩 cycle 的 RSS/swap telemetry 皆 available，stop-loss `STOPPED`。
4. capacity PASS 才依既有正式入口做 promotion plan/apply/finalize、ordinary fast-forward push、coherent one-shot stage、Capacity preactivation 與 Rule25 readiness。
5. 所有 gate PASS 且七服務連續三次 no-PID，才執行唯一一次 Publisher-only activation；Publisher child <= 1，其他六服務 business child I/O = 0。
6. 驗指定 exact run 的 transaction、release commit、annotated tag、ordinary fast-forward push，以及 actor/origin clean coherent。
7. 成功或失敗都保存終態 RESULT 與 mutation accounting；不得 retry 或衍生卡。

## 停止條件

- host capacity invocation 未獲核准、exit 非 0、receipt 非 PASS 或 telemetry 不完整。
- 任一 current invariant、promotion、stage、Capacity/readiness、identity、barrier 或 selector gate 非 PASS。
- Publisher child > 1、其他六服務 business child I/O > 0、push outcome unknown，或需要修改 source 才能繼續。

命中即 `BLOCKED / NO RETRY`，必要時只精確 stop-loss Publisher label，寫 RESULT、commit、停止。

## 完成定義

只有 host capacity PASS，且指定 exact run 唯一完成 transaction、annotated tag、ordinary fast-forward push，Publisher child = 1、其他六服務 business child I/O = 0、actor/origin clean coherent，才可回報 `SHIPPED`。

## 交付

- `CARD-PANTHEON-G8-HOST-CAPACITY-FINAL-CONTINUATION-20260821-RESULT.md`
- 列 capacity invocation count、host/sandbox boundary、所有 gate、mutation accounting、transaction/tag/push、七服務 I/O、未做／未驗／殘餘風險。
