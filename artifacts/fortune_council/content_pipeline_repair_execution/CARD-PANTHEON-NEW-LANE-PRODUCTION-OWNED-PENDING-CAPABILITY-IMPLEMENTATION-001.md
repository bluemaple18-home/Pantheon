---
card_id: CARD-PANTHEON-NEW-LANE-PRODUCTION-OWNED-PENDING-CAPABILITY-IMPLEMENTATION-001
status: CARD_DRAFTED
type: bounded-implementation
project: Pantheon
chain_id: PANTHEON-NEW-LANE-PRODUCTION-OWNED-PENDING-CAPABILITY-20260728
owner: implementation
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 此切片修改 provider 前的 authority boundary、allocator durable state 與 outbox lifecycle ordering，錯誤回退成本高。
created_at: 2026-07-28 Asia/Taipei
fixed_base_sha: c44953a7c3a68008a84eb8e7fb8fc88147a18fd2
review_budget: 1
repair_budget: 1
---

# Pantheon New-Lane Production-Owned Pending Capability Implementation

## Why this is the correct continuation

- 早上持續修復的是 trusted allocator receipt／lifecycle authority 主線。
- 下午「先打通一條」建立 New lane handshake candidate：
  `cea69cc97b59b1635f0e48a444c6d222efc24670`。
- 該 candidate 已由有效唯一 Review commit
  `c44953a7c3a68008a84eb8e7fb8fc88147a18fd2` 判定
  `NO_GO / STOP_NO_REPAIR_BUDGET`。
- 使用者已明確要求另切分支繼續修下午這個未完成點。
- 本卡是新的 bounded Implementation chain，不重開舊 Review、不偽裝成舊 chain Repair。

## Root question

能否讓 `PENDING registration → outbox` 只由 production-owned、不可由 caller 偽造的 transport capability 觸發，並確保任何 injected／direct client 在 provider、allocator durable state、queue、receipt 或 run-file side effect 之前就被拒絕，同時保留一篇 New lane 的完整 production-path lifecycle？

## Authoritative finding

來源：

`artifacts/fortune_council/content_pipeline_repair_execution/evidence/pantheon_new_lane_outbox_lifecycle_handshake_review_001/review.md`

必須只關閉：

`FIND-PANTHEON-NEW-LANE-PENDING-CAPABILITY-001`

- severity：`P1`
- location at reviewed candidate：`scripts/agy_seo_copy_pipeline.py:3924`
- trigger：caller-bound injected client 持有 exact `SharedAllocator` 發出的 genuine verifier，並暴露 callable `enqueue_registered_json`；該 callable 可先執行 provider side effect，再由 pipeline post-call 檢查拒絕。
- observed：`provider_calls_before_completed_lifecycle=1`、`pending_requests=1`、`terminal_bindings=0`、operation receipt written。
- required outcome：pending transition 必須是 production-owned、不可偽造的 capability；direct／injected client 必須在所有 provider／durable／file side effect 前 fail closed。

不得重開已關閉的其他 findings，不得擴張成四 lane 重構。

## Stable requirements and traceability

### FR-001 — Production-owned pending transition

只有 production construction path 建立的 exact transport authority 可以：

1. 建立 exact allocator PENDING registration。
2. 建立唯一 sanitized outbox request。
3. 回傳 bounded pending outcome。

任意 caller-supplied method、duck-typed object、subclass、monkey-patched callable 或 copied verifier 不得成為 execution authority。

### FR-002 — Pre-side-effect rejection

所有不具 production-owned authority 的 client 必須在以下計數全部仍為零時被拒絕：

- provider calls
- allocator PENDING／terminal rows
- outbox／processing／inbox／archive／failed files
- operation receipt／candidate／review／run-state writes

### FR-003 — Positive lifecycle preservation

production New lane 仍須完成：

`first tick PENDING/outbox → writer runner TERMINAL → response acceptance → reviewer PENDING/outbox → reviewer TERMINAL → legal review outcome`

exact writer／reviewer model、trusted receipt、request identity、maker-checker exclusion 與 replay invariants不得退化。

### SC-001

以 genuine verifier 綁定 hostile injected client，讓其 `enqueue_registered_json` 內含 provider spy／durable side effect；呼叫後必須 pre-side-effect fail closed，所有計數為零。

### SC-002

production `OutboxGeminiClient` positive path 能建立一次 PENDING 與一次 outbox request，runner 後才允許 terminal acceptance。

### SC-003

同 operation replay 不新增 provider call、allocator ordinal、registration、binding、terminal 或 queue request。

### SC-004

missing authority、wrong owner、copied callable、monkey-patched method、subclass／proxy、different allocator／verifier／context 均 fail closed。

## Slice

- slice_id：`SLICE-PENDING-CAPABILITY-001`
- traces_to：`FR-001`、`FR-002`、`FR-003`、`SC-001`、`SC-002`、`SC-003`、`SC-004`
- blocking edges：
  - valid Review commit `c44953a7…` 必須存在且 direct parent 為 `cea69cc…`
  - starting worktree 必須精確位於 fixed base `c44953a7…`
  - capability preflight、clean worktree、無 index lock 必須通過
- frontier：本 slice；沒有其他可平行 production slice
- checkpoint：RED fixture 重現 authoritative P1 後才能進 GREEN；SC-001 綠燈後才能跑 positive lifecycle。

## TDD execution

### RED

先新增一個不依賴舊 Review harness 的 regression：

1. 建立 temp `SharedAllocator` 與 genuine trusted verifier。
2. 建立 hostile injected client，綁定 genuine verifier並暴露 callable pending method。
3. hostile method 若被呼叫，會增加 provider spy 並嘗試 durable／file side effect。
4. 在未修改 production 前證明至少一個 forbidden side effect 發生，與 `c44953a7…` finding 一致。

RED evidence 必須記錄實際／預期與所有 side-effect counters。

### GREEN

做最小 production fix：

- pending authority 不得由任意 `getattr(..., "enqueue_registered_json")` callable 決定。
- production-owned authority 必須與 exact transport owner、verifier、operation request/context 綁定。
- authority 驗證必須發生在 mutation `client.operation_context`、provider、allocator registration、queue 與 receipt write之前。
- 禁止用 class name、可複製 boolean、caller-controlled token 或可 monkey-patch attribute 冒充 capability。
- 不提前抽象成通用 transport framework。

### Regression

- hostile genuine-verifier client：所有 side-effect counters `0`。
- production positive New lane：完整 writer／reviewer lifecycle 通過。
- replay：無新增 allocation／request／provider／terminal。
- existing trusted allocator／outbox／SEO behavior 無回歸。

## Changed-file allowlist

Production：

- `scripts/agy_seo_copy_pipeline.py`
- `scripts/agy_gemini_outbox.py`
- `scripts/agy_gemini_allocator.py`

Tests：

- `tests/test_agy_seo_copy_pipeline.py`
- `tests/test_agy_gemini_outbox.py`
- `tests/test_agy_gemini_allocator.py`

Artifacts：

- 本卡
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/pantheon_new_lane_production_owned_pending_capability_implementation_001/**`

若必須修改 coordinator、runner、multilingual、Publisher、launchd、config 或其他檔案，回報 `BLOCKED_SCOPE`，不得擴張 allowlist。

## Forbidden scope

- 不改四條 lane scheduler、fairness、內容規則或翻譯規則。
- 不改 reviewer model cutover、launchd、key pool、credentials 或 live service。
- 不接觸 live `.work`、真實 Gemini、HTTP、provider 或 production queue。
- 不修改既有 candidate／Review evidence。
- 不 push、merge、deploy、publish 或 canary。
- 不建立第二個 Implementation、不自審、不自行開 Review／Repair thread。
- 不用 sub-agent 或平行工作單元。
- 不以新增 post-call rollback 掩蓋 pre-call authority flaw；外部 side effect 不可依賴 rollback。

## Required verification

1. 固定 lineage：
   - `HEAD` 起點精確為 `c44953a7c3a68008a84eb8e7fb8fc88147a18fd2`
   - `HEAD^` 精確為 `cea69cc97b59b1635f0e48a444c6d222efc24670`
2. RED／GREEN SC-001 regression。
3. SC-002 production-path synthetic New lane writer／reviewer lifecycle。
4. SC-003 replay 與 SC-004 adversarial matrix。
5. affected suites：
   - allocator
   - outbox
   - SEO copy pipeline
   - coordinator read-only regression
6. changed production files `py_compile`。
7. exact changed-file allowlist、JSON parse、privacy／secret／raw output／debug print／absolute path scan。
8. `git diff --check` 與 post-commit clean status。

不得以既有 Review evidence或單一 targeted test代替獨立驗證。

## Evidence and delivery

Evidence root：

`artifacts/fortune_council/content_pipeline_repair_execution/evidence/pantheon_new_lane_production_owned_pending_capability_implementation_001/`

至少交付：

- `red_green.md`
- `implementation.md`
- `results.json`
- `verification.txt`

交付一個 candidate commit：

- direct parent 精確為 `c44953a7c3a68008a84eb8e7fb8fc88147a18fd2`
- 只含 changed-file allowlist
- worktree clean
- 回報完整 40 字 candidate SHA
- 狀態只能是 `READY_FOR_REVIEW`、`BLOCKED_SCOPE` 或 `BLOCKED_ENV`

Implementation 不宣稱 ACCEPTED。主線收到 candidate 後才可建立唯一一次獨立 Review；最多一次 Repair，禁止無限迴圈。

## Dispatch receipt

- card source SHA：待提交
- implementation source ref：`codex/new-lane-production-owned-pending-capability-20260728`
- fixed base：`c44953a7c3a68008a84eb8e7fb8fc88147a18fd2`
- source clean／index lock：待驗證
- formal thread ID：PENDING
- title：`CARD-PANTHEON-NEW-LANE-PRODUCTION-OWNED-PENDING-CAPABILITY-IMPLEMENTATION-001`
- worktree exists／clean／distinct：PENDING
- model：`gpt-5.6-sol`
- reasoning：`high`
- Gate 1 card contract：PASS
- Gate 2 visible thread：PENDING
- Gate 3 candidate delivery：PENDING
- Gate 4 independent review：PENDING（Implementation 完成後由主線另開）
- Gate 5 mainline acceptance：PENDING
- workflow：`CARD_DRAFTED`
