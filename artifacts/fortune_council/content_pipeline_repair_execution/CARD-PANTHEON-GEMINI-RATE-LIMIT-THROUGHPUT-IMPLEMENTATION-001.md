---
card_id: CARD-PANTHEON-GEMINI-RATE-LIMIT-THROUGHPUT-IMPLEMENTATION-001
chain_id: PANTHEON-GEMINI-RATE-LIMIT-THROUGHPUT-20260728
type: implementation
status: READY_TO_DISPATCH
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
source_sha: e21d9f7f11ef0fbfd78224afb5027b57c6b07f61
review_budget: 1
repair_budget: 1
---

# Gemini rate-limit throughput implementation

## Root question

在不更換三槽 credential、不繞過 strict round-robin、不重構四條 lane 的前提下，
把 429 burst amplification 改成跨 lane、跨 process、restart-safe provider admission：

1. closed `API_RATE_LIMITED` 後，對應匿名 slot 進入 bounded cooldown。
2. 所有可用 slot cooling 時，不 claim queue、不配置 ordinal、不呼叫 provider、不新增 failed artifact。
3. cooldown 到期只放行一篇 `new`，writer 已完成者的 reviewer 優先於 fresh writer。
4. strict round-robin 在 eligible slot 間 deterministic，slot 恢復後重新加入。
5. 只能減少無效呼叫與 failure churn，不得宣稱突破 RPD/TPM 硬上限。

本卡執行時以正式 thread prompt 攜帶的完整固定派工契約為優先契約。

## Stable requirements

- `FR-RATE-001`：production admission 使用共用 durable state 與跨 process lock；closed schema、atomic、restart-safe。
- `FR-RATE-002`：只有 sanitized `API_RATE_LIMITED` 能建立 cooldown；不得寫入 raw provider body、credential value/path 或 exception text。
- `FR-RATE-003`：denied admission 不得 claim/move queue、配置/消耗 ordinal、建立 response/failure artifact或呼叫 provider。
- `FR-RATE-004`：cooldown bounded、可測試、clock 可注入；process-local sleep 不可作唯一狀態。
- `FR-RATE-005`：維持三個匿名 slot；eligible allocation deterministic；cooled slot credential 不得讀，恢復後重新加入。
- `FR-RATE-006`：每個真實 provider attempt 精確一個 ordinal；denied admission 零 ordinal；429 不 retry/fallback/換 slot。
- `FR-RATE-007`：new-matrix active 低於 floor 時，每 cycle 最多 register 1 run、1 article。
- `FR-RATE-008`：同 cycle 有 writer-complete/review-pending 時，先 reviewer，再 fresh writer。
- `FR-RATE-009`：提供可回退 new-only canary seam；開啟時不 seed/consume rewrite/i18n，關閉後四 lane 相容。
- `FR-RATE-010`：cooldown/admission 輸出只含匿名 slot、時間窗與 closed reason。

## Success criteria

- `SC-RATE-001`：一次五個 prepared new runs 的 fixture 先 RED；GREEN 精確 1 run、1 article。
- `SC-RATE-002`：三槽 synthetic 429 cooling 後，兩 lane root 後續 cycle closed wait；provider、ordinal、claim、failure artifact delta 皆為 0。
- `SC-RATE-003`：clock expiry 後精確放行一篇 new，不同時放多篇或 rewrite。
- `SC-RATE-004`：review-pending 與多個 fresh writer 並存時，下一 request 是 reviewer。
- `SC-RATE-005`：一槽 cooling 時只讀 eligible selected credential；expiry 後恢復公平輪替，無 duplicate ordinal。
- `SC-RATE-006`：new-only 不 seed/consume rewrite、i18n-new、i18n-rewrite；seam off 相容。
- `SC-RATE-007`：state、receipt、log、evidence 通過 secret/local-path privacy scan。

## Scope

Production allowlist:

- `scripts/agy_gemini_allocator.py`
- `scripts/agy_gemini_runner.py`
- `scripts/agy_gemini_coordinator.py`
- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `ops/launchd/com.pantheon.agy-gemini-coordinator.plist.example`
- `ops/launchd/com.pantheon.agy-gemini-lane.plist.example`

Test allowlist:

- `tests/test_agy_gemini_allocator.py`
- `tests/test_agy_gemini_outbox.py`
- `tests/test_agy_gemini_coordinator.py`

Artifact allowlist:

- 本卡
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/pantheon_gemini_rate_limit_throughput_implementation_001/**`

## Guardrails

- 不新增 production module，不重構四條 lane，不讓 coordinator 成為第二套 workflow engine。
- 不修改 Publisher、V4 allocator lifecycle、文章內容、queue payload schema、registry、sitemap 或 feed。
- 不更換、讀取、輸出或複製 credential value/path，不改 pool identity 或三槽數量。
- 不做真實 provider/HTTP、launchctl、deploy、plist install、kickstart、canary、publish、push、PR 或 merge。
- 429 不 retry/fallback/failure-driven rotation；已發生的 attempt 仍須產生 terminal failure。
- 若 denied admission 的零 ordinal 或跨 process correctness 無法證明，狀態必須是 `BLOCKED / SCOPE_CHANGE_REQUIRED`。

## Slices and verification

1. `SLICE-RATE-001`：保存 current burst/reviewer ordering deterministic RED。
2. `SLICE-RATE-002`：durable slot cooldown 與 strict allocator admission。
3. `SLICE-RATE-003`：new-only seam、installer/plist contract 與 regressions。

必跑 focused allocator/runner/outbox/coordinator tests、60+ synthetic multiprocessing、
corrupt/truncated/symlink/wrong-mode/pool-mismatch fail-closed、429/timeout/5xx/success
ordinal matrix、publisher/multilingual/SEO targeted regressions、production Python
`py_compile`、installer `bash -n`、plist lint、`git diff --check`、changed-file allowlist
與 privacy scan。

交付只允許 `DELIVERED_CANDIDATE / READY_FOR_REVIEW` 或有證據的 `BLOCKED`。
