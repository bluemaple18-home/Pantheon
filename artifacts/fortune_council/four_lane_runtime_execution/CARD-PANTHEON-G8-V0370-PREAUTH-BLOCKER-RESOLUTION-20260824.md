---
id: CARD-PANTHEON-G8-V0370-PREAUTH-BLOCKER-RESOLUTION-20260824
chain_id: PANTHEON-G8-V0370-PRODUCTION-ADOPTION-RESET-READINESS-20260822
role: preauthorization-blocker-resolver
cycle: 2
status: ready
type: preauthorization_blocker_resolution
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
model_reason: 既有 BLOCKED evidence 已固定 root question；本卡只收斂 Git/source authority、exact allowlist 與 promotion plan readiness，不做 production mutation，使用 GPT-5.5 high 維持核心契約精度並控制成本。
parent_integrated_sha: c73e3e5a1a4e1f86356e47ded4c3a41de1bc9b92
production_read_authorized: true
production_mutation_authorized: false
remote_git_read_authorized: true
remote_git_write_authorized: false
canary_authorized: false
ownership:
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0370-PREAUTH-BLOCKER-RESOLUTION-20260824-RESULT.md
  - artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_preauth_blocker_resolution_20260824/**
forbidden_scope:
  - fetch、pull、push、tag、branch/ref mutation、remote write 或修改 origin URL
  - production actor、manifest、queue、state、transaction、private stage、live plist、barrier、launchctl mutation
  - promotion apply、rollback、finalize、reset、activation、restage、canary、Publisher child、deploy、schedule、steady autonomy
  - 修改 repo source、tests、config、registry、metadata、既有 evidence、既有 RESULT、handoff 或 Content Expansion backlog
  - 新造第二套 reconciler、promotion workflow、duplicate truth、Publisher workflow 或 authority store
verification:
  - 唯讀遠端 Git authority receipt 鎖定 remote main SHA、origin URL、查詢時間與命令結果；不得以 local tracking ref 或 patch-id 單獨自證
  - release tag、remote main、local main、runtime actor 與 candidate lineage 的 ancestry、tree、patch-id、changed-path 集合可重現
  - exact source authority 與最小 allowlist 已由既有 formal reconciler 的 phase-specific probe 驗證；pre-adoption 允許停在 ACTOR_MANIFEST_AUTHORITY_MISMATCH，不要求 GO
  - 既有 pantheon_content_runtime_promotion plan 以 current production inputs 唯讀回傳 READY_TO_APPLY，或留下具體 BLOCKED/UNKNOWN code；不得呼叫 apply/rollback/finalize
  - before/after protected tripwire PASS、JSON parse、evidence digest 與 git diff --check PASS
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_preauth_blocker_resolution_20260824/
result_path: artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0370-PREAUTH-BLOCKER-RESOLUTION-20260824-RESULT.md
---

# G8 v0.3.370 pre-authorization blocker resolution

## 工作名稱 → 正在做什麼 → 現在狀態

G8 pre-authorization blocker resolution → 唯讀收斂 source authority、exact allowlist 與 promotion plan readiness → `READY / STRICT READ-ONLY`

## Root Question

在不 fetch、不改 Git refs、不改 production 的前提下，能否唯一決定 future adoption/reset 應採用的 source SHA，證明該 source 與 `v0.3.370` 的 runtime 等價邊界、產出 formal reconciler 可接受的 exact allowlist，並讓既有 promotion `plan` 以 current inputs 回傳可人工審查的 deterministic plan？

## Requirements Trace

| ID | requirement | traces_to |
| --- | --- | --- |
| `FR-001` | 以 read-only remote query 鎖定 current remote main authority，不修改任何 local/remote ref。 | `SC-001` |
| `FR-002` | 比對 `v0.3.370^{}`、remote main、local main 與 production actor，決定唯一 source SHA；patch equivalence 只作輔助。 | `SC-001`, `SC-002` |
| `FR-003` | 從實際 changed paths 推導 exact/minimal allowlist，並用既有 formal reconciler 驗證 authority/allowlist phase。 | `SC-002` |
| `FR-004` | 以既有 `pantheon_content_runtime_promotion plan` 做唯讀 plan rehearsal，鎖定 target runtime digest、capacity receipt、locator、write/backup set、rollback order 與 plan digest。 | `SC-003` |
| `FR-005` | 全程以 before/after tripwire 證明 production 與 Git refs 零 mutation。 | `SC-004` |

| ID | success criterion |
| --- | --- |
| `SC-001` | remote main query 有時間、URL、SHA 與可重現命令；authority 結論不依賴 fetch 或 tracking ref 更新。 |
| `SC-002` | source decision 只有一個 SHA；allowlist 是由實際 diff 推導的精確 paths/patterns，formal probe 越過 `ALLOWLIST_REQUIRED` 與 `REMOTE_DIVERGED`，最早可接受 blocker 是 pre-adoption actor/manifest mismatch。 |
| `SC-003` | promotion plan 回 `READY_TO_APPLY` 並產生 deterministic `plan_digest`，或以單一明確 failure code 留在 `BLOCKED/UNKNOWN`；plan 不等於授權。 |
| `SC-004` | protected before/after changed surfaces 為 `[]`，且沒有 fetch/push/tag/ref/production mutation。 |

Current frontier：`FR-001 → FR-002 → FR-003 → FR-004 → FR-005`。任何前一步 `BLOCKED/UNKNOWN` 時，後一步只可做不依賴該結論的唯讀診斷，不得猜值補洞。

## 必讀 Authority

1. `AGENTS.md`
2. `handoff_20260824_g8_readiness_blocked_content_expansion.md`
3. `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0370-PRODUCTION-ADOPTION-RESET-READINESS-20260822-RESULT.md`
4. `artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_production_adoption_reset_readiness_20260822/execution-contract.json`
5. `artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_production_adoption_reset_readiness_20260822/authority-receipt.json`
6. `artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_production_adoption_reset_readiness_20260822/command-receipt.md`
7. `artifacts/fortune_council/four_lane_runtime_execution/g8_current_production_readonly_reconciliation_v0370_20260822_retry_1/release-observation.json`
8. `scripts/pantheon_g8_production_preactivation.py`
9. `scripts/pantheon_content_runtime_promotion.py`
10. `tests/test_pantheon_g8_production_preactivation.py`
11. `tests/test_pantheon_content_runtime_promotion.py`
12. `<ai-core-root>/rules/24-storage-capacity-safety.md`
13. `<ai-core-root>/rules/25-production-canary-readiness.md`

## Existing Capability First

1. 先對主工作區執行 task-semantic CodeGraph query，再以限域 source read 確認入口；不得因 detached worktree 沒 index 就直接全 repo `rg`。
2. Git remote truth 只允許一次 bounded read-only query（例如 `git ls-remote --heads origin main`）；可讀公開/既有授權 remote，不得登入、改 credential、fetch 或修改 refs。
3. 沿用 `scripts.pantheon_g8_production_preactivation` 的 `evaluate_authority`／formal CLI；禁止另寫 reconciler。
4. 沿用 `scripts.pantheon_content_runtime_promotion plan`、`agy_content_publisher.runtime_manifest_digest`、既有 Rule 24 capacity receipt 與 canonical observation；可在 task-owned evidence 或 explicit local-only temporary directory 產生 helper/input，禁止重造 promotion workflow。
5. 若需要 clean source checkout，只能建立 local-only temporary clone/worktree；不得修改主工作區、production actor 或 remote。臨時輸出不得提交，且清理前須確認無唯一證據。

## 執行契約

### Slice A — Git/source authority

1. 保存 `remote-authority.json`：remote URL（遮蔽 credential）、query time、remote main SHA、release tag peeled SHA、local main/HEAD/origin-main ref、production actor SHA。
2. 保存 ancestry/tree/patch/diff evidence。不得把 patch-id equivalence、local `origin/main` 或狀態文字當 remote current truth。
3. 分析 `v0.3.370^{}` 到 current remote main 的每個 changed path，區分 runtime-affecting、docs/evidence-only、unknown；`unknown` 一律 fail closed。
4. `source-decision.json` 必須只給一個 future promotion source SHA，或 `BLOCKED/UNKNOWN`；同時說明如何讓 post-adoption formal reconciler 的 actor/manifest/origin authority 可收斂。

### Slice B — Formal allowlist proof

1. `source-allowlist.json` 必須列每個 pattern、實際 matched paths、未匹配 paths、選擇理由與 overmatch 檢查；優先 exact paths，只有同一受控 evidence family 才可使用 bounded glob。
2. 使用 canonical observation 與既有 formal reconciler 做一次必要 probe；可用 task-owned/temp clean checkout讓 `HEAD == required_source`，但不得改主工作區 HEAD。
3. Probe 必須保存完整 argv、input digests、exit code、result 與內建 mutation tripwire。
4. 可接受 pre-adoption 結果：越過 `ALLOWLIST_REQUIRED`、`LOCAL_HEAD_MISMATCH`、`REMOTE_DIVERGED`、`SOURCE_DRIFT`，最早停在 `ACTOR_MANIFEST_AUTHORITY_MISMATCH` 或更後面的 phase-specific blocker。這不是 production GO。

### Slice C — Promotion plan readiness

1. 從唯一 source checkout 計算 target runtime digest；鎖定 expected origin、current actor/manifest/stage/queue identity、preserved run、runtime Python/uv locators與 capacity receipt path/digest。
2. Capacity receipt 只可沿用符合 `pantheon_content_runtime_promotion._validate_capacity_receipt` 的既有 current evidence；若不 current 或不滿足 contract，固定 `BLOCKED / CAPACITY_RECEIPT_NOT_READY`，不得重跑 production capacity mutation。
3. 只可呼叫 CLI `plan` 或同等 public `plan_promotion`；禁止 `apply`、`rollback`、`finalize`。Prospective transaction root 可指向正式 bounded locator，但 plan 前後必須 tripwire，且不得產生 transaction receipt、rollback bundle或 production檔案。
4. 保存 `promotion-plan.json`、`promotion-plan-inputs.json` 與 `promotion-plan-command.md`。`READY_TO_APPLY` 只代表技術 plan 可供主線審查，不代表人類授權。

### Slice D — Result and tripwire

1. 保存 before/after protected snapshot與 `mutation-tripwire.json`；至少覆蓋 Git refs/packed-refs、actor、manifest、queue、state、transaction、publisher lock、stage、live plist、barrier與 launchctl identity。
2. 產出唯一 RESULT，verdict 只可：
   - `READY-FOR-AUTHORIZATION`：`SC-001..004` 全部成立；停止並回主線。
   - `BLOCKED`：存在具體矛盾、missing current receipt或 formal/plan failure。
   - `UNKNOWN`：證據不足但未形成矛盾。
3. RESULT 必須列 source SHA、remote main SHA、allowlist locator、plan digest、rollback order、tripwire、剩餘 blocker與下一步；不得含授權文案。

## Allowed Writes

只可提交 frontmatter `ownership` 兩個位置。Local-only temporary checkout／stdout 可用於唯讀證明，但不得把 clone、cache、binary、PNG、browser artifact、runtime tree 或 secret 帶進 commit。

## Verification

1. 驗證所有 JSON 可解析、evidence digests 全數對上。
2. 驗證 changed paths 只在 ownership；原未追蹤檔不得 add、修改或刪除。
3. 驗證 remote 操作只有 bounded read-only query；production/Git refs mutation count 全為 `0`。
4. 跑最小受影響測試：formal reconciler authority/allowlist 與 promotion plan tests；不得跑整包無關 suite。
5. 執行 `git diff --check`。
6. 建立單一 candidate commit；禁止 push/tag/merge。交付完整 SHA、parent、changed paths、verdict、驗證與剩餘 blocker。

## Stop-loss

- 同一 blocker 第 3 次失敗即停；禁止第 4 次重試。
- remote query 需要登入、credential 變更或回傳不唯一時，固定 `BLOCKED / REMOTE_AUTHORITY_UNAVAILABLE`。
- 任一動作需要 fetch、Git ref mutation、production write、sudo、launchctl mutation或 promotion non-plan command，立即停止並固定 `BLOCKED / UNAUTHORIZED_MUTATION_REQUIRED`。
- protected before/after 任一改變，固定 `BLOCKED / MUTATION_DETECTED`。
- 任何 source authority、allowlist或 plan input 不唯一，固定 `BLOCKED`；不得自行選一個繼續。

## Pending Forks

- `pending / adoption-reset execution`：只有本卡 `READY-FOR-AUTHORIZATION` 且主線獨立 Review GO 後，才可向使用者提出一次 bounded production 授權。
- `pending / publication canary`：只有 authorized adoption/reset成功、fresh formal reconciliation GO、Rule 24/25 current後，才可另卡。
- `pending / Content Expansion`：P0-02 canary未成功前不進 sustained 10K publishing；不得吞入本卡。
