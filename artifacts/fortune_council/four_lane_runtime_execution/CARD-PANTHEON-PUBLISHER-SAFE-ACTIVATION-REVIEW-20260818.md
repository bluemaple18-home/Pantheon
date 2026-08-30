---
id: CARD-PANTHEON-PUBLISHER-SAFE-ACTIVATION-REVIEW-20260818
chain_id: PANTHEON-PUBLISHER-SAFE-ACTIVATION-RESTORE-20260818
parent_card_id: CARD-PANTHEON-PUBLISHER-SAFE-ACTIVATION-RESTORE-20260818
role: reviewer
cycle: 1
status: ready
type: review
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定 candidate SHA 的 production activation 核心契約審查；規格已鎖定，使用 GPT-5.5 high，不需 5.6。
base_sha: 0dada575ce0684e0afbaaa1ca7cc8c3a4d97e43f
candidate_sha: f1fab53310df7f89add90097c0a182509642d38b
ownership:
  - .work/CARD-PANTHEON-PUBLISHER-SAFE-ACTIVATION-REVIEW-20260818/review/**
forbidden_scope:
  - 修改 candidate、source、tests、installer、manifest、Publisher 或任何 runtime code
  - 修改 Writer、模型路由、文章、registry、sitemap、queue、transactions 或四線 lane
  - 整合、push、tag、部署、LaunchAgent reload、production activation 或發布
  - 建立 replacement、Repair 或第二個 Reviewer thread
verification:
  - 固定 base/candidate SHA 與 changed-file boundary
  - 驗證缺 barrier 的 normal activation 在任何 launchctl mutation 前 fail closed
  - 驗證 activation-only 既有行為與 Publisher child I/O 零次契約未退化
  - 比對 base/candidate exact failing test names，隔離既有 APF backlog
  - git show --check 與 review evidence
evidence_path: .work/CARD-PANTHEON-PUBLISHER-SAFE-ACTIVATION-REVIEW-20260818/review/
---

# Publisher safe activation independent review

## 工作名稱 → 正在做什麼 → 現在狀態

Publisher 安全啟動獨立審查 → 驗證兩階段 activation candidate 與 fail-closed 邊界 → `READY / REVIEW ONLY`

## Root Question

Candidate `f1fab53310df7f89add90097c0a182509642d38b` 是否以最小變更確保 normal `--activate` 在 matching barrier 缺失或 stale 時，於任何 launchctl mutation 與 Publisher `RunAtLoad` child invocation 前 fail closed，同時不破壞 activation-only？

## Review 範圍

- Base：`0dada575ce0684e0afbaaa1ca7cc8c3a4d97e43f`
- Candidate：`f1fab53310df7f89add90097c0a182509642d38b`
- 預期 candidate changed files：
  - `scripts/install_agy_gemini_coordinator_launchd.sh`
  - `tests/test_agy_gemini_coordinator.py`
  - `.work/CARD-PANTHEON-PUBLISHER-SAFE-ACTIVATION-RESTORE-20260818/evidence.md`
- Reviewer 唯一可寫輸出：`evidence_path`。

## 需求追溯

### `SLICE-SAFE-ACT-REVIEW-CONTRACT`

- `traces_to`: `FR-001`, `FR-002`, `FR-003`, `SC-001`, `SC-002`, `SC-003`
- 檢查 gate 是否在所有 destructive launchctl mutation 前執行。
- 檢查 barrier 比對是否真正綁定本次 runtime manifest/generation，且 missing、invalid、stale 均 fail closed。
- 檢查 normal transition 是否意外刪除仍需使用的 barrier，或留下 TOCTOU 窗口。

### `SLICE-SAFE-ACT-REVIEW-REGRESSION`

- `traces_to`: `FR-002`, `SC-001`, `SC-002`
- 重跑 candidate focused RED/GREEN 與 installer affected subset。
- 重跑 manifest/publisher 測試。
- 在 base/candidate 比對完整 coordinator 測試 exact failing names；確認 candidate 沒新增 failure。

### `SLICE-SAFE-ACT-REVIEW-VERDICT`

- `traces_to`: `SC-003`
- 執行 `git show --check`。
- 只以 P0/P1 阻擋：有阻塞 finding 回 `REQUEST_CHANGES`；沒有則回 `ACCEPT_WITH_RESIDUAL_RISK`。
- P2/P3 只列 residual risk，不得移動驗收門檻。

## 必查問題

1. 缺 barrier 時是否在 `install_live_replacements`、bootout、bootstrap、kickstart 前拒絕。
2. Barrier validation 是否使用既有 authority，而非新 token framework、第二套狀態機或時序 sleep。
3. `--activate-only` 是否仍可建立/更新 barrier 並保持 child I/O 為零。
4. 正常 transition 是否只能沿 activation-only 已完成的 matching generation 前進。
5. 測試是否觀察 public launchctl/child invocation contract，而非只測私有字串。
6. Test helper 的 hardened identity 調整是否只修 fixture，未弱化 production validation。
7. Candidate 宣稱的 5 個 APF backlog failures 是否在 base 同名存在，candidate 是否沒有新增失敗。

## 停止條件

- 不得自行修 code；P0/P1 只交 findings。
- 若 candidate SHA、base SHA、card 或 changed-file boundary 不符，回 `REQUEST_CHANGES`。
- 同一驗證 blocker 三次停止並交精確證據。
- 不得碰 production、外部 runtime 或 LaunchAgent。

## 交付格式

- verdict
- findings：severity、path:line、觸發條件、證據、風險、建議修法、confidence
- base/candidate exact test comparison
- changed-file boundary
- residual risks
- review evidence path
