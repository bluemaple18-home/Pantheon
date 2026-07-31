---
card_id: CARD-PANTHEON-FOUR-LANE-A2-NEW-CONTRACT-REPAIR-20260731
chain_id: PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731
parent_card_id: CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731
role: implementation
cycle: 0
status: INTEGRATED_OFFLINE
user_hold: false
type: lane-repair
lane: new
ownership: new output schema contract, deterministic normalization, and closed retry classification
thickness: standard
risk: medium
model: gpt-5.5
reasoning: high
model_reason: 根因與 public seams 已由 Checkpoint A 封閉；改動跨 SEO pipeline、runner／broker 與測試，但不含架構、production mutation 或共享 Publisher。
project_id: c2xpbmdzaG90OmVudl9lXzZhMTdiMzc4MTg1ODgzMmRhZWU4Njk3YzMwZmM3ZTdjCi9Vc2Vycy9tYXR0a3VvL0RvY3VtZW50cy9QYW50aGVvbg==
repo_identity: github.com/bluemaple18-home/Pantheon
required_base_ref: v0.3.183
required_base_sha: de68b6b283493a3e9ca5f80286c682cb7846735e
required_context_commit: 63979fa6e7b2ea88011011f1655e269013e65662
proposed_branch: codex/four-lane-a2-new-contract-repair-20260731
thread_status: DELIVERED
dispatch_key: v1:19562d5bd63056069b72789e78a14a4e6d76291cbff0f28c083efdc2def01abb
formal_thread_id: 019fb5d7-d3e0-72e1-92fe-ae1c0868bc61
activation_state: BOUND
worktree: <codex-home>/worktrees/71879694-dd29-4a4d-b6d6-f8caf49d411a/Pantheon
candidate_commit: aac2d3bd180bb5b82dd41f98596a0cdc62d2866f
integration_commit: 46322d1e4
review_status: GO
offline_acceptance: GO
external_provider_calls_authorized: false
production_mutation_authorized: false
traces_to:
  - FR-4LANE-003
  - FR-4LANE-007
  - SC-4LANE-001
  - SC-4LANE-003
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731/new-red-green.md
---

# A2 — New output contract fail-closed repair

## 目標

用可重現 RED 修復 `new` lane 的 `description minLength` 與 paragraph
`maxLength` schema mismatch，使 schema-invalid／deterministic failure：

1. 不被誤分類為 credential／auth outage；
2. 不無意義輪替帳號或擴散到無界新 run；
3. 經 bounded repair、deterministic normalization 或 prompt contract 後能產生
   schema-valid candidate；
4. 不放寬既有 min／max 或品質 gate。

## 已驗證前提

- Observation candidate：`63979fa6e7b2ea88011011f1655e269013e65662`。
- v0.3.183 後 52 筆 new failure 的 provider outcome 全為 `SUCCESS`。
- 52／52 為 `SCHEMA_MISMATCH`／`SCHEMA_INVALID_PAYLOAD`。
- closed diagnostics 累積 `maxLength` 94 次、`minLength` 23 次。
- 這是 provider output／schema contract failure，不是 credential outage。

## Blocking edges

- `CHECKPOINT-A = GO`：已滿足。
- 不依賴 runtime actor alignment；但未對齊 actor SHA 前不得做 production canary。
- 不依賴 A3／A4；三張卡 code allowlist 互斥。

## Allowlist

只允許在證據指向時修改：

- `scripts/agy_seo_copy_pipeline.py`
- `scripts/agy_gemini_runner.py`
- `scripts/agy_gemini_v4_broker.py`
- `tests/test_agy_seo_copy_pipeline.py`
- `tests/test_agy_gemini_outbox.py`
- `tests/test_agy_gemini_v4_broker.py`
- 必要且本卡專屬的 deterministic fixture
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731/new-red-green.md`

## Forbidden scope

- 不得修改 coordinator、Publisher、multilingual pipeline、LaunchAgent 或其他
  lane。
- 不得放寬 schema min／max、reviewer contract、禁詞或品質門檻。
- 不得加入無上限 retry／repair loop或無條件跨帳號輪替。
- 不得呼叫真實 Gemini/provider。
- 不得讀取 credential、secret、cookie、token 或 raw production output。
- 不得 push、deploy、reload、publish、修改 queue／ledger／candidate 或 production
  artifact。
- 不得自行建立 Review、Repair、replacement 或其他 thread。

## TDD contract

### RED

至少重現：

1. `description` 短於既有 `minLength`；
2. 一個或多個 paragraph 超過既有 `maxLength`；
3. provider transport 成功但 payload schema-invalid；
4. 相同 deterministic class 不得被當成 auth／credential failure。

RED 必須驗 public behavior，不綁內部 helper 名稱。

### GREEN

最小修復可以使用：

- prompt contract；
- deterministic normalization；
- bounded schema repair feedback；
- 以上組合。

但必須保留原 schema 與品質門檻，並證明修復上限與終態分類。

## Acceptance

1. RED 在修改前失敗，GREEN 在修改後通過。
2. schema-valid candidate 可由 deterministic fixture 端到端產生。
3. schema-invalid deterministic failure：
   - 不標成 credential／auth outage；
   - 不消耗無關 credential slot；
   - 不進入無上限 retry；
   - 保存 closed diagnostics，不保存 raw provider output。
4. min／max 與品質 gate 未放寬。
5. candidate persistence／idempotency／replay 受影響測試通過。
6. 受影響 SEO、outbox、broker tests 與 `git diff --check` 通過。
7. changed files 僅限 allowlist。
8. 交付單一 candidate commit與 `new-red-green.md`；不得宣稱 production
   canary 或根卡完成。

## Stop conditions

- 無法建立 red-capable reproduction 時停止，不憑猜測改 code。
- 修復需要共享 coordinator／Publisher ownership 時停止，交回主線。
- 需要真實 provider 或 production mutation時停止，等待另行授權。
- 同一 blocker 三次後停止，不做第四次。
