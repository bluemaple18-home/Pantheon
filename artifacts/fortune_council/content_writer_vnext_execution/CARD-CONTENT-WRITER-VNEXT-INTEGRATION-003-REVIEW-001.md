---
id: CARD-CONTENT-WRITER-VNEXT-INTEGRATION-003-REVIEW-001
card_id: CARD-CONTENT-WRITER-VNEXT-INTEGRATION-003-REVIEW-001
status: ready
execution_authorized: true
production_authorized: false
type: review
chain: PANTHEON-WRITER-VNEXT-ORCHESTRATION
chain_id: PANTHEON-WRITER-VNEXT-ORCHESTRATION
role: code_review
cycle: 1
strictness: strict
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定 SHA 的核心整合審查；需獨立驗證 overlay 組成、runtime/publisher 不變性、控制面單一性與完整回歸，但沒有未解架構 fork。
required_base_sha: cbed615c9c16a03b4d3ccfcf816d9901feea0ed9
required_candidate_sha: 1da55d6fc6b233e008ffff5959f54801a8b927eb
required_writer_overlay_sha: c7ad4881eabc47cbf43e5053f1ac79d7e70af546
required_source_ref: codex/writer-vnext-integration-003-review-source-20260811
source_kind: commit
ownership: 唯讀獨立審查 Writer vNext Integration-003 candidate；只可新增本 Review 卡與唯一 review evidence
allowlist:
  - artifacts/fortune_council/content_writer_vnext_execution/CARD-CONTENT-WRITER-VNEXT-INTEGRATION-003-REVIEW-001.md
  - artifacts/fortune_council/content_writer_vnext_execution/review/writer_vnext_integration_003_review_001/**
forbidden_scope:
  - 修改任何既有 source、test、spec、implementation card、implementation evidence 或候選 commit
  - 自行 Repair、重做舊 integration、重新定義需求、放寬 success criteria 或另開 task
  - merge、push、deploy、publish、production queue/state/article、canary、tag、network、launchctl 或服務啟停
  - 以實作者 receipt、單次 PASS、mock、狀態文案或自填 artifact 取代獨立重現
review_output: artifacts/fortune_council/content_writer_vnext_execution/review/writer_vnext_integration_003_review_001/
---

# Writer vNext Integration-003 獨立 Review

## 五行派工卡

任務 ID｜`CARD-CONTENT-WRITER-VNEXT-INTEGRATION-003-REVIEW-001`；固定審查 candidate `1da55d6fc6b233e008ffff5959f54801a8b927eb` 相對 base `cbed615c9c16a03b4d3ccfcf816d9901feea0ed9`。

派工對象｜獨立 Reviewer；使用 clean worktree；不得修改候選 source/test，不得要求實作者自審。

任務目的｜判斷 Integration-003 是否只把 Writer vNext 的 37 個 exact blobs 疊加到既定 Runtime base，並在不改 Publisher、Runtime authority 與既有控制面的前提下通過完整回歸。

可改範圍｜只可新增本 Review 卡與唯一 review output 目錄；所有產品碼、測試、規格、既有卡片與 evidence 唯讀。

驗收證據｜固定 SHA／clean worktree／allowlist、逐 finding 可重現證據、獨立完整 suite、blob equality、`git diff --check`，最後只能交付 `REVIEW_GO`、`REVIEW_NO_GO` 或 `BLOCKED`。

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：Writer vNext Integration-003 獨立 Review
- 正在做什麼：從固定 candidate 做組成、correctness、regression、控制面與測試缺口審查。
- 現在狀態：`ready`；正式內容服務仍為 `0/4`，production 維持 `NO-GO`。

## 固定來源與進場條件

1. Review source commit 必須以 candidate `1da55d6fc6b233e008ffff5959f54801a8b927eb` 為 parent，且相對 parent 只能新增本卡；不符立即 `BLOCKED / SOURCE_MISMATCH`。
2. Candidate parent 必須正是 `cbed615c9c16a03b4d3ccfcf816d9901feea0ed9`。
3. 先做 CodeGraph 任務語意查詢；若無結果或失敗，才以固定 Git objects 與限域 `rg`／source inspection 補證。
4. Review 對象只限 `cbed615..1da55d6` 的 46 個 changed files及它們直接呼叫的既有 seam；候選不可變。
5. Spec axis 以 Integration-002／Integration-003 卡、Writer vNext contract 與 architecture invariants 為準；Standards axis 以 repo 契約、fail-closed、單一 control plane、可重現性與維護性為準，兩軸不得互相抵銷。
6. 只有可重現 P0/P1 或明確 production safety risk 可阻擋；P2/P3 必須列為 residual，不可單獨導出 `REVIEW_NO_GO`。

## 必審問題

### RQ-1｜Composition identity

- `git diff --name-status cbed615..1da55d6` 必須正好 46 列：37 個 Writer overlay 路徑，加 9 個 Integration-003 evidence 路徑；全部是新增檔。
- 37 個 overlay 路徑必須逐一與 `c7ad4881eabc47cbf43e5053f1ac79d7e70af546` blob 相等，無漏檔、額外檔、rename、delete 或內容漂移。
- Integration evidence 必須與實際 Git objects、測試結果及 host-capacity 記錄一致，不得把 evidence 當成 source identity 的替代品。

### RQ-2｜Runtime 與 Publisher 不變性

- `scripts/agy_content_publisher.py` 及既有 Runtime authority、manifest、activation、capacity、coordinator 與 runner 路徑必須保持 base bytes。
- 檢查 Writer 新契約是否重複建立 queue、lock、transaction、publisher、manifest、runtime activation 或第二套控制面。
- 新 Writer 元件不得靠 stale Writer tree、merge resolution、machine-specific absolute path 或 production state 才能成立。

### RQ-3｜Writer contract 與 orchestration correctness

- 審查 editorial contract 的輸入／輸出、錯誤分類、trace/correlation、determinism、fallback 與 fail-closed 行為是否符合既定 architecture invariants。
- 確認 orchestration 設計與 implementation surface 一致，沒有文件宣稱已接線但 public call chain 尚未存在的 production-ready 誤導。
- 找出可達的 compatibility regression、未受約束資料穿透、語言／SEO／發布邊界錯置或測試只證 private helper 的情況。

### RQ-4｜Evidence 與測試可信度

- 獨立重跑全部 10 個受影響 test groups，不可只引用實作者的 `412 passed`。
- 檢查測試是否涵蓋 public behavior、負向路徑與既有 Publisher/Runtime regression；mock、自填 receipt 或單次終態不得單獨證明通過。
- 任何容量失敗先區分 host capacity 與 source defect；不得因環境噪音擅改候選。

## 獨立驗證矩陣

至少保存命令、exit code、摘要與關鍵 assertions：

```bash
git rev-parse HEAD
git rev-parse HEAD^
git rev-parse 1da55d6fc6b233e008ffff5959f54801a8b927eb^
git diff --name-status cbed615c9c16a03b4d3ccfcf816d9901feea0ed9..1da55d6fc6b233e008ffff5959f54801a8b927eb
git diff --check cbed615c9c16a03b4d3ccfcf816d9901feea0ed9..1da55d6fc6b233e008ffff5959f54801a8b927eb
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

另需用 Git object comparison 產出 37/37 overlay equality、46-file 分類、Publisher/base equality 與 forbidden-path 掃描。不得操作 network、production 或服務。

## Finding 契約

每個 finding 必須包含：`finding_id`、`severity`、`axis`、`category`、`path:line`、觸發條件、最短可重現證據、風險、建議修法、validation gap、confidence。先列 findings；找不到阻擋問題時明確寫「未發現阻塞問題」。

- `P0`：資料破壞、資安事故、錯誤 production mutation／部署。
- `P1`：核心契約違反、正式 call chain 錯接、控制面分叉、重要 regression 或錯誤放行。
- `P2`：可控邊界缺口、非主要相容性或測試缺口。
- `P3`：維護性與非阻塞改善。

## Verdict 與交付

- `REVIEW_GO`：無 P0/P1，Spec axis 與 Standards axis 均通過；列 residual P2/P3，並明示正式服務仍 `0/4`、production 仍 `NO-GO`。
- `REVIEW_NO_GO`：至少一個可重現 P0/P1 或 production safety risk；每個 blocker 都要有最短 reproducer 與精確 repair boundary。
- `BLOCKED`：來源不符、關鍵環境無法重現或需要 contract expansion；不得把未執行測試本身當 finding。
- 寫入 `review-report.md`、`verification-receipt.md`、`findings.json`（無 finding 時為空陣列）及必要的限域測試輸出，再建立只含 allowlist 新檔的 review-only commit，交付 commit SHA 與 clean `git status --short`。
- 不得 Repair、merge、push、deploy、publish、production、canary、tag、launchctl、啟停服務或宣稱 production ready。
