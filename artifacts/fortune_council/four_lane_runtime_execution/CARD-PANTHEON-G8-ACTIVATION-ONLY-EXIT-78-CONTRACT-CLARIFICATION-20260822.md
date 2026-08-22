---
id: CARD-PANTHEON-G8-ACTIVATION-ONLY-EXIT-78-CONTRACT-CLARIFICATION-20260822
chain_id: PANTHEON-G8-ACTIVATION-ONLY-EXIT-78-CONTRACT-CLARIFICATION-20260822
role: implementation
cycle: 1
priority: P1
status: ready
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 核心 release state contract 規格已固定；只做 bounded normative clarification 與 deterministic regression。
source_authority: 0ed5124eab31b073f74c584b39f4353c209689b3
---

# G8 Activation-Only Exit 78 Contract Clarification

## 工作名稱 → 正在做什麼 → 現在狀態

G8 activation-only inert semantics clarification → 明文化 old-live Publisher 面對 promoted shared manifest 時 `exit 78` 是否符合 `ST-QUIESCED-TARGET-STAGED` → `READY / NO PRODUCTION`

## Root question

在 `ST-TARGET-STAGED → ST-QUIESCED-TARGET-STAGED` 中，old-live Publisher activation-only wrapper 因 old expected digest 對 promoted shared manifest mismatch 而 exit `78`，之後 launchd 穩定為 loaded/no-PID、exact path，是否為 State Contract 明確允許的 inert semantics？

## 已知事實

- State Contract：Publisher live 為 `old_live + activation-only + INERT_LOADED + child_policy=forbidden`。
- Edge Map：old live 保持舊 generation、target stage 較新；postcondition 為七服務 activation-only loaded/no-PID。
- Capacity executable contract：last exit code只接受 absent、`0`、`78`。
- Cycle 34 test已把 Publisher child `78`、單次 bootstrap、settle後 loaded/no-PID視為成功。
- `0ed5124e` 已在 main；本卡不撤回、不啟動 production。

## 唯一責任

產出一個 bounded contract clarification candidate，使 normative docs與 executable contract一致：明確區分 activation wrapper／barrier validation exit 與被禁止的 production child，並鎖定 `78` 只在 old-live activation-only、target-newer transition、loaded/no-PID、exact path、current receipts成立時合法。

## Allowlist

- `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821.md`
- `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821.md`
- `tests/test_pantheon_content_capacity_guard.py`
- 唯一 RESULT：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-ACTIVATION-ONLY-EXIT-78-CONTRACT-CLARIFICATION-20260822-RESULT.md`

## 禁止

- 不改 runtime／installer／Capacity implementation／manifest promotion時機。
- 不放寬 PID、path、identity、generation、selector、ordering、receipt或rollback。
- 不把任意 nonzero exit、normal mode或 target generation mismatch合法化。
- 不開 Cycle 35、不做 reset、Capacity、activation、canary、deploy、tag或push。

## 驗收

1. State Contract明文定義允許的 inert terminal exit集合與適用條件。
2. `child_policy=forbidden` 明確指 production workload child，不與 activation wrapper validation矛盾。
3. Edge Map明列此 transition可接受 `78`，但只在 loaded/no-PID、exact path與 old-live/target-newer關係成立時。
4. deterministic test證明 `78`可接受；其他 nonzero、PID、path drift仍拒絕。
5. focused pytest、contract/reference檢查、`git diff --check` PASS。
6. tracked diff僅 allowlist；candidate commit後回 `DELIVERED_CANDIDATE`，不得自行 merge／push。

## Stop-loss

- 若現有 State Contract語義無法在不改 runtime authority下自洽，回 `BLOCKED / CONTRACT_FORK`。
- 同一 blocker三次停止。
