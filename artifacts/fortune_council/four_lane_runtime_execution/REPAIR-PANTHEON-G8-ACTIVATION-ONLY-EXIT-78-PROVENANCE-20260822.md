---
id: REPAIR-PANTHEON-G8-ACTIVATION-ONLY-EXIT-78-PROVENANCE-20260822
chain_id: PANTHEON-G8-ACTIVATION-ONLY-EXIT-78-CONTRACT-CLARIFICATION-20260822
role: repair
cycle: 1
priority: P1
status: ready
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定 P1 finding 的 transition authority／validator bounded Repair。
base_sha: a8878602c0fcf658622e6ec365821f00a73c06c9
candidate_sha: 39f2b29cfa4e71ea9133e42754b9b59de09ca074
review_sha: 79dc06a94311e61697a6b86c175ac6344a625b42
finding_id: G8-EXIT78-P1-001
---

# G8 Exit 78 Provenance Repair

## 工作名稱 → 正在做什麼 → 現在狀態

G8 exit 78 provenance Repair → 讓 Capacity executable contract真正證明 target-newer＋current reset provenance → `RCA_ONLY / AWAITING IMPLEMENT`

## Root question

如何在同一 `TARGET_STAGED → QUIESCED_TARGET_STAGED` repair unit內，使 `exit 78` 只有在 old-live activation-only、target generation newer、current Publisher reset receipt與 unchanged-service proof成立時才被 Capacity transition接受？

## Finding authority

- `G8-EXIT78-P1-001`：normative contract要求 generation／receipt provenance；production validator目前只驗 live aggregate、path、state、PID與 exit set。
- same-generation、缺 formal reset receipt的 fixture仍能接受 `78`並 stage Capacity，構成 fail-open。

## 第一拍：RCA_ONLY

1. 固定閱讀 candidate與Review RESULT；先 CodeGraph，失敗才限域 source。
2. 追出 production call chain、reset receipt schema/path、generation relation authority、unchanged-service proof。
3. 建立會命中 production validator的 RED：same-generation或缺 current reset receipt時 `78` 必須拒絕；不得用 mock-only旁路。
4. 回 `RCA_READY`：列 root cause、minimal seam、精確 allowlist、RED command與 regression matrix；未收到 `IMPLEMENT` 不得修改 tracked檔。

## IMPLEMENT 預授權 allowlist

- `scripts/pantheon_content_capacity_guard.py`
- `scripts/install_pantheon_content_capacity_guard_launchd.sh`
- `tests/test_pantheon_content_capacity_guard.py`
- `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821.md`
- `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821.md`
- 唯一 RESULT：`artifacts/fortune_council/four_lane_runtime_execution/REPAIR-PANTHEON-G8-ACTIVATION-ONLY-EXIT-78-PROVENANCE-20260822-RESULT.md`

若 reset receipt producer必須增加一個直接相關檔，RCA先回主線申請；未允許不得擴張。

## 必守 invariant

- `78` 只適用 old-live activation-only wrapper／barrier validation。
- target generation必須明確 newer than live；same-generation拒絕。
- current Publisher reset receipt、post-reset live receipt、other-six unchanged proof必須可驗證且綁 current identity／correlation。
- absent／`0` 的既有合法 inert semantics不得被無意收窄。
- 其他 nonzero、PID、path／identity drift、stale／missing receipt仍 fail closed。
- bootstrap／reset mutation不增加；不得建立第二套 transition engine。

## 禁止

- 不開 Cycle 35／36；不按 error string拆卡。
- 不做 production reset、Capacity、activation、canary、deploy、tag或push。
- 不修改 Publisher workload child、不放寬 ordering／selector／rollback。
- Repair完成只交 candidate；不得 merge。

## 驗收

- RED→GREEN：same-generation、missing／stale reset receipt拒絕；valid target-newer＋current provenance接受 `78`。
- absent／0／78正向邊界與 other nonzero／PID／path drift負向矩陣。
- focused Capacity與G8 preactivation suites PASS；shell syntax（若改 installer）、`git diff --check` PASS。
- tracked diff僅獲准 allowlist；candidate commit後回 `REPAIR_READY <full-sha>`。

## Stop-loss

- provenance authority無法由既有 receipt chain唯一證明：`BLOCKED / AUTHORITY_FORK`。
- 同一 blocker三次停止。
