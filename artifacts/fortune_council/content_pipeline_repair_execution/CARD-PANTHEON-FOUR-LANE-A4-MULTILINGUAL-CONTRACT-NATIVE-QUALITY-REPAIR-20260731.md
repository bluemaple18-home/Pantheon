---
card_id: CARD-PANTHEON-FOUR-LANE-A4-MULTILINGUAL-CONTRACT-NATIVE-QUALITY-REPAIR-20260731
chain_id: PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731
parent_card_id: CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731
role: implementation
cycle: 0
status: INTEGRATED_OFFLINE
user_hold: false
type: multilingual-vertical-repair
lanes:
  - i18n-new
  - i18n-rewrite
ownership: multilingual locale-plan hydration, translation candidate liveness, and native-quality fail-closed contract
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: i18n-new 與 i18n-rewrite 共用 multilingual pipeline；必須由單一 owner 同時修 coverage contract並保留母語品質 invariant，避免兩個 worktree 衝突或放寬 gate。
project_id: c2xpbmdzaG90OmVudl9lXzZhMTdiMzc4MTg1ODgzMmRhZWU4Njk3YzMwZmM3ZTdjCi9Vc2Vycy9tYXR0a3VvL0RvY3VtZW50cy9QYW50aGVvbg==
repo_identity: github.com/bluemaple18-home/Pantheon
required_base_ref: v0.3.183
required_base_sha: de68b6b283493a3e9ca5f80286c682cb7846735e
required_context_commit: 63979fa6e7b2ea88011011f1655e269013e65662
proposed_branch: codex/four-lane-a4-multilingual-repair-20260731
thread_status: DELIVERED
dispatch_key: v1:9e18aeb21336d73cf4b919d19a5ef58ad4e98b0f24082e32ce8c769f2a502c63
formal_thread_id: 019fb5d8-3c6a-7c11-b507-a2f56c97a1ea
activation_state: BOUND
worktree: <codex-home>/worktrees/4c56ceb3-0331-4a68-903f-0b6090917216/Pantheon
candidate_commit: 9704ad1f2dd98e7478888a3dc5c96aaabcff5939
integration_commit: fe0b0adb4
review_status: GO
offline_acceptance: GO
external_provider_calls_authorized: false
production_mutation_authorized: false
traces_to:
  - FR-4LANE-004
  - FR-4LANE-006
  - FR-4LANE-007
  - SC-4LANE-001
evidence_paths:
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731/i18n-new-red-green.md
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731/i18n-rewrite-red-green.md
---

# A4 — Multilingual contract and native-quality repair

## 目標

由 `agy_multilingual_pipeline.py` 的唯一 owner 完成兩條垂直路徑：

1. `i18n-new`：重現並修復 provider response 成功後的
   `locale plan coverage mapping differs for article-01`，讓合法 locale plan
   能進 candidate。
2. `i18n-rewrite`：驗證 source／locale eligibility、translation／rewrite、
   candidate persistence 與 reviewer路徑，保留
   `NON_NATIVE_SEARCH_INTENT`／`AI_TEMPLATE_STYLE` fail-closed，不以放寬品質
   gate 冒充 liveness。

## 已驗證前提

- Observation candidate：`63979fa6e7b2ea88011011f1655e269013e65662`。
- i18n-new transport／broker response成功，可用既有 closed response與 brief 在
  純記憶體 hydration 重現 coverage mapping `ValueError`。
- i18n-rewrite 已能保存 candidate，但 reviewer 因母語搜尋意圖與 AI template
  style 正確 REJECT；legacy translation published count 為 0。

## Blocking edges

- `CHECKPOINT-A = GO`：已滿足。
- A4 是 `scripts/agy_multilingual_pipeline.py` 唯一 owner；不得拆成兩張同時
  修改此檔的 worktree。
- 不依賴 A2／A3。
- production canary 前依賴 runtime actor alignment、strict review GO 與使用者
  另行授權。

## Allowlist

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- 必要且本卡專屬的 deterministic locale／source fixture
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731/i18n-new-red-green.md`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731/i18n-rewrite-red-green.md`

## Forbidden scope

- 不得修改 runner、broker、coordinator、Publisher、SEO pipeline、LaunchAgent、
  registry或其他 lane owner檔案。
- 不得放寬 locale plan coverage、source hash、target count/order、母語搜尋意圖、
  AI template style 或 reviewer contract。
- 不得執行真實 provider、production Publisher transaction、push、deploy、
  reload、publish 或 canary。
- 不得手改 production brief、response、candidate、review、queue或ledger。
- 不得保存 raw provider output或任何 secret。
- 不得自行建立 Review、Repair、replacement 或其他 thread。

## TDD contract

### RED — i18n-new

以 public behavior 重現：

1. transport／response schema成功；
2. coverage mapping缺漏、重複、slot錯置或順序錯誤；
3. `_hydrate_locale_plan`／validation 在 candidate前 fail closed；
4. error能被分類為 deterministic locale-plan failure，而非 credential／transport。

### RED — i18n-rewrite

建立 source／locale eligibility fixture，至少覆蓋：

1. eligible legacy rewrite source；
2. ineligible／already-terminal source；
3. candidate persistence；
4. clean-approved quality path；
5. `NON_NATIVE_SEARCH_INTENT`、`AI_TEMPLATE_STYLE` rejection path。

### GREEN

- 合法 coverage mapping 能穩定 hydration並產生可驗 candidate。
- 非法 mapping仍 fail closed且保留封閉診斷。
- i18n-rewrite clean fixture可到 candidate／review；已知母語品質 finding仍
  terminal reject。

## Acceptance

1. i18n-new coverage RED 在修改前失敗、修改後通過。
2. locale plan mapping、source hash、target count/order與 identity invariant未
   放寬。
3. i18n-new合法 fixture可完成 brief→plan→candidate persistence。
4. i18n-rewrite eligible／ineligible selection fixture正確。
5. i18n-rewrite clean fixture可完成 source→translation/rewrite→candidate→
   review；已知母語品質 violation仍 fail-closed。
6. deterministic failure不誤分類為 credential／transport，不進入無上限 retry。
7. multilingual受影響 tests 與 `git diff --check` 通過。
8. changed files 僅限 allowlist；交付單一 candidate commit與兩份 lane-specific
   red-green evidence。
9. 不宣稱 production locale release、canary或根卡完成。

## Stop conditions

- 無法以 deterministic fixture重現 i18n-new `ValueError` 時停止。
- 合法 i18n-rewrite fixture仍需修改 Publisher／coordinator才能驗證時停止並
  交回主線，不跨 ownership。
- 修復需要放寬母語品質 gate時停止並回報 `NO-GO`。
- 同一 blocker三次後停止，不做第四次。
