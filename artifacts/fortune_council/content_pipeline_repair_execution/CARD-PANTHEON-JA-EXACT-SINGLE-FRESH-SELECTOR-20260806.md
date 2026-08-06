---
card_id: CARD-PANTHEON-JA-EXACT-SINGLE-FRESH-SELECTOR-20260806
status: READY_FOR_DISPATCH
type: implementation
risk: production-control-plane
base_sha: cb845df125a3acabfcd4661fd3919ccf251b97bc
---

# 補齊 JA single-fresh exact selector

## 目標

在既有 queue → multilingual pipeline → Publisher 骨架中，補最小 selector，使一個全新 `ja/i18n-new` run 能由既有 publisher transaction 發布，並保留 commit、tag、`pushed: true` 證據。

## 邊界

- 不新增第二套 pipeline，不直接 apply locale module／registry，不手建 queue JSON。
- selector 必須只處理明確指定的新 run ID，禁止 fallback、broad sweep、KO、rewrite、舊 run 或 replacement lineage。
- 不修改品質 gate、Reviewer、模型、queue schema、publisher release gate 或 i18n LaunchAgent。
- production 不執行；交付 candidate commit、測試與 evidence，主線另行 review／部署／canary。

## 驗收

- RED/GREEN：只選取指定 JA fresh run；拒絕缺 selector、非 JA、非 fresh、舊 run、或多 run。
- 端到端 fixture 證明路徑會走既有 publisher transaction contract，而不是 direct apply。
- 受影響測試、compile、`git diff --check` 通過；changed files 限於入口、selector、測試與本卡 evidence。

