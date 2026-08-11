---
id: CARD-CONTENT-WRITER-VNEXT-INTEGRATION-002
card_id: CARD-CONTENT-WRITER-VNEXT-INTEGRATION-002
status: ready
type: implementation
chain: PANTHEON-WRITER-VNEXT-ORCHESTRATION
role: implementation
cycle: 2
strictness: strict
model: gpt-5.5
reasoning: high
source_commit: e6d93fba050eac7c22e1a34bf52d8ac4c707a1b3
supersedes: CARD-CONTENT-WRITER-VNEXT-INTEGRATION-001
traces_to:
  - WVO-SLICE-001
  - WVO-ARCH-006
  - WVO-INV-012
---

# Writer vNext Integration 002：以完整 Runtime 基底疊加 Writer 純新增 overlay

## 目的

以 Runtime Authority final reviewed candidate `e6d93fba050eac7c22e1a34bf52d8ac4c707a1b3` 為完整基底，只疊加 Writer vNext 從共同 Writer base `e4df0fc4349568cb0a7df2de56a4865885361494` 到 reviewed orchestration/preflight tip `c7ad4881eabc47cbf43e5053f1ac79d7e70af546` 的 37 個純新增檔，產出可測試、無 Publisher 衝突的 integration candidate。

Integration-001 已證明反向套用 Runtime 尾端五檔修補會缺少 manifest 與五個 Runtime tests，固定 verdict 為 `BLOCKED / ALLOWLIST_VERIFICATION_MISMATCH`。本卡改變 composition 方向，不沿用其 staged files，也不修補舊 worktree。

本卡獲准做 repo 內 composition；不授權 merge 到主線、push、deploy、publication、production 或 canary。

## 固定 authority

- Runtime full base / final reviewed candidate：`e6d93fba050eac7c22e1a34bf52d8ac4c707a1b3`
- Runtime final review：`38774ddf1bccc77a0b40917322bb100d238469d7`
- Runtime final evidence：`artifacts/fortune_council/runtime_authority_activation_execution/review/runtime_authority_activation_review_003/findings.json`
- Writer overlay base：`e4df0fc4349568cb0a7df2de56a4865885361494`
- Writer overlay tip：`c7ad4881eabc47cbf43e5053f1ac79d7e70af546`
- Writer contract candidate/review：`671fdba9bf1b5655cc9182bbf375cadae3efb0b5` / `038cf4d2979bf2a1a8ceaf4d44964c3fde5816c6`
- Writer orchestration candidate/review：`4cd768e353e6e349d15f57c5366a3275f7eefb8c` / `6476719ca652216785166f6c278f073b9b3be760`

只有上述 final `REVIEW_GO` evidence 是 authority。Writer overlay 內舊 composition-preflight evidence 是歷史記錄，已被本卡與 integration-002 evidence supersede，不得作為新 composition 結論。

## Overlay 不變量

先驗證：

```text
git diff --name-status e4df0fc4349568cb0a7df2de56a4865885361494 c7ad4881eabc47cbf43e5053f1ac79d7e70af546
```

必須正好 37 個路徑，且每列狀態都是 `A`；不得有 `M`、`D`、rename、binary 或 submodule。若不符，立即 `BLOCKED / WRITER_OVERLAY_IDENTITY_DRIFT`。

37 個 overlay 路徑只能以 `c7ad4881...` 的 exact blob materialize；不得從 stale Writer base 搬入任何既有 Runtime、Publisher、generated content 或其他檔案。每個 overlay 最終 blob 必須等於 `c7ad4881...`。

## 可改範圍

- 上述固定 diff 推導出的 37 個純新增 Writer overlay 路徑。
- 本卡 evidence：`artifacts/fortune_council/content_writer_vnext_execution/evidence/writer_vnext_integration_002/**`

其中唯一 executable source/test additions 應為：

- `scripts/agy_editorial_contracts.py`
- `tests/test_agy_editorial_contracts.py`

其餘 overlay 均為 Writer 卡片、review/evidence 或 orchestration architecture 文件。

## 禁止範圍

- 不得修改、重建或重新解衝突 `scripts/agy_content_publisher.py`；它必須保持與 Runtime base `e6d93fba...` blob 完全一致。
- 不得修改任何 Runtime manifest、filesystem authority、activation、capacity guard、coordinator、runner、outbox、registry、metadata、article、sitemap、feed、redirect、package 或 lockfile。
- 不得套用 stale Writer base 的完整 tree、merge Writer branch、cherry-pick production/content commits或複製 Integration-001 staged state。
- 不得新增 queue、role、approval、publication、deployment 或 retry authority。
- 不 push、deploy、publish、canary、tag，不啟動／重啟服務，不寫 production state。
- 不自行 Review，不建立新 task，不宣稱 production ready。

## 實作契約

1. 先用 CodeGraph 做 Writer editorial contract／coordinator／publisher boundary 的任務語意查詢，再由固定 Git objects 確認。
2. 驗證 Runtime candidate final review 為 `REVIEW_GO`，且 source HEAD 是本卡 commit 的 exact SHA。
3. 驗證 Writer overlay 為 37 個全 `A` 路徑；以 exact `c7ad4881...` blobs materialize，禁止執行 stale tree merge。
4. materialize 後驗證 Publisher 與全部非-overlay Runtime paths仍與 source parent 相同；若任何既有檔被改動，立即 `BLOCKED / BASE_TREE_MUTATION`。
5. 寫 integration-002 evidence，最後只建立一個 candidate commit；parent 必須是本卡 source commit，worktree clean。

## 必跑驗證

使用 canonical Pantheon `.venv/bin/python`，在本 worktree cwd 執行；不得 sync 或改 lockfile。

```text
tests/test_agy_editorial_contracts.py
tests/test_agy_seo_copy_pipeline.py
tests/test_agy_content_publisher.py
tests/test_pantheon_runtime_fs_authority.py
tests/test_pantheon_runtime_activation.py
tests/test_pantheon_content_runtime_manifest.py
tests/test_pantheon_content_capability_probe.py
tests/test_agy_gemini_coordinator.py
tests/test_agy_gemini_runner.py
tests/test_pantheon_content_capacity_guard.py
```

另外驗證：

- 37/37 overlay blob equality against `c7ad4881...`。
- `scripts/agy_content_publisher.py` blob equality against source parent／`e6d93fba...`。
- `git diff --name-status <source-card-sha> HEAD` 只能是 37 overlay paths 加 integration-002 evidence。
- `git diff --check <source-card-sha> HEAD`。
- conflict/debug marker scan。
- Runtime final evidence、Writer final evidence、source parent與candidate identity。
- 禁止 production mutation 的測試仍通過。

## Evidence 與交付

至少包含：

- `overlay-manifest.json`
- `composition-receipt.md`
- `verification-receipt.md`
- `changed-files.json`

最終狀態：

- `CANDIDATE_READY_FOR_REVIEW`：全部契約與驗證通過。
- `BLOCKED`：附 stable blocker、實際證據與最小解除條件。

回報 candidate SHA、parent SHA、37/37 blob equality、Publisher equality、changed files、測試數量／結果、clean state 與唯一 verdict。
