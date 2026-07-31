---
card_id: CARD-PANTHEON-FOUR-LANE-A3-REWRITE-ELIGIBILITY-DEADLOCK-REPAIR-20260731
chain_id: PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731
parent_card_id: CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731
role: implementation
cycle: 0
status: INTEGRATED_OFFLINE
user_hold: false
type: shared-scheduler-repair
lane: rewrite
ownership: coordinator and Publisher rewrite eligibility/retry terminal-state contract
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 修復會改動共享 coordinator 與 Publisher retry／release selection invariant；錯誤可能重播 exhausted candidate、阻塞 backlog或造成重複發布。
project_id: c2xpbmdzaG90OmVudl9lXzZhMTdiMzc4MTg1ODgzMmRhZWU4Njk3YzMwZmM3ZTdjCi9Vc2Vycy9tYXR0a3VvL0RvY3VtZW50cy9QYW50aGVvbg==
repo_identity: github.com/bluemaple18-home/Pantheon
required_base_ref: v0.3.183
required_base_sha: de68b6b283493a3e9ca5f80286c682cb7846735e
required_context_commit: 63979fa6e7b2ea88011011f1655e269013e65662
proposed_branch: codex/four-lane-a3-rewrite-deadlock-repair-20260731
thread_status: DELIVERED
dispatch_key: v1:46cac7ec0baf6e3e2a11e7f800595d3764532633a05e549d13bdfa94420cd8bf
formal_thread_id: 019fb5d8-0aa3-7921-8da9-464fdd0115a6
activation_state: BOUND
worktree: <codex-home>/worktrees/26797248-6cf6-4a52-84aa-078a7a57fc37/Pantheon
superseded_candidate_commit: 1a4e3c8e0349d18baff1a8bc783141e29b364a1b
candidate_commit: d0fdb136d3142eb5d3687b2fa4ca8e2eea8a229c
integration_commit: 921353cb6
review_status: GO
offline_acceptance: GO
resolved_finding: A3-R1-MALFORMED-RETRY-SHAPE
external_provider_calls_authorized: false
production_mutation_authorized: false
traces_to:
  - FR-4LANE-005
  - FR-4LANE-007
  - FR-4LANE-008
  - SC-4LANE-001
  - SC-4LANE-003
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731/rewrite-red-green.md
---

# A3 — Rewrite eligibility deadlock repair

## 目標

讓 coordinator 與 Publisher 對 `clean-approved + retry exhausted` rewrite
candidate 使用一致、封閉且可觀測的終態，解除：

`clean_approve > 0 → publish_ready_first`

與：

`_retry_eligible() = false → candidate 永久不被選取`

之間的 head-of-line deadlock，同時不重設 production retry、不新增無限重播、
不製造重複發布。

## 已驗證前提

- Observation candidate：`63979fa6e7b2ea88011011f1655e269013e65662`。
- rewrite inventory：353；released 1；clean approve 5；unattempted 179。
- 五筆 clean-approved candidate 均保存，retry 為 `attempts=3/max=3`、
  `eligibility=exhausted`。
- coordinator 回 `publish_ready_first`，Publisher selection 跳過 exhausted
  candidate，因此 backlog 不前進。

## Blocking edges

- `CHECKPOINT-A = GO`：已滿足。
- 不依賴 A2／A4；code allowlist 互斥。
- production canary 前仍依賴 runtime actor alignment、strict review GO 與使用者
  明確授權。

## Allowlist

- `scripts/agy_gemini_coordinator.py`
- `scripts/agy_content_publisher.py`
- `tests/test_agy_gemini_coordinator.py`
- `tests/test_agy_content_publisher.py`
- 必要且本卡專屬的 deterministic fixture
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731/rewrite-red-green.md`

## Forbidden scope

- 不得修改 SEO pipeline、runner、broker、multilingual pipeline、文章 registry、
  生成頁或 LaunchAgent。
- 不得清除、重設、刪除或手改 production retry、queue、ledger、candidate、
  `.work` 或 archive。
- 不得把 exhausted retry 靜默重設為 fresh。
- 不得加入無上限 retry／repair loop。
- 不得執行真實 provider、Publisher transaction、push、deploy、reload、publish
  或 canary。
- 不得自行建立 Review、Repair、replacement 或其他 thread。

## TDD contract

### RED

建立 deterministic fixture，至少同時包含：

1. 五筆 clean-approved candidate；
2. 每筆 retry exhausted；
3. 尚有未嘗試 rewrite inventory；
4. coordinator 目前回 `publish_ready_first`；
5. Publisher 目前沒有 ready candidate；
6. 重跑不應重置 retry或重複發布。

### GREEN

最小修復必須建立單一語意：

- exhausted candidate 進明確 terminal／blocked state；或
- coordinator 可安全繼續選擇 fresh backlog；或
- 其他以測試證明不互鎖、不可重播的 bounded 設計。

不得靠刪除 retry artifact、增加上限或無條件 retry 取得綠燈。

## Acceptance

1. RED 可穩定重現 head-of-line deadlock。
2. GREEN 後 coordinator／Publisher 對 exhausted clean-approve 使用一致終態。
3. fresh eligible backlog 能前進，或被明確、可觀測且非 `idle` 的 blocker
   阻擋。
4. exhausted candidate 不會無意義重播、重設 retry或重複發布。
5. candidate persistence／idempotency／replay測試通過。
6. rejected、ineligible、fresh、exhausted、published fixture 均有 regression
   coverage。
7. coordinator、Publisher 受影響 tests 與 `git diff --check` 通過。
8. changed files 僅限 allowlist；交付單一 candidate commit與
   `rewrite-red-green.md`。
9. 不宣稱 production release、canary或根卡完成。

## Stop conditions

- 無法重現 coordinator／Publisher互鎖時停止，不憑猜測改 code。
- 必須重設 production retry才可前進時停止並回主線。
- 發現修復需要 A2／A4 owner檔案時停止，重新切 ownership。
- 同一 blocker 三次後停止，不做第四次。
