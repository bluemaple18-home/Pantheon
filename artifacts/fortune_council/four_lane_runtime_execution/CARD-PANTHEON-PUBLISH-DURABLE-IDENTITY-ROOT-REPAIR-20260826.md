---
id: CARD-PANTHEON-PUBLISH-DURABLE-IDENTITY-ROOT-REPAIR-20260826
status: ready
chain_id: PANTHEON-PUBLISH-DURABLE-IDENTITY-LIFECYCLE-20260826
role: repair
cycle: 2
dispatch_retry: 1
retry_reason: precreate task intro validation failed before thread creation
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: durable registry schema、跨 promotion 生命週期與 legacy recovery authority 已由 RCA 固定，屬 strict/core-bounded Repair。
supersedes:
  - CARD-PANTHEON-V0399-DANGLING-ACTIVE-TERMINALIZATION-SEAM-20260825
---

# Pantheon publish durable identity root repair

工作名稱：Pantheon publish durable identity root repair

任務目的：一次修復 registry、article identity、run payload 在 promotion／terminalization／automatic sweep 間的 authority 斷裂；不得再新增 symptom Repair。

## 必讀證據

- `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-PUBLISH-DURABLE-IDENTITY-RCA-20260826.md`
- Reviewer NO-GO：`e570d807db441e778078f3456af387082527fad9`
- V0399 prior art：`c13557c89e1d3b5ff2b8e50db1c0040731f7f1d8`

## 可改範圍

- `scripts/agy_gemini_coordinator.py`
- `scripts/pantheon_content_runtime_promotion.py`
- `tests/test_agy_gemini_coordinator.py`
- `tests/test_pantheon_content_runtime_promotion.py`
- 本卡 RESULT 與本卡專屬 evidence

## 固定契約

1. Registry 在 run 建立／activation 時保存 immutable identity envelope：schema version、mode、lane、排序後 article IDs 與 deterministic digest；不得保存公開正文或 prompt。
2. `_registered_article_ids_by_mode()` 與 automatic sweep 以 registry envelope 為 authority，不再以 `run_dir/brief.json` 是否存在決定 dedupe。
3. 新 active run 的 registry envelope 必須與 brief identity exact match；promotion 必須拒絕 actor-local或 missing durable run_dir，且在 mutation 前 fail closed。
4. Dangling terminalization 保留 identity envelope；terminalized failed state仍永久排除相同 article identity，除非另有明確且不屬本卡的 final-acceptance authority。
5. Legacy registry 沒有 identity envelope時只能由可驗、唯一的 source request／replacement receipt backfill；證據缺失或衝突即 fail closed，不猜 identity、不造 brief、不手寫 production JSON。
6. 沿用 V0399 的 CAS、before/after digest、zero-mutation negatives與 idempotency；只取 source/test prior art，不承認舊 candidate verdict。

## RED／GREEN

- 先建立 RCA 所列四個 RED；未紅不得改 implementation。
- Targeted GREEN 必須證明 promotion 防 actor-local loss、registry envelope persistence、terminalize→sweep no reseed、legacy evidence conflict fail closed。
- 完整跑 coordinator＋promotion tests、CLI help／py_compile、`git diff --check`。

## 禁止

- 禁止 production/runtime mutation、Gemini、publish、push/tag、另開卡／thread、改 installer、重構或加入第二套 identity registry。
- 禁止把 `run_id` 當 article identity；禁止用狀態文案或單次 PASS 取代完整 regression。
- 若固定契約無法在 allowlist 內完成，立即 `BLOCKED / SCOPE_EXPANSION`；不得自行擴大。

## 交付

- 單一 candidate commit；列 RED、GREEN、changed files、schema compatibility與剩餘風險。
- 只送獨立 Reviewer；Reviewer 只驗本卡四項 regression，不得新增 P2/P3 移動球門。

## RESULT

狀態：pending
