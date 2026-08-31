---
id: PANTHEON-GATE-A-C-ACCEPTED-BASE-CLOSEOUT
parent: PANTHEON-FOUR-LANE-CURRENT-ACTOR-OPERABILITY-ACCEPTANCE
type: acceptance-closeout
status: ready
root_question: 將目前未提交的 Slice 2A fixture、Gate C case-local evidence、wrong-mode source repair 與相關 receipts 收斂成可 review 的 exact accepted base。
current_head: 0f61545f8c6b561742b27792b8fef11ae8b1ccc5
current_tag: v0.3.375
accepted_base_sha: pending-until-accepted-base-commit
production_activation_authorized: false
shadow_execution_authorized: false
external_write_authorized: false
commit_authorized: true
owner_commit_authorization_date: 2026-08-31
merge_push_deploy_authorized: false
frontier: Accepted base closeout；sealed capability repair blocked until accepted_base_sha exists.
---

# 派工卡：Gate A-C Accepted Base Closeout

## 任務目的

把目前 working tree 中已形成但尚未成為 accepted commit 的 Gate A-C 相關修改，收斂成一個可重現、可獨立 review、Owner 已授權建立 commit 但 SHA 尚待 commit 形成的 exact accepted base 候選。

本卡不修 sealed replay、不建立 D/E runtime capability、不執行 activation/shadow。通過本卡只代表 Gate A-C 的 accepted base 候選可被審核；Owner 已於 2026-08-31 授權建立 accepted-base commit，`accepted_base_sha` 仍須等實際 commit 後形成。

## Current Fact Snapshot

| 項目 | 目前事實 | 驗收含義 |
| --- | --- | --- |
| HEAD | `0f61545f8c6b561742b27792b8fef11ae8b1ccc5` | 目前只是 repo HEAD，不是 accepted base。 |
| tag | `v0.3.375` | tag 與 HEAD 對齊，但不包含 working tree 修改。 |
| modified source/test | `scripts/agy_gemini_coordinator.py`、`tests/test_agy_gemini_coordinator.py`、`tests/test_agy_content_publisher.py`、`tests/test_agy_multilingual_pipeline.py` | 需盤點 provenance、重驗、review 後才可成為候選。 |
| untracked cards/receipts | four-lane runtime execution 目錄下 20260831 卡片與 evidence root | 只能納入本 closeout 的相關 evidence，不得混入 sealed capability scope。 |
| accepted base SHA | 已授權 commit；SHA 尚待 commit 形成 | 不得以 `0f61545f` 冒充 accepted base。 |

## Allowed Scope

只允許下列工作：

- diff inventory：列出每個 dirty 檔案與 untracked receipt 的來源、目的、所屬 slice。
- provenance mapping：把修改歸類到 Slice 2A fixture alignment、Gate C case-local evidence、wrong-mode source repair、result receipts。
- impacted verification rerun：重跑受影響測試與 exact gates，保存 raw outputs。
- independent code review：針對 source/test diff、allowlist、zero-mutation claims、history/source-owner evidence 做獨立 review。
- candidate commit topology：提出一個或多個候選 commit 分組，但不得 commit。
- repo-local receipt：保存本 closeout 的 evidence/result receipt。

## Allowed Source, Tests, Artifacts

| 類別 | 允許路徑 | 用途 |
| --- | --- | --- |
| owner source | `scripts/agy_gemini_coordinator.py` | 僅允許 wrong-mode immutable prevalidation repair 的既有 diff 被盤點與驗收；不得新增 sealed runtime capability。 |
| coordinator tests | `tests/test_agy_gemini_coordinator.py` | Slice 2A fixture alignment、Gate C negative cases、wrong-mode RED-GREEN 驗收。 |
| publisher tests | `tests/test_agy_content_publisher.py` | Gate C selector/locale/ledger 相關 negative evidence 與 impacted regression。 |
| multilingual tests | `tests/test_agy_multilingual_pipeline.py` | Gate C pipeline negative evidence 與 impacted regression。 |
| cards/receipts | `artifacts/fortune_council/four_lane_runtime_execution/**` | 僅本議題相關卡片、result receipt、raw output、review receipt。 |

任何不在 allowlist 的 source、tests、artifact 修改都必須分類為 unrelated dirty 或 allowlist drift，不能被本卡吸收。

## Unrelated Dirty Preservation

本卡執行者必須先以 `git status --short` 與 focused diff inventory 保存 dirty baseline。遇到不屬於 Gate A-C closeout 的修改時：

- 不得 revert、checkout、reset 或重寫。
- 不得把 unrelated dirty 納入候選 accepted base。
- 若 dirty overlap 導致無法判定 provenance，立即 `BLOCKED_EXACT_PROVENANCE_UNRESOLVED`。
- Owner 已於 2026-08-31 明確授權建立 accepted-base commit；若執行 commit，仍必須使用精確 path staging，不得 broad `git add .`。

## Split Strategy

候選 accepted base 至少必須分清下列邏輯群組；可以在 review 後合併為單一 commit，但 commit message 與 receipt 必須保留分組追溯。

| Slice ID | 名稱 | 內容 | Blocking edge |
| --- | --- | --- | --- |
| SL-BASE-001 | Fixture alignment closeout | `_CampaignTranslationClient` test-only fixture 依 fresh provider schema 產出合法 payload，維持 provider calls = 0、production mutation = 0。 | 無；目前 frontier。 |
| SL-BASE-002 | Gate C evidence closeout | 八類 negative case 的 exact node、pre-I/O fail-closed、case-local before/after zero mutation evidence。 | 依賴 SL-BASE-001 baseline 綠。 |
| SL-BASE-003 | Wrong-mode repair closeout | wrong-mode 在 `_run_identity_lock` 前 immutable prevalidation；保留 lock 內 revalidation；gen07 維持 qualified semantics。 | 依賴 SL-BASE-002 對 wrong-mode defect 的分類。 |
| SL-BASE-004 | Receipt and review closeout | raw outputs、allowlist audit、independent review、candidate topology。 | 依賴 SL-BASE-001 至 SL-BASE-003 驗收完成。 |

禁止把以下任何項目混入本 accepted base：

- sealed replay provider/outbox/runner transport repair。
- four-lane shadow consumption。
- successful teardown owner。
- launchctl cohort mutation。
- new scheduler、queue、registry、FSM、database、canonical writer 或第二套 runtime。

## Spec / Standards Axes

本卡驗收需沿下列軸線明確對帳：

| Axis ID | 標準軸 | 要求 |
| --- | --- | --- |
| AX-001 | Source ownership | 只有經 history/source-owner gate 證明的 `scripts/agy_gemini_coordinator.py` wrong-mode bounded diff 可進候選。 |
| AX-002 | Runtime boundary | test-only fixture 與 evidence 不得自動升格為 runtime actor；actor SHA 與 harness SHA 必須分欄。 |
| AX-003 | Zero mutation | Gate C invalid cases 必須在 first I/O 前 fail closed，before/after durable snapshot 相等。 |
| AX-004 | Baseline preservation | requirement-mapped baseline、fresh/legacy safety matrix、impacted positive controls 必須全綠。 |
| AX-005 | Evidence quality | raw pytest outputs、exact node IDs、case-local receipts、allowlist audit 與 independent review 都必須存在。 |
| AX-006 | Governance boundary | commit 已由 Owner 於 2026-08-31 授權；merge/push/deploy/activation/external write 仍未授權；candidate SHA 只能等 commit 實際形成後產生。 |

## Exact Gates

執行者必須用 fresh process 保存命令、raw output 路徑、exit code、provider/service/production mutation 計數。

| Gate ID | 驗收項 | Pass 條件 |
| --- | --- | --- |
| GATE-BASE-001 | Diff inventory | 所有 dirty/untracked 變更均有 provenance、slice、allowlist verdict。 |
| GATE-BASE-002 | Slice 2A baseline | exact baseline、fresh/legacy safety matrix、private campaign E2E impacted tests 全綠；provider calls = 0、production mutation = 0。 |
| GATE-BASE-003 | Gate C negative evidence | 八類 negative gaps 與 13-node impacted manifest 全綠；無 skip/xfail/waiver。 |
| GATE-BASE-004 | Wrong-mode repair | wrong-mode RED-GREEN、`coordinator.lock` pre-I/O 不存在、gen07 qualified semantics 維持。 |
| GATE-BASE-005 | Allowlist audit | diff 僅含本卡 allowlist；sealed capability/runtime D/E diff 必須為 0。 |
| GATE-BASE-006 | Independent review | review 結論為 PASS，且 findings 均 resolved 或明確 classified non-blocking。 |
| GATE-BASE-007 | Whitespace/syntax hygiene | `git diff --check` 通過。 |
| GATE-BASE-008 | Candidate topology | 列出候選 commit grouping、files、message draft、rollback plan；不得形成 commit。 |

## Required Evidence Receipt

本卡結果 receipt 建議使用：

`artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-GATE-A-C-ACCEPTED-BASE-CLOSEOUT-20260831.md`

Receipt 至少包含：

- root question、current HEAD/tag、dirty baseline。
- diff inventory table。
- provenance mapping table。
- exact test command manifest 與 raw output links。
- exact node IDs 與 Gate C case-local receipt links。
- provider/service/production mutation counters。
- actor SHA / harness SHA split。
- independent review result。
- candidate commit topology。
- final verdict：`ACCEPTED_BASE_CANDIDATE_READY` 或 `BLOCKED_EXACT_<reason>`。

## Candidate SHA Contract

`accepted_base_sha` 不可在本卡內自行填入。Owner 已於 2026-08-31 明確授權建立 accepted-base commit；只有在以下條件同時成立且 commit 實際形成後，才可記錄 candidate SHA：

- `GATE-BASE-001` 至 `GATE-BASE-008` 全部 PASS。
- unrelated dirty 已被排除或保留在未 staged 狀態。
- commit staging 使用精確 path list。
- commit message 明確標示 Gate A-C accepted base closeout，不宣稱 D/E sealed capability。
- commit 後重新記錄 `git rev-parse HEAD`、`git status --short`、`git diff --check`。

## Stop Conditions

任一條件成立即停止，回報 `BLOCKED_EXACT_<reason>`：

- 找不到 dirty diff 的來源或所屬 slice。
- 發現 sealed capability、D/E runtime、launchctl、queue/registry/FSM、Publisher domain logic 被混入。
- impacted tests、Gate C manifest、wrong-mode repair 或 baseline 任一失敗。
- provider/network/service/production mutation 計數非 0。
- before/after durable snapshot 不相等，且無法分類為已知 qualified external drift。
- independent review NO-GO 或 unresolved blocker。
- 需要 merge、push、deploy、activation、external write 或 production mutation，但尚未取得 Owner 明確授權。

## Rollback / Removal

本卡本身 rollback 僅為移除本 closeout card 與其 repo-local result receipt。若後續 Owner 授權形成 accepted base commit，rollback 必須是精確 revert 該 commit 或精確 path-level inverse patch；不得使用 broad reset/checkout，也不得影響 unrelated dirty。

Rollback 後必須重新保存：

- `git status --short`。
- impacted exact tests 的預期 RED 或 PASS 狀態。
- `git diff --check`。
- remaining dirty inventory。

## Traceability

| Trace ID | traces_to | 驗收證據 |
| --- | --- | --- |
| TR-BASE-001 | SL-BASE-001、AX-004、GATE-BASE-002 | Slice 2A baseline raw outputs、fresh/legacy safety matrix。 |
| TR-BASE-002 | SL-BASE-002、AX-003、GATE-BASE-003 | Gate C exact node IDs、before/after zero-mutation receipts。 |
| TR-BASE-003 | SL-BASE-003、AX-001、GATE-BASE-004 | wrong-mode RED-GREEN、history/source-owner/invariant evidence。 |
| TR-BASE-004 | SL-BASE-004、AX-005、GATE-BASE-006 | independent review receipt 與 finding resolution。 |
| TR-BASE-005 | AX-002、GATE-BASE-005 | actor SHA / harness SHA split、sealed/runtime D/E zero diff audit。 |
| TR-BASE-006 | AX-006、GATE-BASE-008 | candidate topology，且 commit SHA 欄位仍為 pending-until-accepted-base-commit。 |

## Why Not Less / Why Not More / Do Not Absorb

- `why_not_less`：只看 `git status` 或只跑單一 pytest，無法證明 Gate A-C 的 dirty diff 可追溯、可 review、可回退，也無法防止 `0f61545f` 被誤當 accepted base。
- `why_not_more`：本卡只建立 accepted base 候選，不修 D/E blocker；sealed replay、四 lane shadow consumption、successful teardown 必須等 accepted base SHA 存在後另開 capability card。
- `do_not_absorb`：不吸收第二套 runtime、新 registry/FSM、production launchctl、Publisher domain rewrite、public content publish、external provider call、未分類 dirty diff 或 waived failure。

## Final Handoff Format

交付時只回報：

- closeout result receipt path。
- dirty inventory 與 provenance verdict。
- exact gates PASS/BLOCKED table。
- independent review verdict。
- candidate topology。
- 是否仍維持 `BLOCKED_D_E_NO_EXISTING_SEALED_PROVIDER_OUTBOX_REPLAY_SEAM`。

不得宣稱 `GO_FOUR_LANE_RUNTIME_CURRENT`，不得宣稱 accepted base SHA 已存在，除非 accepted-base commit 已實際形成且 commit 後 evidence 已更新。
