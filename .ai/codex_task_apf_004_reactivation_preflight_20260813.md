# APF-004-REACTIVATION-PREFLIGHT-001

- 目標：基於已核准整合 commit `8fea7a47a86a97e0dd1eb6af94df1ba6056e7a17`，只讀重驗 repo／runtime／stage／capacity／六個 service 狀態，產出唯一 exact live reactivation payload；`traces_to: US-004, FR-012, FR-014, SC-001, SC-003, SC-008`。
- 依賴：Repair `e5ce8491ce320ff30ae18717ca45a82ae86b434c` 已由原 Reviewer `REVIEW_APPROVED`；integration `8fea7a47...` 已通過 matrix `5 passed`、affected suite `31 passed, 151 deselected`、bash／DBG／diff gates；blocking edges 已清空，本卡是唯一 frontier。
- 可做：CodeGraph 後限域讀原始碼；唯讀核對 `origin/main`、integration SHA、runtime actor/manifest digest、保留 stage identity、LaunchAgent loaded/unloaded、queue/state bytes、host free/RSS/swap、installer preflight；寫本卡與 `.ai/evidence/apf_004_reactivation_preflight_001.md`。不得輸出 secrets 或絕對跨機路徑。
- 禁止：不得 commit source code；不得 push/merge main、install、activate、bootstrap/kickstart/bootout、改 plist/manifest、刪 stage、呼叫外部模型、publish/transaction/tag/deploy/schedule。任何 prerequisite 不一致立即 `NO-GO`，不得自行修復或重試 live action。
- 驗收：回 `REACTIVATION_PAYLOAD_READY | NO-GO | BLOCKED`；READY 必須包含 exact source SHA/digest、stage generation/correlation、命令與 env allowlist、預期 receipt、rollback/stop、一次性執行順序與 success/failure gates；明示 `mutation_executed=false`。若需外部 write，僅產 final payload summary，等待主線另行確認。

## 驗證

- installer／aggregate preflight 僅能走明確 read-only mode；若 public CLI 無法證明 zero-write，停止。
- 核對 repair matrix 與 affected suite 的既有可重現命令；本卡只重跑必要 subset，不擴掃。
- `rg '\[DBG-'`、secret/path/binary scan、`git diff --check`。
- evidence 必須列出時間、命令、exit、sanitized result、remaining risk；單一 exit 0 不算 READY。
