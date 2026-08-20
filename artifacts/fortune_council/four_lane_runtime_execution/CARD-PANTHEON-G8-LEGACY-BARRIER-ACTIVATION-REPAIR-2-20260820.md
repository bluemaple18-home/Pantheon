---
id: CARD-PANTHEON-G8-LEGACY-BARRIER-ACTIVATION-REPAIR-2-20260820
chain_id: PANTHEON-FOUR-LANE-PRODUCTION-RECOVERY-20260818
parent_card_id: CARD-PANTHEON-G8-LEGACY-BARRIER-ACTIVATION-RCA-20260820
role: repair
cycle: 2
status: ready
type: source_repair
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
ownership:
  - scripts/install_agy_gemini_coordinator_launchd.sh
  - tests/test_agy_gemini_coordinator.py
  - .work/CARD-PANTHEON-G8-LEGACY-BARRIER-ACTIVATION-REPAIR-2-20260820/**
forbidden_scope:
  - production/runtime/LaunchAgent/queue/transaction/tag/push mutation
  - pantheon_content_runtime_manifest.py除非RED證明installer seam無法安全修復
  - 放寬mixed identity、PID/running、stale barrier、stage drift或一般barrier驗證
verification:
  - RED test先失敗且精確重現promoted shared manifest path
  - GREEN只接受coherent old-live→new-stage activation-only transition
  - 所有負例在replace_live_plists前fail-closed且launchctl/child I/O=0
  - targeted/full affected tests、git diff --check、candidate commit、clean worktree
evidence_path: .work/CARD-PANTHEON-G8-LEGACY-BARRIER-ACTIVATION-REPAIR-2-20260820/
---

# G8 legacy barrier activation Repair 2

## 工作名稱 → 正在做什麼 → 現在狀態

修復legacy barrier activation → 避免用promoted current manifest內容驗old-live barrier，同時保留全部fail-closed負例 → `READY / USER AUTHORIZED`

## Root Question

如何讓capacity gate已接受的coherent old-live→new-stage transition通過aggregate activation-only previous barrier phase，而不接受任意legacy barrier或跳過identity驗證？

## RCA鎖定

- old live plist保存old digest `f78faa...`，但manifest path指向已被promotion覆寫的共用檔；current檔為g14 digest `db6cc697...`。
- installer在`previous_barrier_validation`以old expected digest載入current manifest，必然`runtime manifest expected digest mismatch`。
- failure在`replace_live_plists`前；production mutation=0。
- 沒有既有正式參數可解。

## 實作契約

1. 先新增`test_activate_only_accepts_coherent_old_live_with_promoted_manifest_path`，fixture精確建立old live tuple＋old barrier＋已覆寫為new generation的shared manifest＋coherent new stage；證明現況RED。
2. 以最小installer seam修復`previous_barrier_validation`：old live/barrier authority必須來自完整coherent live tuple與已保存barrier payload，不得把可變current manifest內容當old authority。
3. 只有capacity preactivation transition已accepted、old live七服務同identity/generation/digest/config/runtime/actor/barrier path、loaded/no-PID、new staged seven coherent時可採用legacy transition。
4. mixed old live、任一PID/running、old barrier identity/digest/generation不符、missing/malformed barrier、new stage drift、normal activation、非transition path全部仍在live replacement/launchctl/child I/O前拒絕。
5. 不操作production，不修改queue/plist/barrier/manifest實體；只用tmp fixture。

## 驗證與交付

- RED exact test；GREEN exact test。
- `tests/test_agy_gemini_coordinator.py`全檔與受影響runtime/capacity targeted tests。
- shell syntax、git diff --check。
- candidate SHA、diff allowlist、test counts、production mutation=0、唯一residual risk。
