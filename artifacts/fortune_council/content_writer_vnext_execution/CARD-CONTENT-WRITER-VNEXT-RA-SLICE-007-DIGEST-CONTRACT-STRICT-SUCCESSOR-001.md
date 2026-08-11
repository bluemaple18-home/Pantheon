---
id: CARD-CONTENT-WRITER-VNEXT-RA-SLICE-007-DIGEST-CONTRACT-STRICT-SUCCESSOR-001
status: ready
chain_id: CONTENT-WRITER-VNEXT-RUNTIME-ACTIVATION
role: implementation
cycle: 2
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定 P1 契約的高影響 evidence 修復；需以可攜、版本化 digest domain 讓 committed sample 可獨立重算，適用 strict/core-bounded 跑道。
traces_to:
  - RA-CHECKPOINT-B
  - STORAGE-CAPACITY-SAFETY-GATE-3
  - STORAGE-CAPACITY-SAFETY-GATE-5
supersedes:
  - CARD-CONTENT-WRITER-VNEXT-RA-SLICE-007-CAPACITY-PREFLIGHT@1e5a447b8c52ec4e07a225ecef64cecb103b0815
authorized_scope_expansion: user-approved-2026-08-11
depends_on:
  - RA-SLICE-007-RE-REVIEW-NO-GO@1e5a447b8c52ec4e07a225ecef64cecb103b0815
---

# Writer vNext RA007：Digest Contract Strict Successor

## 目標

只修 RA007 committed capacity evidence 的 `measurement_digest` 可重算契約。保留既有量測值、容量判定與 `production NO-GO`；不得重新量測、擴大容量恢復工作或執行 cleanup。

## Root finding

- 固定 finding：`RA007-DIGEST-NOT-RECOMPUTABLE-P1`。
- 證據：`ra_slice_007_capacity_preflight_re_review/findings.json`。
- 問題：兩筆 digest 無法由 committed evidence 重建；缺 versioned domain、完整 canonical projection 或等價 canonical receipt。

## Ownership

- 本卡 owner：strict successor implementation。
- 主線保留 dispatch、Review、Repair generation、整合與最終判定。
- 沿用 chain 既有唯一 Reviewer／Repair threads；禁止建立 replacement 或第二個 role identity。
- 前一張 standard 卡維持 `BLOCKED / REVIEW_REPAIR_LIMIT`；本卡是使用者明確授權的 strict successor，不回寫或偽造前卡狀態。

## Allowlist

只可修改：

- `artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_007_capacity_preflight/resource-snapshot.json`
- `artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_007_capacity_preflight/capacity-verdict.md`
- `artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_007_capacity_preflight/verification.txt`

若 verdict 文字不需同步，保持不變。不得修改 inventory、cleanup plan、原 review、re-review 或其他 artifacts。

## 修復契約

1. 保留兩筆既有 sample 的量測值與 3 秒 interval；禁止重新執行 host probe。
2. 在 committed `resource-snapshot.json` 明示版本化 digest contract，至少包含：domain/version、algorithm、UTF-8 serialization、key ordering、separator、digest 欄位排除規則、完整 input projection。
3. 每筆 `measurement_digest` 必須可只靠同一 committed JSON 重算；禁止依賴 temp file、本機絕對路徑、未提交 raw receipt、時間變動或外部狀態。
4. digest 格式固定為 `sha256:<64 lowercase hex>`。兩筆 digest 必須與契約重算完全一致。
5. `verification.txt` 保存可攜的重算步驟、實際 expected/actual 與 PASS；不得保存本機絕對路徑。
6. 容量 verdict 保持 `NO-GO`。本卡不新增 cleanup 權、不宣稱 Checkpoint B 或 production readiness 通過。

## 禁止範圍

- 禁止 cleanup、刪除、prune、archive、push、deploy、tag、production、canary、正式產文、network write、服務啟停。
- 禁止修改 code、config、ai-core、card、inventory、cleanup plan、Reviewer evidence。
- 禁止新增 task、Reviewer、Repair 或 sub-agent。
- 禁止以重新取樣掩蓋 committed evidence 缺口。

## 驗證

- JSON parse。
- 由 committed `resource-snapshot.json` 依內嵌 contract 獨立重算兩筆 digest；兩筆皆 exact match。
- 舊四項 runtime 指標仍非空；sample interval、reserve、deficit、delta 算術不回歸。
- `rg` 確認共享 evidence 無 `/Users/`、`/private/`、其他專案內容。
- changed-file allowlist exact match；`git diff --check` 通過。
- 單一 candidate commit，父為本卡 source commit；worktree clean。

## Stop conditions

- 需要新 host probe、外部狀態或未提交檔案才能重算。
- 任一既有量測值、容量判定、inventory 或 cleanup plan 必須變更。
- 任一禁止操作成為必要條件。
- 同一 blocker 第 3 次失敗。

## 交付

只回：

- `RA007_DIGEST_CONTRACT_READY_FOR_REVIEW` + candidate SHA + `NO-GO`；或
- `BLOCKED` + blocker evidence。
