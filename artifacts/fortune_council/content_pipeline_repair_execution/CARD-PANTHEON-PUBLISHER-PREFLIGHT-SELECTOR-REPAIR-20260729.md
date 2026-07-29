# Pantheon Publisher Preflight Selector Repair

## 目的

修正發布器 fast preflight 引用已改名測試，解除通過內容在發布交易中的阻塞。

## 根因

- 發布器仍選取 `test_cloudflare_pages_exact_rewrites_use_prerendered_product_hubs`。
- 現行測試名稱已改為 `test_cloudflare_pages_wildcard_rewrite_uses_prerendered_product_hubs`。
- pytest 因找不到舊 selector 以 exit code 4 結束；發布交易已安全復原，未留下文章 commit 或 tag。

## 可修改範圍

- `scripts/agy_content_publisher.py`
- `tests/test_agy_content_publisher.py`
- 本卡與同任務驗證證據

## 禁止範圍

- 不修改文章候選、review、queue、ledger 或 retry 狀態。
- 不改 Reviewer、品質門檻、重試次數與自動發布政策。
- 不繞過 preflight 或完整 release gate。

## 驗收

1. `PREFLIGHT_TEST_COMMAND` 的每個 pytest node selector 均可解析至現存測試。
2. fast preflight 通過。
3. publisher 單元測試與完整受影響 release suite 通過。
4. `git diff --check` 通過。
5. 合併部署後執行單篇實際發布 canary；成功才啟用常駐 publisher。

## 回退

- 修復分支：`codex/publisher-preflight-selector-repair-20260729`
- 若驗收失敗，不合併；若上線後異常，以修復 commit 的 revert 回退。
