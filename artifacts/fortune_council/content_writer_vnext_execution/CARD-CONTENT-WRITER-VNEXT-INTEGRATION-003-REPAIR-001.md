---
id: CARD-CONTENT-WRITER-VNEXT-INTEGRATION-003-REPAIR-001
card_id: CARD-CONTENT-WRITER-VNEXT-INTEGRATION-003-REPAIR-001
status: ready
execution_authorized: true
production_authorized: false
type: repair
chain: PANTHEON-WRITER-VNEXT-ORCHESTRATION
chain_id: PANTHEON-WRITER-VNEXT-ORCHESTRATION
role: repair
cycle: 1
strictness: strict
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定 P1 與兩個產品檔的核心 schema 修復；規格、reproducer、錯誤碼與驗收皆已固定，無未解架構 fork。
required_review_commit: 19e7e01085e9e26ce5c7003b60056b6f98a09705
required_candidate_sha: 1da55d6fc6b233e008ffff5959f54801a8b927eb
required_finding: WVNI3-REVIEW-001
required_source_ref: codex/pantheon-writer-vnext-integration-003-repair-source-20260-20260811-101655
source_kind: commit
ownership: 只修正 WVNI3-REVIEW-001；不得擴大 Writer vNext、Publisher 或 Runtime 架構
allowlist:
  - artifacts/fortune_council/content_writer_vnext_execution/CARD-CONTENT-WRITER-VNEXT-INTEGRATION-003-REPAIR-001.md
  - scripts/agy_editorial_contracts.py
  - tests/test_agy_editorial_contracts.py
  - artifacts/fortune_council/content_writer_vnext_execution/repair/writer_vnext_integration_003_repair_001/**
forbidden_scope:
  - 修改 review evidence、既有 implementation evidence、架構文件或其他卡片
  - 修改 Publisher、Runtime authority、coordinator、runner、capacity、queue、lock、manifest transport 或 production state
  - 新增第二套控制面、fallback、legacy shadow mode 或額外自由狀態
  - 自行 Review、另開 task、merge、push、deploy、publish、canary、tag、network、launchctl 或服務啟停
repair_output: artifacts/fortune_council/content_writer_vnext_execution/repair/writer_vnext_integration_003_repair_001/
---

# 修正 Writer vNext manifest 明示 opt-in 邊界

## 五行派工卡

任務 ID｜`CARD-CONTENT-WRITER-VNEXT-INTEGRATION-003-REPAIR-001`；只關閉 `WVNI3-REVIEW-001`。

派工對象｜獨立 Repair；GPT‑5.5 high；使用 clean worktree，不得由 Reviewer 自修。

任務目的｜讓 `EditorialManifestV1` 對缺少／錯誤 `orchestration_mode`、未知頂層欄位及不完整 legacy pair 一律 fail-closed。

可改範圍｜本卡、`scripts/agy_editorial_contracts.py`、`tests/test_agy_editorial_contracts.py`、唯一 Repair evidence 目錄。

驗收證據｜RED→GREEN public tests、Review reproducer 轉為阻擋、10 組完整回歸、allowlist、`git diff --check`、單一 repair candidate commit 與 clean state。

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：修正 Writer vNext manifest opt-in 邊界
- 正在做什麼：以最小 schema 修補關閉已重現的 P1 fail-open。
- 現在狀態：`ready`；正式內容服務仍 `0/4`，production 維持 `NO-GO`。

## 固定輸入

- 原 integration candidate：`1da55d6fc6b233e008ffff5959f54801a8b927eb`
- Review source：`bb0d6bc2752f157568339c590e9ef17f2d082e0e`
- Review commit：`19e7e01085e9e26ce5c7003b60056b6f98a09705`
- 阻斷 finding：`WVNI3-REVIEW-001`，P1，位於 `review/writer_vnext_integration_003_review_001/findings.json`
- 公開 reproducer：`review/writer_vnext_integration_003_review_001/manifest-opt-in-reproducer.py`
- 架構 invariant：`WVO-INV-011` 與 `WVO-ARCH-005`

## 唯一修復契約

1. 先做 CodeGraph 任務語意查詢，再讀 finding、reproducer、validator 與 public tests；若 CodeGraph 無結果或 semantic mismatch，才限域以固定 Git objects／`rg` 補證。
2. 採 TDD：先新增 public RED tests，證明下列輸入目前錯誤放行；保存 `red.txt` 後才改產品碼。
3. `EditorialManifestV1` 的必填頂層欄位必須正好包含：
   - `version`
   - `orchestration_mode`
   - `run_id`
   - `article_identity`
   - `brief_sha256`
   - `selected_stages`
   - `artifacts`
   - `artifact_sha256`
   - `final_candidate_sha256`
4. 只允許兩個既有 optional 頂層欄位：`legacy_candidate`、`legacy_candidate_sha256`；兩者必須同時存在或同時缺席，不得孤立出現。
5. `version` 必須等於 `EditorialManifestV1`；`orchestration_mode` 必須等於 `writer_vnext_opt_in_v1`。
6. 缺欄、錯 mode、未知／free-state 頂層欄位、孤立 legacy 欄位一律加入既有 deterministic finding `schema_version_unsupported`，不得新增另一套 error vocabulary、補值或 fallback。
7. 保留合法 core-only、optional stages 與完整 legacy pair 的既有成功行為；不得修改 Publisher／Runtime／coordinator／runner。

## 必補 public tests

- 更新 `_manifest()` 產生合法的 `orchestration_mode: writer_vnext_opt_in_v1`。
- missing `orchestration_mode` → invalid，含 `schema_version_unsupported`。
- wrong `orchestration_mode` → invalid，含 `schema_version_unsupported`。
- unknown/free-state top-level field → invalid，含 `schema_version_unsupported`。
- `legacy_candidate` 或 `legacy_candidate_sha256` 任一孤立存在 → invalid。
- 完整 legacy pair、core-only、optional stages 仍 valid。
- Review reproducer 的三個負向案例都必須由 `valid: true` 轉為 `valid: false`；`expected_opt_in` 維持 valid。

## 驗證矩陣

先跑 targeted：

```bash
<repo-root>/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_agy_editorial_contracts.py
```

再跑完整受影響 10 組：

```bash
<repo-root>/.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_agy_editorial_contracts.py \
  tests/test_agy_seo_copy_pipeline.py \
  tests/test_agy_content_publisher.py \
  tests/test_pantheon_runtime_fs_authority.py \
  tests/test_pantheon_runtime_activation.py \
  tests/test_pantheon_content_runtime_manifest.py \
  tests/test_pantheon_content_capability_probe.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_gemini_runner.py \
  tests/test_pantheon_content_capacity_guard.py
```

另需執行 Review reproducer、`git diff --check`、allowlist 檢查與 forbidden-path diff。若 worktree 無 `.venv`，只可唯讀使用主專案既有 `.venv`，並以 `PYTHONDONTWRITEBYTECODE=1`／`-p no:cacheprovider` 避免 allowlist 外產物；不得建立新依賴環境。

## Evidence 與交付

至少寫入：

- `red.txt`
- `green.txt`
- `verification-receipt.md`
- `changed-files.json`

全部通過才建立單一 repair candidate commit；parent 必須是含本卡的正式 source commit，worktree 必須 clean。回報 candidate SHA、parent SHA、修正 finding、changed files、targeted/full 測試數量、reproducer 結果及唯一 verdict：`REPAIR_CANDIDATE_READY_FOR_REREVIEW` 或 `BLOCKED`。

完成後必須回到原 Reviewer task `019fec79-c6d9-7122-bfc6-50212c782eca` 定點重審；Repair 不得自行關閉 finding。
