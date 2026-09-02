---
id: CARD-PANTHEON-OPEN2-PUBLICATION-SUCCESS-QUOTA-IMPLEMENTATION-20260902
chain_id: PANTHEON-FOUR-LANE-RESIDENT-OPERABILITY-20260902
role: implementation
cycle: 1
model: gpt-5.6-terra
reasoning: high
model_reason: strict core-bounded transaction/ledger change；native subagent 無 GPT-5.5 跑道，採最近的 Terra high
status: ready
risk: high
---

# OPEN-2 publication success quota 實作

## 一行契約

在既有 Publisher lock／ledger authority 內建立 Asia/Taipei 每日
`new=1, rewrite=1, translation=1, total=3` 的 durable success quota；不碰 provider cost cap。

## Strict fact gate

- 四條 lane 仍存在；`i18n-new` 與 `i18n-rewrite` 共用 translation bucket。
- quota check／reservation 必須在共同 `state_root/publisher.lock` 內、selection 後且任何
  repo/tag/push/publication mutation 前；不得以 scheduler、`--max-runs` 或 process-local
  counter 代替。
- 以 existing `ledger.json`／release identity 延伸 reservation→terminal accounting；
  不新增 state store。
- admission date 以 Asia/Taipei 固定於 exact `run_id`；跨午夜 replay 仍歸原日。成功只計
  一次；可證明未發布的失敗才釋放 success reservation。
- create／rewrite／translation 都必須處理 publication success 後 ledger 尚未 terminal 的
  crash window；replay 由 run_id、target commit/tag 與 remote identity 辨識，不猜測。
- production cap config 必須固定存在且 Publisher 真正讀取；缺失、錯值、malformed／future
  ledger schema 一律在 mutation 前 fail closed。

## Allowlist 與停線

- 可改：`scripts/agy_content_publisher.py`、`scripts/install_agy_content_publisher_launchd.sh`、
  `tests/test_agy_content_publisher.py`，以及直接驗 Publisher plist/config 的既有 test file。
- 可新增唯一 RESULT：
  `artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-OPEN2-PUBLICATION-SUCCESS-QUOTA-IMPLEMENTATION-20260902.md`。
- 若必須改 allocator、Coordinator lifecycle、manifest schema 或新增 state store，停止回
  `BLOCKED_REQUIRED_OWNER_SEAM`。
- 禁止 production runtime／queue／state mutation、provider、真 `launchctl`、publish、
  push、merge、deploy。

## RED → GREEN

1. 先建立 RED：class／shared translation／total exhaustion 均在 mutation 前拒絕；manual
   rerun／restart 不繞過；concurrency 只有一個 reservation。
2. 建立 crash matrix：reservation 後 mutation 前、commit/tag 後 push 前、push success 後
   ledger terminal 前、同 run replay、23:59 admission 跨午夜 terminal。
3. 最小 GREEN：延伸既有 ledger 與 prepared/reconcile seam；不得複製三套 phase state machine。
4. 跑 focused Publisher tests、affected suites、py_compile／bash -n、`git diff --check`；RESULT
   記錄實際數量與 production/public mutation 0。
