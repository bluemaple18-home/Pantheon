---
id: CARD-PANTHEON-G8-PRODUCTION-PREACTIVATION-RECONCILIATION-REVIEW-RETRY-1-20260820
chain_id: PANTHEON-G8-PRODUCTION-PREACTIVATION-RECONCILIATION-20260820
parent_card_id: CARD-PANTHEON-G8-PRODUCTION-PREACTIVATION-RECONCILIATION-REPAIR-20260820
supersedes: CARD-PANTHEON-G8-PRODUCTION-PREACTIVATION-RECONCILIATION-REVIEW-20260820
role: reviewer
cycle: 1
status: ready
type: source_review
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: Production 邊界需獨立檢查 fail-closed、selector 隔離與零 mutation，使用 GPT-5.5 high。
candidate_sha: 0894ace3b8
ownership:
  - artifacts/fortune_council/four_lane_runtime_execution/g8_production_preactivation_reconciliation_review_retry_1_20260820/**
forbidden_scope:
  - 修改任何 source、test、production、queue/state/transaction、registry、manifest、plist 或 git refs
  - production activation、publisher、promotion、installer、launchctl、push、tag
verification:
  - 獨立審查 authority ancestry/allowlist、old-live→new-stage transition、selector isolation、mutation tripwire
  - 重跑新測試與受影響 collector/capacity tests
  - 驗證 reject/invalid selector 只寫 temporary snapshot，不碰 production roots
  - git diff --check 通過，candidate source tree 不變
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/g8_production_preactivation_reconciliation_review_retry_1_20260820/
---

# G8 production preactivation reconciliation review retry 1

## 工作名稱 → 正在做什麼 → 現在狀態

獨立審查 G8 preactivation reconciliation → 驗證 candidate `0894ace3b8` 的 fail-closed 與零 production mutation → `READY TO DISPATCH`

## Root Question

Candidate 是否能在不碰 production roots 的前提下，正確判定 authority、coherent old-live→new-stage 與 current exact selector，並對所有 drift／cardinality／mutation 路徑 fail-closed？

## Retry Cause

前卡在 create request 形成前因缺 `model_reason` 被控制面終止；未建立 formal thread、client thread 或 worktree。本卡補齊 routing 契約，不改 review scope。

## Review Contract

1. Spec axis：逐項對照 Repair 卡契約；不得以測試綠取代 source review。
2. Standards axis：檢查 correctness、regression、security、TOCTOU、temporary snapshot cleanup、跨機路徑與錯誤處理。
3. 特別驗證 `collect_ready_runs` 永遠只收到 temporary queue/state snapshot；production state 已有 ledger/retry/policy rejection 時結果需維持 parity。
4. 以 temporary fixtures 重跑正向與全部負向；執行前後 production queue/state/transaction/lock/git refs/live/staged/manifest digest 必須相同。
5. 只可新增本卡 evidence；不得修改 candidate source/tests。Finding 需含 severity、path:line、觸發條件與修法。
6. Verdict 只可 `GO` 或 `NO-GO`；有 P0/P1、契約缺口或驗證不可重現即 `NO-GO`。

## Required Commands

```text
.venv/bin/python -m pytest -q tests/test_pantheon_g8_production_preactivation.py
.venv/bin/python -m pytest -q \
  tests/test_agy_content_publisher.py::test_collect_ready_runs_skips_reviewer_reject \
  tests/test_agy_content_publisher.py::test_collect_ready_runs_exact_selector_excludes_unlisted_ready_run \
  tests/test_agy_content_publisher.py::test_collect_ready_runs_without_exact_selector_keeps_existing_selection \
  tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_stages_during_manifest_bound_preactivation_transition \
  tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_unsafe_preactivation_transition_cases
git diff --check 0894ace3b8^..0894ace3b8
```

## Stop

- 發現 candidate 需改 source/test：輸出 `NO-GO` finding，回原 Repair task；Reviewer 不修。
- 不得啟動 production canary；即使 `GO` 也只交 reviewer evidence。

## 正式 task 初始 prompt 核心契約

```text
你負責 CARD-PANTHEON-G8-PRODUCTION-PREACTIVATION-RECONCILIATION-REVIEW-RETRY-1-20260820，role=reviewer、cycle=1。先 CodeGraph，失敗才限域 rg。獨立 review candidate 0894ace3b8，只新增本卡 evidence，不得修改 source/tests。驗 authority ancestry+allowlist、coherent old-live→new-stage、temporary selector snapshot parity、mutation tripwire與全部負向 fail-closed；特別確認 collect_ready_runs 不可能收到 production state_root。重跑指定 26 tests與 git diff --check。Verdict 只可 GO/NO-GO；finding 必須含 severity、path:line、觸發條件與修法。禁止 production/remote/git refs/queue/state/transaction/LaunchAgent mutation。
```
