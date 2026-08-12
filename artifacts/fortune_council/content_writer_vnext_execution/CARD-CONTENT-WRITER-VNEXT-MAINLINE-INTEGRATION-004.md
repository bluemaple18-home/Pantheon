---
id: CARD-CONTENT-WRITER-VNEXT-MAINLINE-INTEGRATION-004
card_id: CARD-CONTENT-WRITER-VNEXT-MAINLINE-INTEGRATION-004
status: ready
execution_authorized: true
production_authorized: false
type: integration
chain: PANTHEON-WRITER-VNEXT-ORCHESTRATION
chain_id: PANTHEON-WRITER-VNEXT-ORCHESTRATION
role: implementation
cycle: 4
strictness: strict
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定 main SHA、已驗收候選 SHA 與 REVIEW_GO 證據的高影響 Git 整合；契約與驗收已固定，沒有未解架構 fork。
required_base_ref: main
required_base_sha: fe91f3f7fd96d57791b569022fad06f7a3b3c497
required_candidate_sha: 6f9aa59804a97a71d96fabf32cd6829e2f84918c
required_review_commit: 1faf26aa18baa02ead68cf49cd8bfc17deb6685c
required_review_verdict: REVIEW_GO
required_source_ref: codex/pantheon-writer-vnext-mainline-integration-004-source-202-20260811-105104
source_kind: branch
ownership: 在隔離 worktree 將已驗收 Writer vNext 候選整合到精確 main 基底，產出可供主線複審的 merge candidate；不得更新 main ref。
allowlist:
  - artifacts/fortune_council/content_writer_vnext_execution/CARD-CONTENT-WRITER-VNEXT-MAINLINE-INTEGRATION-004.md
  - immutable-git-object-set: merge-base(fe91f3f7fd96d57791b569022fad06f7a3b3c497,6f9aa59804a97a71d96fabf32cd6829e2f84918c)..6f9aa59804a97a71d96fabf32cd6829e2f84918c
  - immutable-main-object-set: merge-base(fe91f3f7fd96d57791b569022fad06f7a3b3c497,6f9aa59804a97a71d96fabf32cd6829e2f84918c)..fe91f3f7fd96d57791b569022fad06f7a3b3c497
  - artifacts/fortune_council/content_writer_vnext_execution/integration/writer_vnext_mainline_integration_004/**
forbidden_scope:
  - 更新 refs/heads/main、使用者目前 checkout 或其他既有 worktree
  - 引入不屬於兩個固定 parent Git object set 的產品碼、設定、內容或測試變更
  - 對產品碼衝突自行設計新行為；任何產品碼衝突一律 BLOCKED
  - 改寫、壓平、squash 或丟棄既有 candidate／review／repair lineage
  - 自行 Review、另開 task、push、deploy、publish、canary、tag、network、launchctl 或服務啟停
integration_output: artifacts/fortune_council/content_writer_vnext_execution/integration/writer_vnext_mainline_integration_004/
traces_to:
  - WVO-SLICE-001
  - WVO-INV-011
  - WVO-INV-012
---

# Writer vNext 主線整合 004：固定候選併入精確 main 基底

## 五行派工卡

任務 ID｜`CARD-CONTENT-WRITER-VNEXT-MAINLINE-INTEGRATION-004`；只產出隔離的主線整合候選。

派工對象｜獨立 Integration；`GPT-5.5 high`；使用 clean worktree，不沿用 Reviewer／Repair task。

任務目的｜把已經 Repair 與原 Reviewer 複審通過的 Writer vNext 候選，安全併入固定 main SHA。

可改範圍｜兩個固定 Git parent 所能推導的 merge 結果、本卡與唯一 integration evidence 目錄。

驗收證據｜exact lineage、conflict 分類、雙 parent merge commit、10 組 affected suite、reproducer、allowlist、`git diff --check` 與 clean state。

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：整合 Writer vNext 驗收候選
- 正在做什麼：在隔離 worktree 將固定候選合併到精確 main 基底，保留完整 lineage。
- 現在狀態：`ready`；尚未更新 main，正式內容服務仍 `0/4`，production 維持 `NO-GO`。

## 固定輸入與依賴

- main base：`fe91f3f7fd96d57791b569022fad06f7a3b3c497`
- accepted repair candidate：`6f9aa59804a97a71d96fabf32cd6829e2f84918c`
- final re-review commit：`1faf26aa18baa02ead68cf49cd8bfc17deb6685c`
- final verdict：`REVIEW_GO`
- resolved finding：`WVNI3-REVIEW-001`
- merge base：必須由 Git 重新計算並等於 `36845c9052546e8ee732f54ea1aa8765f552bde1`
- main-only commits：必須正好 1 個；candidate-only commits：必須正好 25 個。

Blocking edges：候選 SHA、Reviewer `REVIEW_GO`、source HEAD、source clean、merge-base 與 lineage 任一不符，禁止執行 merge。

Frontier：上述唯讀 preflight 全部成立後，才允許在本 worktree 建立隔離 merge candidate。

## 唯一整合契約

1. 完整讀本卡、Repair receipt 與 `rereview-001` receipt；先做 task-semantic CodeGraph query，再以固定 Git objects 和原始碼限域確認。
2. 進場必須驗證：`HEAD` 為含本卡的 source commit、`HEAD^` 為固定 main base、worktree clean、候選與 review commit 可讀、review commit parent 為候選。
3. 以 `git merge --no-ff --no-commit 6f9aa59804a97a71d96fabf32cd6829e2f84918c` 建立 merge 結果；不得 rebase、squash、cherry-pick 25 個 commit 或改寫 lineage。
4. 若沒有 conflict，直接進驗證。若只有 docs／card／evidence add-add 或文字衝突，只能保留雙方既有資訊並記錄 object-level resolution；不得改變任何既有 verdict 或 receipt。
5. 若任何產品碼、測試、設定、manifest、Publisher、Runtime、coordinator、runner、capacity、queue 或 lock 路徑發生 conflict，立即 `git merge --abort` 並交付 `BLOCKED`；不得自行設計解法。
6. Merge 結果中的非 evidence 路徑必須全部能由兩個固定 parent 的三方 merge 推導；integration task 只可額外新增唯一 integration evidence 目錄。
7. 驗證全部通過後建立單一雙 parent merge commit；第一 parent 必須是含本卡的 source commit，第二 parent 必須是 `6f9aa598...`。不得更新 `main` ref。

## 驗證矩陣

先執行原 finding reproducer與 targeted：

```bash
PYTHONDONTWRITEBYTECODE=1 <repo-root>/.venv/bin/python \
  artifacts/fortune_council/content_writer_vnext_execution/review/writer_vnext_integration_003_review_001/manifest-opt-in-reproducer.py
PYTHONDONTWRITEBYTECODE=1 <repo-root>/.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_agy_editorial_contracts.py
```

再跑完整受影響 10 組：

```bash
PYTHONDONTWRITEBYTECODE=1 <repo-root>/.venv/bin/python -m pytest -q -p no:cacheprovider \
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

另需驗證：

- `git diff --check` 對 merge result 與最後 commit 均通過。
- Reviewer 的 `findings.json` 與 `generation-ledger.json` 可解析，verdict 為 `REVIEW_GO`、finding disposition 為 `RESOLVED`。
- merge tree 同時保留 main-only 15 個路徑與 candidate 的 996-path object set；任何意外刪除或未解 conflict 為 `BLOCKED`。
- `git show --pretty=%P -s HEAD` 最終回傳精確兩個 parent，順序正確。
- final worktree clean；不得產生 pyc、pytest cache 或 allowlist 外 artifact。

## Evidence 與交付

至少寫入：

- `lineage-receipt.json`
- `merge-transcript.txt`
- `conflict-classification.json`
- `changed-files.json`
- `verification-receipt.md`
- `test-output.txt`

全部通過才建立單一 integration merge commit。回報 integration candidate SHA、兩個 parent SHA、conflict 數量與分類、changed files、targeted/full suite/reproducer/diff-check、clean state，以及唯一 verdict：`INTEGRATION_CANDIDATE_READY_FOR_REVIEW` 或 `BLOCKED`。

交付後必須回到主線；不得自行把候選合併到 `main`、不得自行 Review 或啟動 production。
