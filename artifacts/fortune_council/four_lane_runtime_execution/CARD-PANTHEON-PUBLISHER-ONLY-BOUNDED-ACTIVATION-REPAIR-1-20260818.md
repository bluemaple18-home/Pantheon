---
id: CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-REPAIR-1-20260818
chain_id: PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-20260818
parent_card_id: CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-REVIEW-20260818
role: repair
cycle: 1
status: ready
type: repair
thickness: standard
risk: high
model: gpt-5.6-terra
reasoning: medium
model_reason: 唯一 P1 finding 已有可重現腳本與固定修復邊界，屬 bounded Repair；依路由用 Terra medium，Review 標準不降級。
base_candidate_sha: 482ae14d90d9b632e2cfa705e1fac00ffc3bc651
review_evidence_sha: e0cc146026e802d7415a03f41be5196afda22ea9
blocking_findings:
  - PANTHEON-PUBLISHER-ONLY-REVIEW-F001
ownership:
  - scripts/install_agy_content_publisher_launchd.sh
  - scripts/install_agy_gemini_coordinator_launchd.sh
  - scripts/pantheon_content_runtime_manifest.py
  - tests/test_agy_content_publisher.py
  - tests/test_agy_gemini_coordinator.py
  - tests/test_pantheon_content_runtime_manifest.py
  - .work/CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-REPAIR-1-20260818/**
forbidden_scope:
  - 修 F001 以外問題、重構 aggregate activation、改 Writer／lane／queue／文章／Publisher selection semantics
  - production activation、runtime promotion、LaunchAgent reload、發布、tag 或 push
  - 刪除或弱化 stage receipt、max-runs=1、barrier、manifest identity、rollback 或其他六服務不變契約
verification:
  - stale／missing／extra publisher-exact-run-id receipt 與 plist child args 不一致時，任何 launchctl mutation 前 fail closed
  - exact-run receipt 與 plist args 一致時可通過 preflight；兩者皆無 exact-run 時也可通過
  - 既有 max-runs、barrier、aggregate activation-only、rollback 與其他六服務不變測試持續通過
  - 原 Reviewer repro 由 fail 轉 pass、受影響 pytest、bash -n、git diff --check
evidence_path: .work/CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-REPAIR-1-20260818/
---

# Repair-1：綁定 exact-run stage receipt 與 Publisher plist

## 工作名稱 → 正在做什麼 → 現在狀態

修復 Publisher exact-run receipt drift → 只關閉 `F001` 並保留原 bounded activation 契約 → `READY / REPAIR-1`

## Root Question

如何以最小修正，讓 `publisher-exact-run-id` stage receipt 與 staged Publisher plist 的 child args 完整一致，避免 stale／missing／extra receipt 在 Publisher-only activation 前置驗證中被漏掉？

## 固定 Finding

- `PANTHEON-PUBLISHER-ONLY-REVIEW-F001`（P1）：stage 存在 stale `publisher-exact-run-id`，但 Publisher plist 沒有 `--exact-run-id` 時，candidate 仍回 0 並執行 bootout/bootstrap。
- Repro：`.work/CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-REVIEW-20260818/reproduce_stale_exact_receipt.py`。

## 執行契約

1. 先重跑 Reviewer repro，確認 RED。
2. 以正式 manifest／installer contract 比對三態：receipt+plist 同值、兩者皆無、任一缺失／多出／值不同。
3. 所有 mismatch 必須在 backup、install、bootout、bootstrap 與 Publisher child I/O 前 fail closed。
4. 只做關閉 F001 的最小 code/test 變更；不得處理 APF-004 backlog 或其他 residual。
5. 重跑原 Publisher-only tests、Reviewer repro、受影響回歸、`bash -n`、`git diff --check`。
6. 交付 repair candidate SHA、changed files、RED/GREEN、F001 regression ID、production mutation=`0`、evidence path。

## 停損

- 同 blocker 第三次停止。
- 若必須改 Publisher selection、queue、production runtime 或重寫 aggregate engine，回 `BLOCKED / SCOPE_EXPANSION`。
- Repair 不得自稱 GO；完成後回原 Reviewer thread targeted re-review。
