---
id: CARD-PANTHEON-ACCEPTANCE-B-GEN04-SEMANTIC-BUDGET-REVIEW-20260827-RETRY-1
status: ready
chain_id: PANTHEON-ACCEPTANCE-B-GEN04-SEMANTIC-BUDGET-REPAIR-20260827
parent_card_id: CARD-PANTHEON-ACCEPTANCE-B-GEN04-SEMANTIC-BUDGET-REPAIR-20260827
role: reviewer
cycle: 1
type: source_review
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定候選涉及 continuation lifecycle、durable authority 與 semantic budget 邊界，需對精確 production state 做獨立核心契約審查。
candidate_sha: 662942386c239d24c562438fcdce83279065f094
execution_mode: read_only_targeted_review
production_mutation: forbidden
remote_mutation: forbidden
ownership: []
forbidden_scope:
  - 修改或提交任何 source、tests、artifact、git refs 或候選內容
  - integration、merge、push、tag、deploy、promotion、publisher、provider、production 或真實 gen04/gen05 執行
  - 建立 Repair、Reviewer、replacement 或其他任務
verification:
  - 精確驗證 production semantic_budget=1 的 gen04 terminalization 與下一正式入口
  - 驗證 abandoned_generations authority、連續性、唯一性、上界與重放安全
  - 重跑鎖定回歸測試及受影響測試檔
  - git diff --check 通過且 worktree 維持 clean
evidence_path: runtime final response only
---

# Pantheon Acceptance B：gen04 semantic budget 替代 Reviewer

## 工作名稱 → 正在做什麼 → 現在狀態

gen04 semantic budget 替代驗收 → 唯讀裁決候選 `662942386c239d24c562438fcdce83279065f094` → `READY TO DISPATCH`

## 替代授權與邊界

Owner 於 2026-08-27 明確允許建立替代 Reviewer。原「Pantheon 翻譯公開網址自動化驗收」任務在 targeted re-review 後連續三次、再加 Owner 直接訊息一次，均顯示 turn completed 但沒有任何可見 message／tool item；這是 review transport failure，沒有產生目前候選的 GO／NO_GO。

本卡只替代失效的 review transport，不重置 root question、finding、Repair generation 或候選。原任務既有歷史 finding 仍是證據，但不得再作本候選裁決 authority。Owner 的例外只授權這一個替代 Reviewer；不授權第二個 Repair、integration、push、production 或外部 write。

## 固定 Authority

- candidate：`662942386c239d24c562438fcdce83279065f094`
- parent G2：`7f4a18cd024589fdd4100da9888dc79494207164`
- RCA evidence candidate：`d54e3e64014aaa0411a30608182268fab439412e`
- primary：`RESUME_CONTRACT_GAP`
- regression：`REG-GEN04-SEMANTIC-BUDGET-1-EMPTY-LOOP`
- Repair RESULT：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN04-SEMANTIC-BUDGET-REPAIR-20260827-RESULT.md`
- RED/GREEN evidence：`artifacts/fortune_council/four_lane_runtime_execution/gen04_semantic_budget_repair_20260827/`

## Root Question

候選是否讓 pre-provider abandoned allocation 不消耗 `semantic_budget=1`，在 gen04 terminalization／authority transition 後，下一個正式 continuation entry 恰好 targeting gen05 一次，同時維持 fail-closed、idempotent、bounded 且不接受偽造或不連續的 abandoned accounting？

## Targeted Review Contract

只審原 finding 與同類 regression，不得加入新功能或移動球門：

1. 精確 state 固定為 `started_after_generation=3`、`semantic_budget=1`、`next_generation=4`、`completed_generations=[]`、`abandoned_generations=[]`。
2. gen04 partial 只有 `external-plan.json`、`plan-operation.json`；缺 `source-ref-map.json`、`locale-plan.json`、PASS planning result、article/review。第一次正式 recovery 必須 fail closed；terminalization／consume action 只允許 canonical authority `next_generation=4→5`，保留 gen04 audit，不在同 action 建 gen05，provider/article/reviewer calls 全為 0。
3. 第二次相同 recovery／transition 必須完全 idempotent：state、transition、failure receipt 不重複累加，protected bytes 不漂移。
4. 下一個正式 continuation entry 必須恰好 targeting generation 5 一次；不得空 loop、重回 gen04、跳 gen06、重複 target 或在 terminalization action偷建 gen05。
5. 對候選新增的 `len(abandoned_generations)` accounting 做 adversarial source review：canonical validator 必須拒絕 duplicate、non-integer、out-of-order、non-contiguous、future、outside-owned-range 或 forged abandoned state；不得藉任意 list 長度擴張 budget、製造無界 continuation或繞過 semantic attempt 上限。
6. 正常沒有 abandoned generation 的 complete flow、既有 cross-version plan authority fail-closed 行為與 provider-facing semantic attempt accounting 不得退化。
7. 分開 Spec axis 與 Standards axis。只有 P0/P1 可 `NO_GO`；P2/P3 只能列 residual risk，不得阻擋。

## Required Verification

在 candidate tree 內唯讀執行：

```text
.venv/bin/python -m pytest -q tests/test_agy_multilingual_pipeline.py -k "semantic_budget or partial_generation_terminalization"
.venv/bin/python -m pytest -q tests/test_agy_multilingual_pipeline.py
git diff --check 662942386c239d24c562438fcdce83279065f094^..662942386c239d24c562438fcdce83279065f094
git status --short
```

先用限域 `rg` 對應 exact regression 測試名稱；不得擴掃或改測試。若 `.venv` 不存在，可使用 repo 既有 `uv run --frozen --no-sync`；不得下載、安裝或 network。

## Verdict

最終回覆只能是下列二選一，且必須附最小 evidence：

- `GEN04_SEMANTIC_BUDGET_REVIEW_GO`：無 P0/P1，列出 exact-state、adversarial accounting、targeted/full-file tests 與 clean/diff 證據，以及 residual risk。
- `GEN04_SEMANTIC_BUDGET_REVIEW_NO_GO`：只列 P0/P1；每項包含 `path:line`、觸發條件、風險、最小修法、重現命令／症狀及 regression id。

若候選不可讀、環境無法無網路驗證或證據不完整，回 `NO_GO` 並精確標示 verification blocker；不得猜測 GO。

## 停損

Reviewer 不修程式、不寫 RESULT、不 commit。完成 verdict 立即停止；不得把 GO 解讀為已整合、可 push 或 Acceptance B 已完成。

## 正式 task 初始 prompt 核心契約

```text
工作名稱：gen04 semantic budget 替代驗收
任務簡介：唯讀裁決既有 Repair 候選
任務卡：artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN04-SEMANTIC-BUDGET-REVIEW-20260827-RETRY-1.md
執行規範：完整讀卡，只審固定候選與原 regression。
來源：本任務 worktree HEAD
現在狀態：只做 bootstrap；收到 activation 前不得測試或 review。
```
