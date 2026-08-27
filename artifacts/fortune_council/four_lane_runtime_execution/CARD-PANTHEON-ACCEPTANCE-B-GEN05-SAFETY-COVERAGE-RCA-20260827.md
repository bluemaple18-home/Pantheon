# Pantheon Acceptance B：gen05 safety coverage authority RCA

status: `DISPATCH_READY`
card_id: `CARD-PANTHEON-ACCEPTANCE-B-GEN05-SAFETY-COVERAGE-RCA-20260827`
chain_id: `PANTHEON-ACCEPTANCE-B-GEN05-SAFETY-COVERAGE`

## 目的

以 production exact gen05 artifacts，唯讀定位 `locale plan safety coverage differs for article-01` 的唯一根因與最小 Repair frontier；本卡不是 Repair，不授權重跑 generation 或任何 production mutation。

## 已知證據

- Runtime actor／manifest 已收斂至 `e3a2bbd188a0d25f15a02cde1b2b6820df5dd583`／`g52-e3a2bbd1-gen04-semantic-budget-20260827`。
- gen04 已合法 terminalize，留下 `partial-generation-decision.json`、`generation-lifecycle.json`、`authority-transition-04.json`，continuation 為 `abandoned_generations=[4]`、`next_generation=5`、`semantic_budget=1`。
- 下一正式入口建立 gen05 planning artifacts；Writer plan operation `status=success`，deterministic hydration fail closed：`locale plan safety coverage differs for article-01`。
- Deterministic source fact package 的 22 個 fact 全部 `safety_boundary=false`；external plan 把 6 個 refs 標成 `true`：`source_ref_03/08/14/15/16/22`。
- gen05 未產生 article candidate、Reviewer receipt 或 publish transaction。
- 先前 Acceptance B 已知 blocker 是同一 protected source coverage family，但前一個精確錯誤為 `external locale plan source fact coverage differs for article-01`。

## 允許範圍

- 唯讀 production artifacts、候選 SHA `e3a2bbd1` 的相關 pipeline／schema／prompt／tests 與 git history。
- 在 task-owned `/private/tmp` 建立 provider=0 的 exact-fixture harness 與 evidence。
- 唯一 repo 輸出：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN05-SAFETY-COVERAGE-RCA-20260827-RESULT.md`。

## 禁止範圍

- 禁止 provider、article、Reviewer、publisher 呼叫；禁止正式入口重跑。
- 禁止修改 queue／state／runtime actor／manifest／service／source code／tests。
- 禁止 Repair、commit、merge、push、promotion、tag、deploy、production publish 或建立其他任務。
- 不處理 forged gen07 finding；不重新裁決已接受的 gen04 lifecycle Repair。

## 必答根因

1. provider schema／prompt 是否要求模型自行輸出 deterministic `safety_boundary`；模型取得了哪些足以正確填值的 authoritative input。
2. deterministic owner 是誰；external plan 的 flag 是 assertion、proposal 還是 authority；目前 hydration 為何只能 fail closed。
3. 六個 mismatch 是否可由正式 runtime 穩定產生，與先前 source-ref coverage blocker 是同根因、次級因子或新 gap。
4. 最後成功版本／行為、開始失敗的 commit／機制、被破壞的 durable invariant，以及 promotion／replacement 邊界是否相關。
5. 最小 Repair frontier：`why_not_less`、`why_not_more`、`do_not_absorb`；不得直接實作。

## 驗收

- 實際跑過一條 provider=0、可重跑、pass/fail 明確的 RED command，使用 exact gen05 artifacts，重現同一 safety coverage error；import／fixture failure 不算 RED。
- 列出 22 個 expected 與 6 個 actual mismatch 的 deterministic 對照與 artifact digest。
- 證明 article/reviewer/publish calls=0、protected production bytes before==after。
- 對至少兩個可證偽假說給證據，最後只留一個主根因與必要 secondary factors。
- 唯一裁決：`GEN05_SAFETY_COVERAGE_RCA_COMPLETE` 或 `GEN05_SAFETY_COVERAGE_RCA_INCOMPLETE`。
