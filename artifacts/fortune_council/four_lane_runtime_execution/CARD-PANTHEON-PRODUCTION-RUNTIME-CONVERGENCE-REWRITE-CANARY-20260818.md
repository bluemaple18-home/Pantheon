---
id: CARD-PANTHEON-PRODUCTION-RUNTIME-CONVERGENCE-REWRITE-CANARY-20260818
chain_id: PANTHEON-FOUR-LANE-PRODUCTION-RECOVERY-20260818
role: implementation
cycle: 1
status: ready
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: production promotion、launchd、Publisher transaction 與單筆發布皆屬固定契約的高回退成本操作。
ownership:
  - .work/CARD-PANTHEON-PRODUCTION-RUNTIME-CONVERGENCE-REWRITE-CANARY-20260818/**
  - production runtime promotion transaction and receipts
forbidden_scope:
  - 修改 source、tests、派工框架、規則、Writer 架構或舊 evidence
  - 手動刪除或改寫 queue、transaction、文章、tag、runtime manifest
  - force push、無界 retry、第二筆 canary、其他 lane 新工作
evidence_path: .work/CARD-PANTHEON-PRODUCTION-RUNTIME-CONVERGENCE-REWRITE-CANARY-20260818/
---

# Production runtime convergence and single rewrite canary

## 工作名稱 → 正在做什麼 → 現在狀態

Production runtime convergence 與 rewrite canary → 對齊 current main/runtime/LaunchAgents，重建 readiness，執行一筆 `rewrite_existing_body` → `READY / USER AUTHORIZED`

## Root Question

能否只用既有正式入口，將 production 收斂到本卡所在 source SHA，並讓第四線一筆 rewrite 完成 Publisher transaction、commit、tag、push？

## 使用者授權

使用者已連續確認「開卡派工監工」，承接前一拍明示範圍：

- production runtime convergence
- LaunchAgents reload／service activation
- current readiness receipt 重建
- 單筆四線故障路徑 canary
- 正常 Publisher commit／tag／push

授權不包含 source repair、queue deletion、手動 transaction 編輯、第二筆 canary 或其他 production 擴張。

## 已鎖定結論

- product root fix 已在 `b711184af27a8624410704f3c086b9150fd2a517`、`db74e966b4ac67d6a4b2acd14b8e8729a339b467`。
- production actor／manifest／plist 仍舊且互不一致；Capacity Guard 為 `STOPPED`，RSS unavailable。
- 舊或未追蹤 readiness package 不具 current authority，不得搬來補 PASS。
- 第四線差異為 `rewrite_existing_body` 的 Publisher transaction 長窗口曾暴露 Coordinator ownership 缺口。
- 不再改派工框架、不再開 RCA、不再補舊 evidence。

## 執行順序

1. 唯讀鎖定正式 task source SHA、`origin/main`、production actor、runtime manifest、LaunchAgents、capacity state、queue、未完成 transaction 與公開 sitemap 基線。
2. 跑受影響測試與 `git diff --check`。任何 source failure → 停止；不得現場改 code。
3. 生成 current、non-production、`canary_created=false` 的兩週期 capacity proof 與七步 capability receipt；必須含 source SHA、script digests、manifest authority、runtime identity、execution line／correlation lineage。
4. 用正式 `production_canary_readiness_gate.py` 驗證。非 `READY`／capacity 非 `PASS` → 停止，不准 promotion 或 canary。
5. 若 `origin/main` 落後，只允許 fast-forward push 本卡 source SHA；禁止 force push。
6. 用 `scripts/pantheon_content_runtime_promotion.py` 正式 plan/apply/postcheck/finalize；保留 rollback bundle。任何 identity、descendant、path、digest、capacity preflight 失敗 → 正式 rollback，停止。
7. 用既有 installer 對齊七個 LaunchAgents 至同一 runtime manifest／identity，reload 後驗 loaded 狀態；排程型 idle 無 PID 可接受，但 identity/path/exit 必須正確。
8. 用正式 Publisher recovery 入口收斂既有未完成 transaction；禁止手動刪除。
9. 從 canonical queue 鎖定一筆既有 `rewrite_existing_body` run；先記錄 exact run ID，再 dry-run；只允許 `--max-runs 1 --exact-run-id <id>` 的一次 normal acceptance。
10. 驗證 Publisher bounded exit 0、lane ownership、transaction closed、queue complete、無重複領取、commit、annotated tag、fast-forward push。Rewrite 不要求 sitemap +1，但須驗公開內容與 sitemap 不退步。
11. 成功後保留既有正常排程 loaded；禁止額外 kickstart。輸出 production receipt 與 exact SHA/run/tag/push evidence。

## 正式入口

- `scripts/pantheon_content_runtime_promotion.py`
- `scripts/pantheon_content_runtime_manifest.py`
- `scripts/pantheon_content_capacity_guard.py`
- `scripts/pantheon_writer_vnext_runtime_activation_capacity.py`
- `scripts/pantheon_writer_vnext_runtime_activation_readiness.py`
- `<ai-core-root>/scripts/production_canary_readiness_gate.py`
- `scripts/install_agy_content_publisher_launchd.sh`
- `scripts/install_pantheon_content_capacity_guard_launchd.sh`
- 現有四 lane／Coordinator installer
- `scripts/agy_content_publisher.py` 的正式 recovery／exact-run 介面

若正式入口不支援必要動作，立即停止。不得用 shell 手工改 production state 模擬成功。

## 停損

- promotion 前任何 gate 非 PASS／READY：不動 production。
- promotion 後首次新 blocker：停止 acceptance；若 transaction 尚未 finalize，使用同一正式 transaction rollback。
- ownership 混線、重複領取、資料遺失風險：卸載七服務，保全現場，停止。
- 同一 blocker 最多三次；不得改錯誤名稱繼續。
- 不建立新卡、Reviewer、Repair 或流程層；只交回 exact blocker。

## 完成證據

- source／origin/main／actor／manifest／plist identity exact match。
- current capability `READY`；capacity `PASS`；`canary_created=false` 的 pre-canary receipt。
- 七服務 loaded；Capacity Guard current PASS。
- 舊 transaction 由正式 recovery 收斂。
- 恰好一筆 `rewrite_existing_body` run complete。
- Publisher exit 0；transaction closed；commit、annotated tag、fast-forward push 成功。
- 無假 active、跨 lane、重複領取或未完成 Publisher transaction。
- evidence commit SHA；worktree clean；production mutation receipt。
