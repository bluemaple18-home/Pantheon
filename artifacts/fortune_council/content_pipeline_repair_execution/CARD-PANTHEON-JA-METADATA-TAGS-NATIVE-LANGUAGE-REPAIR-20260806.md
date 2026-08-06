# Pantheon JA metadata tags 母語化修復派工卡

- card_id: `CARD-PANTHEON-JA-METADATA-TAGS-NATIVE-LANGUAGE-REPAIR-20260806`
- chain_id: `PANTHEON-I18N-JA-RECOVERY-20260806`
- role: `implementation`
- cycle: `0`
- status: `QUEUED`
- 工作厚度: `standard`
- 風險: `中高；影響翻譯品質閘門，但本卡禁止碰 production`
- traces_to: `FR-JA-TAGS-NATIVE-001`, `SC-JA-REVIEWER-PASS-001`, `SLICE-JA-TAGS-001`

## 已知證據

- JA fresh canary run：`auto-i18n-ja-903a25b4046edb242172`。
- Reviewer：`gemini-3.1-flash-lite`。
- deterministic gate 三次皆為空 findings，但 Reviewer 最終以 `NON_NATIVE_LANGUAGE_RESIDUE` 拒絕。
- 殘留欄位是 `tags`，可重現值包含繁體中文 `人際`、`戀愛心理`。
- run 已完成但 `approved_by_reviewer: 0`；沒有 Publisher transaction、commit、tag 或 push。

## 單一垂直切片

`SLICE-JA-TAGS-001`：讓 JA 翻譯候選的所有可見 metadata tags 都必須是自然日文，且 deterministic gate 能在 Reviewer 前攔下繁中殘留。

## 目標與不變量

1. Writer contract 明確要求 `tags` 依目標語言重寫，不得複製來源語言 tag。
2. deterministic gate 逐一驗證 tags；JA tag 含繁中殘留時回傳穩定 finding，不能再以整篇大量假名掩蓋。
3. 現有 EN／JA／KO 合法候選仍通過。
4. 不降低 Reviewer 標準，不把已拒絕稿直接標成通過。

## TDD 驗收

### RED

- 新增測試：把 JA 候選 tags 改成 `人際`、`戀愛心理`，現況應暴露 gate 未攔截問題。
- 新增測試：Writer/public brief 必須明示 tags 不得沿用來源語言。

### GREEN

- 實作最小修補，讓上述測試通過。
- finding 必須可定位到 metadata tags，訊息使用繁中，不能只依賴 Reviewer 自由文字。

### VERIFY

- `uv run pytest tests/test_agy_multilingual_pipeline.py -q`
- `uv run pytest tests/test_agy_gemini_coordinator.py tests/test_agy_gemini_outbox.py -q`（若檔案存在且受影響）
- `uv run python -m py_compile scripts/agy_multilingual_pipeline.py`
- `git diff --check`

## 可修改範圍

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- 僅在直接測試依賴時，才可最小修改 `tests/test_agy_gemini_coordinator.py` 或 `tests/test_agy_gemini_outbox.py`。

## 禁止範圍

- 不改 Reviewer verdict、模型、provider、threshold 或 schema。
- 不改 topology、selector、coordinator、publisher、launchd 或 runtime SHA 契約。
- 不操作 production，不啟動或停止服務，不載入 i18n lanes。
- 不重跑舊 JA run，不建立 replacement，不處理 KO／rewrite，不發布內容。
- 不修改 registry、article locale module、sitemap、feed、redirect、共享 metadata 或既有產出。
- 不 push、不 merge；只交付候選 commit 給主線驗收。

## 停損條件

- 若修復需要超出 allowlist、改 Reviewer 放行邏輯或操作 production，立即停止並回報。
- 同一測試 blocker 連續三次仍無法排除，停止，不開 replacement task。

## 交付格式

- candidate SHA。
- changed files。
- RED／GREEN／完整驗證命令與結果。
- residual risk。
- 明確聲明未操作 production、未處理 KO／rewrite、未 push。
