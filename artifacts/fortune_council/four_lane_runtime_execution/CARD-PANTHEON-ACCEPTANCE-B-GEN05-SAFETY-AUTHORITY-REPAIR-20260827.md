# Pantheon Acceptance B：gen05 safety authority bounded Repair

status: `DISPATCH_READY`
card_id: `CARD-PANTHEON-ACCEPTANCE-B-GEN05-SAFETY-AUTHORITY-REPAIR-20260827`
chain_id: `PANTHEON-ACCEPTANCE-B-GEN05-SAFETY-COVERAGE`
rca: `GEN05_SAFETY_COVERAGE_RCA_COMPLETE`

## 目的

修正 provider safety echo authority gap：未來 external locale plan 不再輸出 `safety_boundary`；local hydration 依 deterministic source fact owner 注入。既有 production gen05 legacy external plan 只允許經明確 schema-receipt 綁定的 provider=0 legacy-read path hydrate，且原 audit bytes 不變。

## 可改檔案

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- 本卡唯一 RESULT／task-owned evidence artifacts

## 禁止範圍

- 不改 publisher、promotion、replacement、provider transport/model routing、semantic-budget、gen04 lifecycle 或 forged gen07。
- 不修改 production queue/state/artifacts；不呼叫 provider/article/Reviewer/publisher；不重跑正式入口。
- 不 commit、merge、push、deploy、tag、publish、建立其他任務。
- 不新增 registry、FSM、database、authority ledger 或第二套 runtime。

## 必要契約

1. Fresh provider schema/prompt 移除 `coverage_mapping.safety_boundary`，並明示 safety 為 local read-only authority。
2. Hydration 由 current `_source_fact_package()` 經 validated source-ref-map 注入 deterministic `safety_boundary`，下游 hydrated locale-plan shape 保持相容。
3. 既有 persisted legacy shape 不得被一般 fresh path 默默接受；legacy-read 必須由 companion planning receipt／legacy schema digest 明確辨識，provider calls=0，且不得改寫 `external-plan.json`、`source-ref-map.json`、`plan-operation.json`。
4. Legacy adapter 只忽略 external safety assertion；missing/duplicate/unknown source_ref、receipt/schema drift、無 companion receipt、其他欄位 drift 仍 fail closed。
5. Exact production gen05 fixture hydrate 後 22 facts 全部使用 deterministic false，且不新建 generation、不變更 continuation state。

## RED / GREEN 驗收

- 先新增 exact-shape provider=0 RED：current code 對 persisted gen05 legacy plan 精確失敗；protected fixture bytes before==after。
- GREEN：同一 fixture 由 legacy-read hydrate 成 `locale-plan.json`，provider=0，22 deterministic safety values 正確；三個 legacy audit artifacts bytes before==after。
- Fresh-shape test：schema 不含 safety field，provider output 含該欄位時 strict reject；合法 output 由 local 注入。
- Negative tests：missing/duplicate/unknown refs、schema receipt drift、missing receipt 至少各一個 fail closed，且 provider/article/reviewer=0。
- 跑受影響測試檔全套、targeted tests、`git diff --check`。

## 交付

- 唯一候選 commit SHA、parent、allowlist diff。
- RESULT 必須列 why_not_less／why_not_more／do_not_absorb、RED/GREEN commands、calls/bytes accounting、remaining risks。
- 不得宣稱 production 完成；候選須交獨立 Reviewer。
