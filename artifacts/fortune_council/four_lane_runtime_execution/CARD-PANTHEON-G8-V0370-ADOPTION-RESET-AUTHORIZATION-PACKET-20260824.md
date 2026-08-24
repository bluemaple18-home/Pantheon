---
id: CARD-PANTHEON-G8-V0370-ADOPTION-RESET-AUTHORIZATION-PACKET-20260824
chain_id: PANTHEON-G8-V0370-PRODUCTION-ADOPTION-RESET-READINESS-20260822
role: production-authorization-packet-preparer
cycle: 3
status: ready
type: read_only_authorization_packet
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
parent_integrated_sha: 0bca7d03ca67e89dd6f39578d6e33e5199d78a9a
accepted_exception: bounded_remote_query_invocation_2_after_dns_failure
exception_scope: evidence_acceptance_only
production_read_authorized: true
production_mutation_authorized: false
remote_git_read_authorized: false
remote_git_write_authorized: false
canary_authorized: false
ownership:
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0370-ADOPTION-RESET-AUTHORIZATION-PACKET-20260824-RESULT.md
  - artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_adoption_reset_authorization_packet_20260824/**
forbidden_scope:
  - 任何 remote Git query、fetch、pull、push、tag、branch/ref mutation 或 origin 變更
  - production actor、manifest、queue、state、transaction、stage、barrier、plist、launchctl mutation
  - promotion apply、finalize、rollback、Publisher reset receipt write、activation、canary、deploy、schedule
  - 修改 source、tests、config、registry、metadata、既有 evidence、handoff 或 Content Expansion backlog
  - 新造 promotion、reset、reconciler、Publisher、authority store 或第二套 truth
result_path: artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0370-ADOPTION-RESET-AUTHORIZATION-PACKET-20260824-RESULT.md
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_adoption_reset_authorization_packet_20260824/
---

# G8 v0.3.370 adoption/reset production authorization packet

## 工作名稱 → 正在做什麼 → 現在狀態

G8 adoption/reset authorization packet → 以既有正式入口鎖定 exact mutation、rollback、reset 與 post-gate 契約 → `READY / STRICT READ-ONLY`

## Root Question

不執行任何 production 或 Git mutation，能否把已整合的 source authority 與 promotion plan 收斂成單一、可人工授權、可 fail-closed、可回退的 adoption/reset 執行封包？

## Authority Boundary

- 使用者已接受本 chain 先前「第一次 DNS 失敗、第二次成功」的 bounded remote query 例外。
- 此例外只允許整合與沿用 SHA `5a9103785ebfc8d5a28fa8188def6069beb12d88` 的既有 evidence。
- 例外不授權 production、reset、canary、push、tag 或任何新 remote query。
- 既有 integrated receipts 是 baseline；current production read-only drift check 決定封包是否仍可授權。

## Requirements Trace

| ID | requirement | traces_to |
| --- | --- | --- |
| `FR-006` | 鎖定例外範圍與唯一 source SHA，不重查 remote。 | `SC-005` |
| `FR-007` | 以 current production inputs 唯讀重算既有 promotion `plan`，不得呼叫 mutation API。 | `SC-006` |
| `FR-008` | 產出 exact authorization envelope：before identity、plan/authorization digest、write/backup set、rollback order、停損與 command boundary。 | `SC-006`, `SC-007` |
| `FR-009` | 鎖定既有 Publisher reset receipt 正向契約、fresh reconciliation 與 canary 前置 gate；不得執行。 | `SC-007` |
| `FR-010` | before/after tripwire 證明 production、Git refs 與 external state 零 mutation。 | `SC-008` |

| ID | success criterion |
| --- | --- |
| `SC-005` | source SHA 唯一為 `5a910...`；remote query count 本卡為 0；例外未擴張。 |
| `SC-006` | current plan 回 `READY_TO_APPLY` 且 deterministic；所有 digest、locator、write/backup set 與 rollback order 可重現，或單一明確 blocker。 |
| `SC-007` | 封包逐項列出仍需使用者另行授權的 production mutations；Publisher reset、fresh reconciliation、Rule 24/25、單次 canary 均有既有正式入口與 fail-closed success contract。 |
| `SC-008` | protected before/after changes `[]`；無 production、Git ref、remote 或外部狀態 mutation。 |

Frontier：`FR-006 → FR-007 → FR-008 → FR-009 → FR-010`。任何 blocker 出現即保留 `BLOCKED/UNKNOWN`，禁止猜值或擴權。

Trace preflight：`acceptance_scenarios: not-applicable`；原因：本卡是 deterministic production-authorization gate，`SC-005..008` 已直接定義 machine-verifiable acceptance，不建立 Jira 或產品 User Story。

## 必讀 Authority

1. `AGENTS.md`
2. 本 chain PREAUTH RESULT 與 `g8_v0370_preauth_blocker_resolution_20260824/**`
3. `scripts/pantheon_content_runtime_promotion.py`
4. `scripts/pantheon_g8_production_preactivation.py`
5. `scripts/pantheon_content_capacity_guard.py`
6. `scripts/agy_content_publisher.py`
7. 對應四個 test files
8. `<ai-core-root>/rules/24-storage-capacity-safety.md`
9. `<ai-core-root>/rules/25-production-canary-readiness.md`

## Existing Capability First

1. source decision 前先查主工作區 CodeGraph；worktree 無 index 時用主工作區索引。
2. promotion 只沿用 `plan_promotion`；不得包裝成另一套 workflow。
3. reset 契約只沿用 `write_publisher_reset_receipt`、`_validate_publisher_reset_provenance` 與 `validate_preactivation_transition`。
4. fresh reconciliation 只沿用 `pantheon_g8_production_preactivation`。
5. 不得因 locator 或測試工具失敗下載依賴、重建環境或盲測；同 blocker 第三次即停。

## Slices

### `G8-ARP-001` — Exception/source lock

- `traces_to`: `FR-006`, `SC-005`
- 驗證 integrated receipts、commit lineage、例外邊界；remote query 必須為 0。

### `G8-ARP-002` — Current plan-only rehearsal

- `blocked_by`: `G8-ARP-001`
- `traces_to`: `FR-007`, `SC-006`, `SC-008`
- before snapshot → existing public plan → after snapshot；禁止 apply/finalize/rollback。

### `G8-ARP-003` — Exact authorization envelope

- `blocked_by`: `G8-ARP-002`
- `traces_to`: `FR-008`, `SC-006`, `SC-007`
- 將 current plan、authorization digest、writes、backups、rollback、postchecks、stop-loss 與 exact command boundary 固定成 machine-readable JSON。

### `G8-ARP-004` — Reset/post-gate contract

- `blocked_by`: `G8-ARP-003`
- `traces_to`: `FR-009`, `SC-007`
- 只讀證明 reset success receipt、fresh reconciliation、Rule 24/25 與 canary 的既有入口、輸入、輸出、correlation identity 與 fail-closed negative path。

### `G8-ARP-005` — Verdict and tripwire

- `blocked_by`: `G8-ARP-004`
- `traces_to`: `FR-010`, `SC-008`
- JSON/AST parse、evidence-relative digest、受影響 tests、`git diff --check`、單一 candidate commit；禁止 push/tag。

## Verdict

只允許：`READY-FOR-PRODUCTION-AUTHORIZATION`、`BLOCKED`、`UNKNOWN`。

`READY-FOR-PRODUCTION-AUTHORIZATION` 不是 production 授權。下一步仍須主線 review、使用者明確授權 exact mutation envelope，才可另開 execution 卡。

## Delivery

- 單一 candidate commit，parent 必須是任務卡 commit `3e7d0e66d56d4e5efb24b169beb6618836b31412`；`parent_integrated_sha` 仍是整合 baseline `0bca7d03ca67e89dd6f39578d6e33e5199d78a9a`。
- 只新增 ownership 內 RESULT/evidence。
- 回報 verdict、candidate SHA、changed files、tests、tripwire、remaining risks；不整合、不 push、不 tag、不執行 production。
