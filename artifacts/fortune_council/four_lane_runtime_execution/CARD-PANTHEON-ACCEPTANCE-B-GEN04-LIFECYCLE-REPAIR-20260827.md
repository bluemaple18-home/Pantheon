---
id: CARD-PANTHEON-ACCEPTANCE-B-GEN04-LIFECYCLE-REPAIR-20260827
status: ready
chain_id: PANTHEON-ACCEPTANCE-B-GEN04-LIFECYCLE-20260827
role: repair
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: lifecycle/state contract 規格已固定且影響 continuation authority、audit 與後續唯一 B generation，但目前沒有未解架構 fork；採 strict bounded repair，維持單一既有 continuation planning seam。
execution_mode: bounded_code_repair
production_mutation: forbidden
remote_mutation: forbidden
---

# Pantheon Acceptance B：gen04 lifecycle contract bounded Repair

工作名稱：Pantheon Acceptance B：gen04 lifecycle contract bounded Repair

任務目的：修復 `RESUME_CONTRACT_GAP`。對「generation 04 已配置 `external-plan.json`／`plan-operation.json`，但缺 `source-ref-map.json`」的舊 partial generation，建立正式、可重入且 fail-closed 的 continuation planning recovery／terminalization contract；不得猜 mapping、補造完整 planning outcome，並讓合法 replan／next-generation 路徑有明確終態與 audit。

接手依據：`HANDOFF-PANTHEON-ACCEPTANCE-B-GEN04-LIFECYCLE-RCA-20260827.md`；原 B task/thread：`01a03c34-fd96-7021-9423-29879c9b5b47`（`Pantheon 翻譯公開網址自動化驗收`）。唯一主裁決為 `RESUME_CONTRACT_GAP`。這是同一 B chain 的唯一 bounded Repair，不得建立 replacement B task。

## 執行順序與硬門檻

1. 先在精確 provider=0 fixture 上補 RED，並實際連續執行兩次同一測試／fixture。RED 必須在任何 implementation change 前成立；未取得完整雙跑證據不得改 production code。
2. RED 後才可在既有 continuation planning seam 做最小實作；不得擴大為 publisher、promotion、replacement、provider 或 production recovery flow。
3. 實作後重跑同一雙跑 RED fixture 並補 GREEN／regression evidence，確認原 finding 仍 fail closed、partial generation 不被誤當 committed/resumable，且正常完整 generation 行為不退化。
4. 交付唯一 candidate commit 與專屬 RESULT/evidence；主線須回原 B task，交由原 Reviewer 針對原 finding 與 regression re-review。Worker 不得自行整合、執行 B、promotion、publish 或 production acceptance。

## 可改範圍

只允許修改：

- `scripts/agy_multilingual_pipeline.py`：既有 continuation planning seam，限 `_load_or_create_source_ref_maps`、`_run_locale_generation`、`_load_or_create_continuation_state` 及其必要的同檔 helper／contract wiring。
- `tests/test_agy_multilingual_pipeline.py`：provider=0 精確雙跑 RED、最小實作後 regression／idempotency 測試。
- 本卡專屬 `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN04-LIFECYCLE-REPAIR-20260827-RESULT.md`。
- 本卡專屬 `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen04_lifecycle_repair_20260827/` evidence 目錄。
- task-owned `/private/tmp/pantheon-acceptance-b-gen04-lifecycle-repair-*` 暫存證據。

不得修改任何其他檔案、共享 metadata、registry、queue、生成頁、sitemap、feed、redirects、production data/state 或既有 evidence。

## 禁止事項

- 禁止呼叫 Writer、Reviewer、任何 provider 或 network；provider/article/reviewer calls 必須維持 0。
- 禁止執行 production、B fresh generation、generation 04、generation 05、publisher、promotion、replacement、deploy、push、tag 或 remote mutation。
- 禁止刪除、rename、覆寫或補造 generation 04 的 partial artifacts；禁止手改 queue、registry、continuation state、current-generation authority 或 audit receipt。
- 禁止猜測／重建 `source-ref-map.json`、以 coverage/natural-language similarity 取代 deterministic mapping，或把目錄／`next_generation` 存在當成 committed 證據。
- 禁止建立第二張 Repair、Reviewer、replacement thread 或新的 implementation frontier；遇到 scope 外 defect 只在 RESULT 回報主線。

## 固定 RED fixture 與雙跑證據

Fixture 必須精確建立：同一 locale generation 04 目錄已有 `external-plan.json` 與 `plan-operation.json`，缺 `source-ref-map.json`、`locale-plan.json`、`planning-result.json`、`article-operation.json`、`review-operation.json`；continuation state 為 `status=active`、`started_after_generation=3`、`next_generation=4`、`completed_generations=[]`。使用 deterministic fail-if-called doubles，不能以單純 mock assertion 或錯誤文案代替 call count。

在實作前連跑兩次，逐次保存可重現 receipt，必須明確證明：

- Writer/provider calls = 0、article calls = 0、Reviewer calls = 0；
- new generation = 0；
- operation success receipt = 0；
- protected source artifacts、continuation state、current-generation／authority bytes 的 before/after 完全一致；
- 只允許 deterministic append-only failure receipt；第二跑不得重複累加、改變裁決或改寫受保護 bytes；
- 兩跑的 blocker、terminal decision（在現行程式尚未具備時應明確顯示 contract gap）與核心計數一致。

若 RED 不能穩定捕捉上述契約，立即停在測試／證據階段，不得先修改實作。

## 最小 lifecycle contract

實作必須在既有 continuation planning seam 內明確區分三種 durable 狀態：

- `allocated`：generation identity／目錄與部分 plan artifact 存在；不代表 planning committed。
- `committed`：同一 generation 必須有可驗證且成對的 external plan、source-ref map、source／extractor contract version、coverage result 與 operation terminal success；partial files 不得推論為 committed。
- `resumable`：只有 committed planning outcome 且 continuation 明確授權 resume action 才能成為 current resumable generation；`next_generation=4` 僅表示 allocation target。

對精確 partial fixture，contract 必須：

1. fail closed，不猜 mapping、不呼叫 provider、不產生 article／reviewer operation、不寫 success receipt；
2. 提供正式且可觀測的 `terminalize`／`abandon` partial-generation decision，保留原始 plan／operation audit artifact 與 failure receipt；不得人工刪檔或手改 state；
3. 只在合法 terminal state 後允許 deterministic replan 或建立下一 generation，並由正式 continuation state／authority contract 表達，不可直接跳過 partial generation 或把其檔案當成功結果；
4. 保持 source、continuation、current-generation authority 與既有 queue state 的 ownership 邊界，不以 repair 代替未授權 state mutation；
5. 對同一 partial generation 重跑具 idempotency：相同 input／identity／contract version 產生相同 terminal decision，audit 保留且 failure receipt 不二次累加；
6. 對正常完整 planning outcome 不增加 provider、article、reviewer 或 publication side effect，不破壞既有 cross-version guard。

不得以新增第二套 registry、FSM、database、canonical writer 或常駐 recovery service 實現；若既有資料模型不足，採最小可驗證欄位／artifact contract，並在 RESULT 說明 why_not_less、why_not_more 與未吸收項目。

## 驗證與交付

至少執行並記錄：精確 fixture 雙跑 RED（改碼前）、實作後雙跑 regression／idempotency、受影響 `tests/test_agy_multilingual_pipeline.py` 測試、必要的 targeted test 與 `git diff --check`。所有結果需列出 command、exit status、call counts、generation／receipt counts、protected-byte hashes 與 artifact inventory；不得用狀態文案單獨宣稱完成。

RESULT 必須標記 `DELIVERED_CANDIDATE`，包含：根因與 durable invariant、RED→implementation→regression 證據、唯一 candidate commit SHA、允許檔案清單與 diff 摘要、未執行的 production／B／publisher／promotion 動作，以及回原 B task Reviewer re-review 指令。不得標記 `ACCEPTED`、`INTEGRATED`、`PRODUCTION_GO` 或宣稱 Acceptance B 完成。

停損條件：同一 blocker 第三次失敗、需要修改 scope 外檔案／production state、需要 provider/network、無法保持 provider=0、bytes 被非授權改寫、或 lifecycle contract 仍需猜測 mapping／人工 state mutation；保留證據並回報主線。
