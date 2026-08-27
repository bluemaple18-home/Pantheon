# Pantheon Acceptance B：gen05 topology guard Repair 結果

## 範圍與修正

- 卡片：`CARD-PANTHEON-ACCEPTANCE-B-GEN05-TOPOLOGY-GUARD-REPAIR-20260827-RETRY-1`
- 只調整 `validate_locale_plan` 的 rebuild guard：H2 wording equality 不再是 blocking authority；只有 non-empty authoritative fact-to-H2 topology 與 prior 相同時才拒絕。
- 未改動 provider、prompt、source-ref-map authority、safety authority、semantic budget、lifecycle、queue/state、runtime、publisher 或 production artifacts。

## RED → GREEN

- 新增 `test_outline_rebuild_allows_same_headings_with_changed_fact_topology`：current/prior H2 文字完全相同、但 fact-to-H2 topology 不同。修正前失敗於 `locale plan rebuild reused prior outline topology`；修正後通過。
- 既有 `test_outline_rebuild_rejects_synonym_headings_with_same_fact_topology` 維持通過，證明 mapping 相同仍 fail closed。

## Exact gen05 fixture

- `test_exact_production_gen05_legacy_safety_hydrates_read_only` 使用 mounted 的 exact gen05 bytes 與 `attempts/03/locale-plan.json` 作 prior，且以 `rebuild_by_slot={"article-01": True}` 經過本 guard。
- 驗證 22 個 mappings、current/prior topology 不同、source-ref map 與 legacy safety receipt 正確；external plan、source-ref map、plan-operation 與 continuation state bytes 均未變，`generations/06` 不存在。
- 測試只直接呼叫 `_hydrate_locale_plan`，不傳入 provider client，因此 planning/article/reviewer/publish provider calls 為 0；state bytes 不變亦涵蓋 semantic budget 未改變。

## 驗證

- 目標回歸：4 passed。
- `tests/test_agy_multilingual_pipeline.py`：224 passed。
- `git diff --check`：待候選 commit 前重跑。

## 殘餘風險

- guard 現在完全以 canonical fact-to-H2 allocation 判定；H2 wording 仍受既有 locale、outline、coverage 與 source-structure validations 約束，但不再具有 allocation authority。
