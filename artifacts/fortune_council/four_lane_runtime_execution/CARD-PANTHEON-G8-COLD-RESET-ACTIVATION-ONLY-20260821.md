---
id: CARD-PANTHEON-G8-COLD-RESET-ACTIVATION-ONLY-20260821
chain_id: PANTHEON-G8-PRODUCTION-PREACTIVATION-RECONCILIATION-20260820
parent_card_id: CARD-PANTHEON-G8-LIVE-PUBLISHER-IDENTITY-RECONCILIATION-20260821
role: repair
cycle: 4
status: ready
type: production_cold_reset
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
ownership:
  - exact seven live LaunchAgent services and plist files
  - .work/CARD-PANTHEON-G8-COLD-RESET-ACTIVATION-ONLY-20260821/**
forbidden_scope:
  - source、tests、current stage、manifest、queue、state、transaction、content、registry、tag、push mutation
  - normal activation、Publisher child execution、canary、retry、RCA、Reviewer、replacement thread
evidence_path: .work/CARD-PANTHEON-G8-COLD-RESET-ACTIVATION-ONLY-20260821/
---

# G8 cold reset activation-only

## 工作名稱 → 正在做什麼 → 現在狀態

打掉舊 live LaunchAgent → 用 current staged payload 原地重建七個 activation-only service → `USER AUTHORIZED / READY`

## 鎖定 authority

- actor/source/origin：`c05929f2a7dac86e94aaeaa5ab6c5455892f5f77`
- manifest：`e3c393bb18a55eba1c8c6cb9e92abfb63b4241936dc78772bfaa5ec952177d32`
- runtime identity：`db8c1691bb5433b23a4803743782d686d8779ef4fec5d5b7d1cb9e038092999e`
- generation：`g17-c05929f2a7-20260821T827804Z`
- exact run：`auto-i18n-en-614aa4dc3542ab2c5637`

## 唯一執行序列

1. 僅核對 actor clean、current manifest/stage七 plist、exact run、七服務 loaded/no-PID；不得擴大診斷。
2. 將舊 live 七 plist 與 launchctl 狀態備份到本卡 evidence；備份必須可回復。
3. 對精確七個 label各執行一次 `launchctl bootout`；服務不存在視為已卸載，不 retry。
4. 移走精確七個舊 live plist到 timestamped backup；禁止刪除 stage、manifest、barrier或其他 LaunchAgent。
5. 從正式 runtime actor執行一次既有 `scripts/install_agy_gemini_coordinator_launchd.sh --activate-only`。不得手動組 normal plist、不得執行 Publisher child。
6. 成功後驗七服務 current activation-only identity、aggregate/barrier PASS、loaded/no-PID；queue仍140、exact run未消耗，所有受保護 delta為0。
7. 失敗時只允許一次 rollback：卸載本次新載入服務並把備份七 plist移回；不得第二次 activation。

## 停損

- 任何前置 authority/stage不符：`BLOCKED / NO RESET`。
- cold reset或activation-only失敗：完成一次rollback後 `BLOCKED / ROLLED BACK`。
- 禁止另開診斷、修 code或重試卡。

## 完成定義

- `REBUILT / NO CANARY`：七服務 current identity、loaded/no-PID，production child invocation=0。
- `BLOCKED / ROLLED BACK`：舊七 plist與原loaded/no-PID狀態恢復，其他production delta=0。

