---
id: CARD-PANTHEON-PROMOTION-PRESERVE-RUN-ID-RCA-20260818
chain_id: PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-20260818
parent_card_id: CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-PRODUCTION-CANARY-20260818
role: diagnostic
cycle: 1
status: ready
type: readonly_diagnostic
thickness: minimal
risk: medium
model: gpt-5.6-luna
reasoning: medium
model_reason: promotion plan 已 fail-closed；只需判定 preserve-run-id 是排序、重複或格式問題並重跑唯讀 plan，使用 Luna medium 節省。
blocked_canary_evidence_sha: ece0a6a3c11b228d380c0a30eb10f517dbb55803
ownership:
  - .work/CARD-PANTHEON-PROMOTION-PRESERVE-RUN-ID-RCA-20260818/**
forbidden_scope:
  - 修改 source、tests、rules、queue/state/transaction、promotion gate 或 production runtime
  - push、promotion apply/finalize、LaunchAgent mutation、發布、tag、另開 Repair/Reviewer/canary
verification:
  - 從 blocked request 與 live queue唯讀重建原 preserved_run_ids
  - 分別證明 sortedness、duplicate與 SAFE_ID_PATTERN invalid IDs
  - 用 canonical sorted unique IDs 重跑同一 formal promotion plan；plan不得產生 production mutation
  - git diff --check、production mutation=0、evidence commit、worktree clean
evidence_path: .work/CARD-PANTHEON-PROMOTION-PRESERVE-RUN-ID-RCA-20260818/
---

# Promotion preserve-run-id RCA

## Root Question

`preserved run ids are invalid` 是 run ID 字元格式錯、輸入未排序、輸入重複，還是其他 request drift？

## 已知事實

- `SAFE_ID_PATTERN = ^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`，明確允許 hyphen。
- `_validate_request_shape` 同時要求 `tuple(sorted(set(ids))) == ids` 與每筆符合 pattern；錯誤訊息不區分原因。
- 原 canary 已 capacity PASS、readiness READY、origin/main fast-forward；promotion plan 在任何 actor/manifest/stage mutation 前 NO-GO。

## 執行

1. 讀 blocked evidence `ece0a6a3...` 與原 plan request；抽 preserved IDs 原始順序。
2. 輸出：count、sorted、duplicate IDs、invalid IDs、第一個 order inversion。
3. 僅建立 canonical `sorted(set(ids))` 參數，其他 request 欄位完全不變。
4. 重跑正式 `promotion plan`；禁止 apply/finalize。
5. 結論：
   - `INPUT_CANONICALIZATION_ONLY`：canonical plan READY；交 exact args/order，回原 canary。
   - `SOURCE_REPAIR_REQUIRED`：仍 NO-GO；交唯一 validator/request seam與 RED command。
   - `LIVE_DRIFT`：queue/request identity已變；交 drift，不猜修法。

## 停損

- 同 blocker第三次停止。
- 不得把 plan READY 當 promotion完成。
- 不手改 queue，不放寬 pattern，不進 production mutation。

## 交付

- verdict與唯一根因
- original/canonical ID diagnostics
- formal plan command/status/digest
- production mutation=0
- evidence commit SHA
