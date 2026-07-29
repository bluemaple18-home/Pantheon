# CARD｜Pantheon multilingual policy mode repair

## 目的

修復 publication policy v2 將 `translate_existing` 候選稿誤判為 `create`，導致已通過多語 schema 與 deterministic gate 的文章無法套用。

## 可改範圍

- `scripts/agy_seo_copy_pipeline.py`
- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- 本卡與對應驗證證據

## 禁止範圍

- 不放寬 `create`／`rewrite_existing_body` 的 publication policy v2 gate。
- 不替 translation article 加入虛假的 `publicationPolicy`。
- 不修改正式文章、queue、ledger、版本、tag 或遠端 branch。

## 驗收

1. translation apply 明確以 `translate_existing` mode 呼叫 shared approval gate。
2. translation 仍須通過既有 schema、deterministic、review、approval hash 與 source drift gate。
3. `create`／`rewrite_existing_body` 缺少必要 policy 時仍 fail closed。
4. 兩個既有 RED 測試轉綠。
5. 完整 publisher release suite、publisher unit suite 與 `git diff --check` 全綠。

## 交付

- 一個可重現的 atomic commit。
- 驗證命令與結果。
- production canary 另行決定，不在本卡直接執行。

## 驗證結果

- 精準回歸：`4 passed`
- multilingual suite：`19 passed`
- publisher release suite：`196 passed`
- publisher unit suite：`58 passed`
- `git diff --check`：通過
