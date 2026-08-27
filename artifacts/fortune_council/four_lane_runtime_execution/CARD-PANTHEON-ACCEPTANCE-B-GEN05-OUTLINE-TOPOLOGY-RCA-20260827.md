# Pantheon Acceptance B：gen05 outline topology authority RCA

status: `DISPATCH_READY`
card_id: `CARD-PANTHEON-ACCEPTANCE-B-GEN05-OUTLINE-TOPOLOGY-RCA-20260827`
chain_id: `PANTHEON-ACCEPTANCE-B-GEN05-OUTLINE-TOPOLOGY`

## 目的

以 production exact gen05 artifacts，唯讀定位 `locale plan rebuild reused prior outline topology for article-01` 的唯一根因與最小 Repair frontier；本卡不是 Repair，不授權重跑 generation 或任何 production mutation。

## 已知證據

- main、origin/main 與 runtime actor 已收斂至 `6766fff999de7af09efc227230e69efd25795108`；runtime generation 為 `g53-6766fff9-gen05-safety-authority-20260827`。
- 先前 `model route config digest mismatch` 已證明是 executor 把 raw route file SHA 當 canonical route digest；正式 canonical digest 為 `1ed24743202ff953bf32d07d570602e61c77194df45889cabc93b13495945e0e`，不是 code gap。
- 使用正式 route authority 續跑同一 gen05 後，在 provider/article/reviewer/publish calls 全為 0 時 fail closed：`deterministic locale plan failure: locale plan rebuild reused prior outline topology for article-01`。
- continuation state 前後相同：`abandoned_generations=[4]`、`completed_generations=[]`、`next_generation=5`、`semantic_budget=1`、`status=active`。
- gen05 檧案集合前後相同；gen06 不存在；唯一變動為失敗的 `planning-result.json` receipt。
- production execution evidence：`/private/tmp/pantheon-b-gen05-continuation-6766-20260827-02/summary.json`。

## 允許範圍

- 唯讀 production gen03／gen04／gen05 planning artifacts、continuation state、accepted actor 的相關 pipeline／schema／prompt／tests 與 git history。
- source decision 前先查 CodeGraph；無結果或失敗才限域 `rg`。
- 在 task-owned `/private/tmp` 建立 provider=0 exact-fixture harness 與 evidence。
- 唯一 repo 輸出：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN05-OUTLINE-TOPOLOGY-RCA-20260827-RESULT.md`。

## 禁止範圍

- 禁止 provider、article、Reviewer、publisher 呼叫；禁止正式入口重跑。
- 禁止修改 queue／state／runtime actor／manifest／service／source code／tests。
- 禁止 Repair、commit、merge、push、promotion、tag、deploy、production publish 或建立其他任務。
- 不處理 forged gen07 finding；不重新裁決已接受的 gen04 lifecycle 或 gen05 safety authority Repair。

## 必答根因

1. `prior_plan` 的 authoritative owner 與來源為何；本次 rebuild 比對的是哪一代、哪個 artifact、哪個 schema 下的 topology。
2. 「reused prior outline topology」的 exact deterministic predicate、expected／actual topology 與 artifact digests；它是否把舊版 partial plan 或同 generation retry 誤當合法 prior committed plan。
3. 此 shape 是否可由正式 runtime 穩定產生；與 gen04 partial lifecycle、gen05 safety hydration schema transition 是同根因、次級因子或獨立 gap。
4. 最後成功版本／行為、開始失敗的 commit／機制、被破壞的 durable invariant，以及 promotion／replacement boundary 是否相關。
5. 最小 Repair frontier：`why_not_less`、`why_not_more`、`do_not_absorb`；不得直接實作。

## 驗收

- 實際跑過一條 provider=0、可重跑、pass/fail 明確的 RED command，使用 exact gen05 artifacts，重現同一 topology error；import／fixture failure不算 RED。
- 列出 prior 與 rebuilt outline topology 的 deterministic 對照、來源 generation、schema identity 與 artifact digest。
- 證明 provider/article/reviewer/publish calls=0、semantic budget 不變、gen06 不存在、protected production bytes before==after；允許的 failure receipt 必須明列且重跑不重複累加。
- 對至少兩個可證偽假說給證據，最後只留一個主根因與必要 secondary factors。
- 唯一裁決：`GEN05_OUTLINE_TOPOLOGY_RCA_COMPLETE` 或 `GEN05_OUTLINE_TOPOLOGY_RCA_INCOMPLETE`。
