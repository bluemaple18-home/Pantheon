---
id: CARD-PANTHEON-PUBLISHER-SCHEDULER-SAFE-ACTIVATION-CANARY-20260818
chain_id: PANTHEON-PUBLISHER-SCHEDULER-SAFE-ACTIVATION-20260818
role: implementation
cycle: 1
status: ready
type: production_canary
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 已固定 barrier-first 兩階段 activation 契約，但涉及 runtime promotion、LaunchAgents 與 production scheduler 恢復，使用 GPT-5.5 high；不需 5.6。
ownership:
  - .work/CARD-PANTHEON-PUBLISHER-SCHEDULER-SAFE-ACTIVATION-CANARY-20260818/**
  - production runtime promotion transaction and receipts
  - Pantheon seven-service activation transaction and receipts
forbidden_scope:
  - 修改 source、tests、rules、派工框架、Writer 架構、文章、registry、sitemap、queue 或 transaction 內容
  - 手動建立或刪除 barrier、plist、queue item、transaction、tag、branch 或 content commit
  - force push、非 fast-forward push、第二筆 content canary、無界 retry、另開 replacement／Repair／Reviewer task
  - 用舊 readiness、舊 capacity 或狀態文案冒充 current source 的 PASS
verification:
  - current source 的 capability gate READY 且 canary_created=false
  - current source 的 capacity gate PASS，包含兩週期、回收與 stop-loss
  - activation-only 建立 matching barrier，七服務 child I/O 為零
  - normal activation 前 scheduler-equivalent dry-run 選取數為零
  - matching barrier normal activation 後七服務 loaded，Publisher scheduler restored，無新文章／transaction／tag／push
  - git diff --check、production mutation receipt、evidence commit、worktree clean
evidence_path: .work/CARD-PANTHEON-PUBLISHER-SCHEDULER-SAFE-ACTIVATION-CANARY-20260818/
---

# Publisher scheduler safe activation canary

## 工作名稱 → 正在做什麼 → 現在狀態

恢復 Publisher scheduler 安全啟動 → 將已驗收的 barrier-first 修正推進 production，執行兩階段 activation canary → `READY / USER AUTHORIZED`

## Root Question

能否只用既有正式入口，把 production runtime 收斂到本卡 source SHA，先以 `--activation-only` 建立 matching barrier 且保持 Publisher child I/O 為零，再於 scheduler-equivalent dry-run 選取數為零時執行 normal activation，恢復 Publisher scheduler 而不產生第二筆文章發布？

## 已知事實

- 前一張 rewrite canary 已完成一筆正式發布，但終態為 `PARTIAL`：Publisher scheduler 仍 absent。
- 舊 active translate 已用正式 Coordinator exact cycle 收斂為 failed。
- Publisher safe activation candidate 已通過獨立 Review 並整合主線：normal activation 在任何 launchctl mutation 前要求 matching activation barrier；activation-only 維持零 child I/O。
- 使用者已明確授權本張 production activation canary。
- 本卡不授權第二筆 content canary；本次 canary 驗證對象是 runtime／LaunchAgent activation transaction。

## 執行順序

1. 唯讀鎖定本卡 source SHA、`origin/main`、production actor、runtime manifest、七個 LaunchAgents、capacity guard、queue、transaction、tag 與公開內容基線。
2. 跑受影響測試、shell syntax、`git diff --check`。任何 source failure 立即停止，不得現場修 code。
3. 以本卡 source 重建 current、non-production、`canary_created=false` 的七步 capability receipt：`create → run → select → publish → transaction → tag → push`；每步保留正式入口、I/O、identity/correlation、PASS 與 BLOCKED evidence。
4. 重建 current capacity proof：兩個完整週期、host reserve、RSS/swap、檔案與 bytes 上限、cleanup reclaim、stop-loss negative。官方 readiness 非 `READY` 或 capacity 非 `PASS`，停止且不碰 production。
5. 僅允許將 `origin/main` fast-forward 到本卡 source SHA；禁止 force push、merge commit 或內容變更。
6. 用 `scripts/pantheon_content_runtime_promotion.py` 正式 `plan → apply → postcheck → finalize` 將 actor／manifest 收斂至 exact source SHA；保留 rollback bundle。任何 gate 或 identity drift 立即 rollback／停止。
7. 跑七服務 aggregate installer preflight；只能使用既有 installer 與 runtime manifest authority。
8. 執行 aggregate `--activation-only`。驗證 matching barrier、七服務 loaded、activation-only mode、Publisher child I/O 零次、無 queue／transaction／article／tag／push mutation。
9. 在 normal activation 前，用 Publisher 正式入口及 scheduler 等價參數執行 dry-run。選取數必須為零，且不得建立 transaction。只要會選到任何 run，維持 activation-only／安全停機，回報 `BLOCKED / CONTENT_SELECTION_NOT_ZERO`，禁止 normal activation。
10. 僅在第 9 步零選取時，使用同一 matching barrier 執行 aggregate normal `--activate`；不得手動改 barrier 或 plist。
11. 驗證七服務 loaded、Publisher scheduler present、runtime／manifest／plist identity 一致；對比基線確認沒有新文章、transaction、content commit、tag 或 push。
12. 寫入 production mutation receipt 與 evidence commit。結論只能是 `GO` 或帶 exact blocker 的 `BLOCKED/PARTIAL`，不得模糊宣稱完成。

## 正式入口

- `scripts/pantheon_content_runtime_promotion.py`
- `scripts/pantheon_content_runtime_manifest.py`
- `scripts/pantheon_content_capacity_guard.py`
- `scripts/pantheon_writer_vnext_runtime_activation_capacity.py`
- `scripts/pantheon_writer_vnext_runtime_activation_readiness.py`
- `<ai-core-root>/scripts/production_canary_readiness_gate.py`
- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `scripts/install_agy_content_publisher_launchd.sh`
- `scripts/install_pantheon_content_capacity_guard_launchd.sh`
- `scripts/agy_content_publisher.py` 的正式 dry-run／scheduler 介面

若正式入口不支援上述 bounded 行為，立即停止；不得以 shell 手工操作 production state 補洞。

## 停損

- promotion 前任一 gate 非 PASS／READY：零 production mutation。
- activation-only 不是零 child I/O、barrier 不 matching、七服務 identity 不一致：rollback／停止。
- dry-run 選取數非零：不做 normal activation，不發布第二筆內容。
- normal activation 出現文章、transaction、tag、push 或非預期 content commit：立即停止 Publisher scheduler，保全現場，不做重試。
- 同一 blocker 最多三次；第三次立即停止，不改名繼續。

## 完成證據

- exact source／origin/main／actor／manifest／plist identity。
- current capability `READY`、capacity `PASS`、`canary_created=false`。
- activation-only matching barrier 與 Publisher child I/O `0`。
- normal activation 前 scheduler-equivalent dry-run selected `0`。
- normal activation 後七服務 loaded，Publisher scheduler present。
- 文章、queue、transaction、content commit、tag、push 前後無新增。
- evidence commit SHA、production mutation receipt、worktree clean。
