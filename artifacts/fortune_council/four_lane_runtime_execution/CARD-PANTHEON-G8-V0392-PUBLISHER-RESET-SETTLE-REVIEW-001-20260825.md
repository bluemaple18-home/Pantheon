---
id: CARD-PANTHEON-G8-V0392-PUBLISHER-RESET-SETTLE-REVIEW-001-20260825
status: ready
chain_id: PANTHEON-G8-PUBLISHER-RESET-SETTLE-REPAIR-20260825
role: reviewer
role_slot: reviewer
cycle: 1
type: review
thickness: strict
risk: critical
base_sha: 1a5c3d60559f26604740050de081e2d8ace027f1
candidate_sha: 8c18080be331be954224b5616d1374dbfee98b2c
model: gpt-5.5
reasoning: high
model_reason: 固定 SHA 的 production activation fail-closed 契約審查；用 strict/core-bounded reviewer，不開架構岔。
traces_to:
  - SC-001
  - SC-002
  - SC-003
---

# Publisher activation-only settle 修復獨立審查

工作名稱：審查 Publisher transient PID settle 候選

## 唯一責任

唯讀審查 candidate `8c18080be331be954224b5616d1374dbfee98b2c` 相對 base `1a5c3d60559f26604740050de081e2d8ace027f1` 的完整 diff，判定它是否安全修正 transient PID 誤判，且沒有放寬 production activation 的 fail-closed 邊界。

本卡是此候選唯一 Reviewer；不得建立第二 Reviewer、Repair、replacement 或其他任務。

## 必審風險

1. correctness：同 canonical path 的 PID 只能在既有 20 次 bounded window 內暫時容忍；no-PID 才能 settle success。
2. fail-closed：持續 PID、path 缺失／重複／漂移、settle absent、postcheck failure 仍須 rollback；不得把最後一次 PID 誤標 success。
3. test validity：新增 transient regression 必須真的驅動所聲稱的狀態。尤其 `child_log` 的不存在只有在 fake launcher 確實具備寫入該 log 的能力時才算「Publisher child 未執行」證據；若只是建立一個從未接線的 Path，視為驗證缺口。
4. side effects：other six plist byte-identical、mutation log、receipt/provenance 與 rollback phase 必須維持既有契約。
5. regression：重跑卡片的 13 項 targeted subset、`bash -n`、`git diff --check`；不得只相信候選附帶 log。
6. activation readiness：核對完整測試 `73 failed, 192 passed` 的代表性證據。若 `writer model is unavailable: gemini-3.5-flash` 代表目前正式 activation 必然被擋，必須與本候選 correctness 分軸回報，且不得宣稱可直接 activation／發文。

## 可讀範圍

- implementation card 與 candidate commit 全 diff。
- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `tests/test_agy_gemini_coordinator.py`
- V0392 RESULT 與專屬 evidence。
- 為理解既有契約所需的直接相鄰程式碼；禁止全 repo 漫遊。

## 可寫範圍

- 僅 `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0392-PUBLISHER-RESET-SETTLE-REVIEW-001-20260825-RESULT.md`
- 僅 `artifacts/fortune_council/four_lane_runtime_execution/g8_v0392_publisher_reset_settle_review_001_20260825/`

不得修改 source、tests、candidate、既有 evidence 或其他檔案。

## 禁止範圍

- 禁止真實 `launchctl`、`~/Library/LaunchAgents`、正式 runtime、activation、Writer、第二 run、publication、push、tag、merge 或整合。
- 禁止修 code、調 timeout、重產 candidate、順手處理 model route 或開任何新卡。
- 禁止安裝／下載工具、查 remote 或碰既有未追蹤檔。

## Findings 契約

- findings 依 P0→P3 排序；每項必須包含 `severity`、`category`、`path:line`、evidence、觸發條件、風險、建議修法、validation gap、confidence。
- Spec axis 與 Standards axis 分開判定，不得互相抵銷。
- 只有 P0/P1 或 production safety risk 可阻擋 candidate；P2/P3 不得冒充阻擋。

## Verdict

- `GO`：candidate 無未解 P0/P1；列出重跑證據、remaining risks，並另列 activation readiness 是否仍被 model capability 阻擋。
- `NO-GO`：列出每個阻擋 finding 與可重現證據；只交回主線，不得自行修或另開卡。
- 全程保持 worktree clean，或只新增本卡允許的 RESULT/evidence；交付一個 reviewer result commit 與完整 SHA。
