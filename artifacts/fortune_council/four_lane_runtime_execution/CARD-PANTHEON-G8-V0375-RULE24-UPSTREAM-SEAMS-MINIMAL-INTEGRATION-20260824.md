---
id: CARD-PANTHEON-G8-V0375-RULE24-UPSTREAM-SEAMS-MINIMAL-INTEGRATION-20260824
chain_id: PANTHEON-G8-RULE24-SIGNED-EVIDENCE
role: integration
cycle: 1
status: ready
type: strict_bounded_mainline_integration
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 兩條安全核心 seam 已固定 REVIEW_GO，但 accepted branch ancestry 含禁止的舊 composition；需以固定 commit allowlist 做 fail-closed 最小整合。
mainline_base_sha: 4762ab768956300b7f8bdcd1d288c465d6397173
accepted_v0373_tip: c1b38ec30ccd4916ca6f64bd9376d488489d1b00
accepted_v0374_tip: 464592cbcd523321d6100f4935f73beb47cff79b
ownership:
  - scripts/pantheon_writer_vnext_runtime_activation_capacity.py
  - tests/test_pantheon_writer_vnext_runtime_activation_capacity.py
  - scripts/pantheon_rule24_dsse_attestation.py
  - tests/test_pantheon_rule24_dsse_attestation.py
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0375-RULE24-UPSTREAM-SEAMS-MINIMAL-INTEGRATION-20260824-RESULT.md
forbidden_scope:
  - merge accepted branch 或帶入其 ancestry
  - 整合 0af881df、6de8e487、5ca75022ba、d90137815d、d1e1be51aa
  - 帶入舊 signed evidence composition、dispatch、Review、Repair 卡片或既有 RESULT/evidence
  - 修改 ownership 外檔案、既有卡片、registry、metadata、generated pages、sitemap、feed、redirects
  - 建立 composition implementation、Reviewer、Repair、replacement 或下一張卡
  - push、deploy、canary、production mutation、tag、清理 worktree/thread/branch
verification:
  - .venv/bin/python -m pytest -q tests/test_pantheon_writer_vnext_runtime_activation_capacity.py tests/test_pantheon_rule24_dsse_attestation.py
  - git diff --check
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0375-RULE24-UPSTREAM-SEAMS-MINIMAL-INTEGRATION-20260824-RESULT.md
---

# V0375 Rule24 upstream seams 最小整合

## 工作名稱 → 正在做什麼 → 現在狀態

V0375 Rule24 upstream seams 最小整合 → 將 V0373 evaluator bundle 與 V0374 DSSE commit re-authentication 的已驗收變更限域整合 → READY

## Root question

如何只把兩條 `REVIEW_GO` upstream seam 整合到以 `4762ab768956300b7f8bdcd1d288c465d6397173` 為基底的獨立 worktree，不攜入 accepted branch 的舊 composition ancestry？

## 固定 authority

- V0373 accepted tip：`c1b38ec30ccd4916ca6f64bd9376d488489d1b00`；source allowlist：`4185b1c9616d02f9a500cee73a7d49da785cd5ce`、`a7ca0c2d65eeddd46d0e9f05a7b63ccb56a6cda2`。
- V0374 accepted tip：`464592cbcd523321d6100f4935f73beb47cff79b`；source allowlist：`377d0da63f184fa73d26542718fb25b82904a1cc`、`947f781d8e368091ba179c85524249cc49774304`、`1621d49785cada2fd0a3e3ef4b78cf9209020cce`。
- V0373 final verdict：`REVIEW_GO`；13 tests PASS；兩個 P1 已關閉。
- V0374 final verdict：`REVIEW_GO`；63 affected tests PASS、31 focused tests PASS。
- accepted API invariant：會消耗 replay state 或釋放 observer payload 的操作，必須從 original DSSE envelope 與 verifier-owned trust context 在 commit-time 重新 authentication。

## Integration contract

1. 第一拍只讀：確認 cwd、HEAD、clean、獨立 worktree；執行 task-semantic CodeGraph query，再用 Git objects 核對兩個 accepted tips、五個 source allowlist commits、Review authority 與 ancestry。
2. 驗證新 worktree 起點只比 `mainline_base_sha` 多本卡 bootstrap commit；任何其他 tracked delta 立即 `INTEGRATION_BLOCKED`。
3. 禁止 merge/cherry-pick accepted tip 或整段 range。只允許按順序擷取五個 source allowlist commit 的 ownership 內 patch：V0373 `4185b1c...` → `a7ca0c2...`；V0374 `377d0da...` → `947f781...` → `1621d497...`。
4. 每筆先檢查 patch dependency。若 patch 可乾淨套用，以 `cherry-pick --no-commit` 或等價限域方式只保留 ownership 內 source/tests；任何 commit 內既有 RESULT/evidence、卡片或其他檔案不得進 candidate。
5. 若 patch 依賴舊 composition parent、發生 conflict、空 patch或需改 ownership 外檔案，禁止手動吞 conflict。改以 accepted tip 的四個 ownership source/test blobs 與 allowlist commit diff 做 patch-equivalence 重建；仍無法證明等價即停。
6. V0373 與 V0374 分段驗證；兩段都通過後跑共同 suite。只新增本卡 RESULT，記錄 source→integration mapping、實際 changed files、tree/blob equivalence、禁止 commit/ancestry absence、測試與 clean status。
7. 產出單一 candidate commit；final worktree clean。不得自行宣稱 `ACCEPTED`、整合回 main、開 Review 或開 composition。

## Acceptance

- `git diff --name-status <bootstrap>..HEAD` 精確落在 ownership；本卡本身不得被修改。
- 四個 source/test final blobs 或其 patch-equivalence 可由固定 Git objects 重現；不得含 allowlist 外的歷史變更。
- `git log`／patch provenance 證明未整合 `0af881df`、`6de8e487`、`5ca75022ba`、`d90137815d`、`d1e1be51aa`，也未 merge 兩條 accepted branch。
- evaluator 與 DSSE 兩個完整 test files 全 PASS；`git diff --check <bootstrap>..HEAD` PASS。
- RESULT 含 full candidate SHA、bootstrap SHA、source allowlist、驗證命令摘要、剩餘風險；final 回 `DELIVERED_CANDIDATE` 或 `INTEGRATION_BLOCKED`。

## Stop

- fixed object 不可讀、Review authority 不一致、需擴 scope、patch-equivalence 無法證明、測試失敗需修 source/tests：立即 `INTEGRATION_BLOCKED`。
- 同一 blocker 第三次失敗即停；不得開下一張卡、Repair、Review 或 replacement。
