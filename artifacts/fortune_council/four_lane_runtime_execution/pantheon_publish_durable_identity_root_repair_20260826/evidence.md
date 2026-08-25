# Pantheon publish durable identity root repair evidence

## Context

- Base：`131c85a53a98c4547aa9770d5356628e66a2b778`
- CodeGraph：ready，583 files／6997 nodes／15621 edges。
- V0399 `c13557c89e1d3b5ff2b8e50db1c0040731f7f1d8`：只取 CAS、before/after digest、zero-mutation negative 與 idempotency source/test prior art；未沿用 verdict。

## RED

Implementation 修改前執行四項 targeted regression，結果為 `4 failed`：

1. actor-local queue root 可進入 promotion plan，未在 mutation 前拒絕。
2. `register_run`／exact reservation activation 未保存 immutable identity envelope。
3. coordinator 缺少 dangling active terminalization seam，無法驗 terminalize→sweep lifecycle。
4. legacy source request／replacement receipt 衝突時未 fail closed。

## Fixed Contracts

1. Registry 保存 `identity_envelope`：schema version、mode、lane、排序且唯一的 article IDs、canonical SHA-256 digest；不保存公開正文或 prompt。
2. `_registered_article_ids_by_mode()` 與 active capacity 只使用 registry envelope；automatic sweep 不依賴 `run_dir/brief.json` 存活。
3. 新 active state 在 integrity gate 與 promotion 驗 envelope／brief exact match；promotion 拒絕 actor-local queue、missing/outside durable run_dir，且 plan fail-closed 發生在 transaction write 前。
4. Dangling terminalization 原樣保留 envelope；failed terminal state 仍永久排除相同 article identity。
5. Legacy backfill 只讀 queue root 內 canonical、regular、run_id 一致的 source request／replacement receipt；缺失、衝突、path drift 或 concurrent registry drift均拒絕。
6. Dangling terminalization 保留 expected digest CAS、before/after digest、zero-mutation negatives、concurrent drift rejection 與 byte-idempotent replay。

## GREEN

- Root targeted：`4 passed in 0.29s`
- CAS／legacy recovery／promotion drift targeted：`10 passed`（修正 replacement strict-schema 相容後相關 targeted `3 passed`）
- Compatibility targeted：原 16 個 failure 修正後 `16 passed`
- 完整 coordinator＋promotion（final-state）：`336 passed in 457.55s`
- `uv run python -m py_compile scripts/agy_gemini_coordinator.py scripts/pantheon_content_runtime_promotion.py`：PASS
- `uv run python -m scripts.agy_gemini_coordinator --help`：PASS，包含 `terminalize-dangling-active`
- `uv run python -m scripts.pantheon_content_runtime_promotion --help`：PASS
- `git diff --check`：PASS

## Schema Compatibility

- Registry 外層 schema 保持 version 1；新欄位 `identity_envelope` 自帶 version 1，digest 只覆蓋 identity core。
- 新 translate run 必須在 brief 明列 lane，避免把 legacy/new 身分猜成錯誤 lane。
- 既有 registry 若沒有 envelope，不從 live/missing brief 猜 identity；只有唯一 evidence 才 CAS backfill。
- Replacement 不修改既有 outbox strict decision schema；另寫 `identity-replacement-receipts/`，registry 只保存相對 evidence path。
- Promotion 對缺 envelope 的 preserved legacy registry fail closed，要求先由 coordinator evidence seam 完成可驗 backfill。

## Residual Risk

- 未在 production queue 執行 legacy backfill、terminalization 或 promotion；歷史 registry 若沒有可驗 evidence，會維持 blocked，這是預期 fail-closed 行為。
- 本 candidate 未操作 Gemini、publish、production/runtime、push 或 tag；最終 verdict 由獨立 Reviewer 只驗本卡 regression。
