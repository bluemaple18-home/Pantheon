---
id: CARD-PANTHEON-G8-PUBLISHER-TERMINAL-RESET-REPAIR-20260821
chain_id: PANTHEON-G8-PUBLISHER-CANARY
parent_card_id: CARD-PANTHEON-G8-HOST-CAPACITY-FINAL-CONTINUATION-20260821
role: repair
cycle: 32
status: ready
type: bounded_repair
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 根因已鎖定為 Publisher-only terminal 後缺少 activation-only 復位 seam；涉及 launchd 安全狀態機但規格固定。
ownership:
  - scripts/install_agy_gemini_coordinator_launchd.sh
  - tests/test_agy_gemini_coordinator.py
  - tests/test_pantheon_content_capacity_guard.py
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-PUBLISHER-TERMINAL-RESET-REPAIR-20260821-RESULT.md
  - .work/CARD-PANTHEON-G8-PUBLISHER-TERMINAL-RESET-REPAIR-20260821/**
forbidden_scope:
  - 修改 Capacity/readiness 門檻、production manifest schema、Publisher business logic
  - 手改 live plist、queue、state、transaction、tag 或 remote
  - production promotion、activation、canary、push
  - 全 repo 掃描、release suite、無關重構
  - 新建 replacement、Cycle、Reviewer 或下一張 Repair
evidence_path: .work/CARD-PANTHEON-G8-PUBLISHER-TERMINAL-RESET-REPAIR-20260821/
---

# 修復 Publisher terminal 後 activation-only 復位入口

## 工作名稱 → 正在做什麼 → 現在狀態

Publisher terminal reset repair → 補上單一正式復位 seam，消除 live Publisher normal／其他六服務 activation-only 的混合狀態 → READY

## Root Question

能否透過 repo-owned、fail-closed、Publisher-only 的正式入口，把已 terminal 且無 PID 的 live Publisher 從 normal one-shot plist 復位成 activation-only loaded/no-PID，同時保證其他六服務 plist、PID、I/O 與狀態完全不變，讓既有 Capacity preactivation 可再次通過？

## 已證實根因

- current runtime actor／origin main：`4c16a2f4ab81865ba854cff6cf79a82dfe700c71`。
- host capacity exercise 已 PASS；不是容量或 swap 問題。
- live coordinator＋四 lane＋Capacity plist 均含 `--activation-only`；live Publisher plist 不含，且 Publisher service absent。
- private stage 的 Publisher plist 是合法 normal exact-run，`max-runs=1`；Capacity staged plist 尚未建立。
- `validate_preactivation_transition()` 明確要求七個 live plist 全部 activation-only loaded/no-PID；因此現況必然回 `plist activation mode mismatch`。
- 現有 aggregate `--activate-only` 需要完整七 plist stage；目前缺 Capacity staged plist，而 Capacity installer 又先要求 live 七服務 activation-only，形成 recovery seam 缺口。

## 修復契約

1. 在既有 coordinator installer 增加一個明確、單次、Publisher-only terminal reset action；名稱由實作者選擇但必須人類可讀且進 usage。
2. action 只接受以下前置狀態：matching manifest/generation/barrier、private stage 有合法 Publisher exact-run plist、其他六個 live plist 全為 matching activation-only、其他六服務 loaded/no-PID、Publisher 無 PID且為 absent 或 terminal idle。
3. action 只可替換／bootstrap Publisher live plist：由 matching staged Publisher plist產生 activation-only 版本；禁止啟動 child、禁止碰其他六個 plist或 launchctl target。
4. postcheck 必須證明七個 live plist aggregate 全為 activation-only、Publisher loaded/no-PID、其他六服務 identity/PID/I/O 前後完全一致。
5. 任一前置或 postcheck 失敗須 rollback Publisher plist／loaded state，輸出結構化 failure receipt，禁止留下混合狀態。
6. 此 action 同時作為未來 Publisher-only child terminal 後的正式復位 seam；不可只針對本機檔案硬編碼。

## 驗證

- 先新增一個 red-capable test，重現「live Publisher normal/absent＋其餘六服務 activation-only」目前無法安全復位。
- 補正向：只變 Publisher、復位後 aggregate activation-only、無 child。
- 補負向：其他服務有 PID、identity drift、stage digest/exact-run drift、Publisher 有 PID、bootstrap/postcheck failure 均 fail-closed 並 rollback。
- 只跑受影響 test 檔與 shell syntax；`git diff --check`。
- 禁止跑 production 或全 release suite。

## 交付

- candidate commit＋RESULT，列 public action、RED/GREEN、變更檔、測試數、未驗與殘餘風險。
- 本卡只交付 repair candidate；主線驗收後才可 promotion 與 final ship。
