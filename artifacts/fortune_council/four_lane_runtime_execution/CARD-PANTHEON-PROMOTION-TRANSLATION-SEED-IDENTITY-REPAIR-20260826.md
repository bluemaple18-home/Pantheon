---
id: CARD-PANTHEON-PROMOTION-TRANSLATION-SEED-IDENTITY-REPAIR-20260826
status: ready
chain_id: PANTHEON-PROMOTION-CONTRACT-REPAIR-20260826
role: repair
cycle: 3
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
execution_mode: bounded_code_repair
production_mutation: forbidden
remote_mutation: forbidden
---

# Pantheon translation seed durable identity repair

工作名稱：修復正式 publication seed translation 後無法 promotion 的 durable identity 缺口。

任務目的：讓正式 publisher 新建的 active translation run 在 registry 寫入當下即具備可由 promotion 驗證的 identity envelope，且 new／rewrite lane authority 來自 publisher 已知的 ledger lifecycle，不靠 run ID 或文章名稱猜測。

## 根因證據

- 最後成功 promotion：actor `e5c0743fe1e0c99a66f2c0e3355591f2a353a322`，135 筆 queue，transaction `v0404-gsc-json-shape-e5c0743f-20260826` 為 `COMMITTED`。
- A publication commit `47d7b804f4dbda6491f48141535fc869000421aa` 經正式 `_seed_pending_translations` 新建 3 筆 active translation run，queue 增為 138。
- red-capable command：`<repo-root>/.venv/bin/python /private/tmp/pantheon_v0405_promotion_driver.py plan`，穩定回 `PromotionError: preserved run identity envelope is missing or invalid`；transaction root 未建立、production mutation 為 0。
- authority gap：`scripts.agy_multilingual_pipeline.enqueue_article_translations` 直接寫 active run state，沒有 `identity_envelope`；`scripts.agy_content_publisher._seed_pending_translations` 合併 `published_runs` 與 `rewrite_released_runs` 後失去 `i18n-new`／`i18n-rewrite` lane authority。
- durable invariant：active run registry entry 建立時必須已有 exact `{schema_version, mode, lane, article_ids, digest}` envelope，且與 brief 的 mode/lane/source article 一致。

## 可改範圍

- `scripts/agy_multilingual_pipeline.py`
- `scripts/agy_content_publisher.py`
- `tests/test_agy_multilingual_pipeline.py`
- `tests/test_agy_content_publisher.py`
- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`

## 禁止範圍

- 禁止修改 promotion validator、放寬 identity contract、補寫或遷移 production queue、刪除三筆 translation run、啟動服務、push、promotion 或 publication。
- 禁止由 run ID prefix、文章 ID、檔案路徑或目前 queue 狀態猜 lane；lane 必須由建立該 run 的 authoritative publication lifecycle 明示傳入。
- 禁止建立新 Repair／Reviewer thread；回原 Repair 與原 Reviewer。

## 驗收

1. 先補一個會對現有 publisher-seeded active translation state 轉 RED 的 regression test，再做最小修復。
2. new publication seed 為 `translate_existing / i18n-new`；legacy rewrite seed 為 `translate_existing / i18n-rewrite`。
3. state envelope digest 可重算且與 brief 一致；既有 idempotent enqueue 不覆寫、不漂移 identity。
4. `enqueue_article_translations` 不得以 optional lane 建立無 envelope active state；所有 production caller，包括 campaign replay，必須使用其既有 authoritative lane 明示傳入。
5. promotion object-only contracts、invalid JSON fail-closed、GSC array bytes-preserved contract 不得放寬。
6. 跑受影響測試、promotion focused tests、AST／語法檢查、`git diff --check`，並確認 production mutation `0`。

## 交付

- 完整 candidate commit SHA。
- RED／GREEN 指令與結果。
- 變更檔案、production mutation accounting、剩餘風險。
- 只能標記 `DELIVERED_CANDIDATE`，主線與原 Reviewer 保留 GO。
