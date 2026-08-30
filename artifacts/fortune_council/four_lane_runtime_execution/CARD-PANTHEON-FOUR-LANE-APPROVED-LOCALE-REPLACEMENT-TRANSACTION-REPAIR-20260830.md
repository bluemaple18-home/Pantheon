# Pantheon 四線：Approved Locale Replacement Transaction Repair

## 工作名稱 → 正在做什麼 → 現在狀態

`Approved Locale Replacement Transaction Repair` → 在既有 approved-revision stage、translation apply 與 publisher transaction 內，補齊 replacement/attempt lifecycle、exact existing-locale replacement與post-push reconciliation → `REWORKED_READY_FOR_SAME_REVIEWER / IMPLEMENTATION_NOT_STARTED`。

## 同卡 REWORK closure

已吸收原 Reviewer 唯一 blocker：現行 remote push 成功至 translation ledger/evidence落盤之間缺 durable recovery identity。本版不新增 transaction subsystem；在既有 publisher unresolved-push/state/evidence family中，要求local commit/tag已形成、remote mutation尚未開始時先寫 `PUSH_PREPARED`，並用closed state table讓second execute只補exact missing remote edge或finalize同一ledger/evidence。

## 唯一裁決

`GO_BOUNDED_CROSS_SEAM_REPAIR`

本卡只允許一個跨 seam、但仍由既有 owner 持有的 transaction：

1. lifecycle-neutral approved-revision descriptor/seal 可明確表示 `continuation_generation` 或 `replacement_attempt`，不得把 attempts 偽造成 generations，也不得削弱原 continuation branch。
2. publisher/apply 只能對 exact existing `(source_article_id, locale)` record 做 receipt-first in-place replacement；public registry path、URL 與 record order 不變。
3. 既有 publisher `MutationJournal`、publisher state/evidence family、translation ledger、Git commit/tag/push 繼續擁有 transaction 與 rollback/reconciliation；不新增 authority owner。remote push 前必須有 durable `PREPARED` evidence，push 後 crash 只能收斂同一 commit/tag/ledger/evidence，不得重做 release。

若實作 discovery 證明需要修改超過下列 2 個 production source files、需要第三個 authority owner，或不能在既有 module writer 上證明 exact single-record rollback，立即裁決 `BLOCKED_SCOPE_EXPANSION`，不得先交付 staging-only patch。

## Spec sources

- `CARD-PANTHEON-FOUR-LANE-REPLACEMENT-APPROVED-REVISION-LIFECYCLE-RCA-20260830.md`
- `PANTHEON-FOUR-LANE-REPLACEMENT-APPROVED-REVISION-LIFECYCLE-RCA-20260830/RESULT.md`
- `PANTHEON-FOUR-LANE-EN-I18N-REWRITE-CONTENT-REPAIR-20260830/RESULT.md`
- `PANTHEON-FOUR-LANE-EN-I18N-REWRITE-FORMAL-REREVIEW-20260830/`
- `PANTHEON-FOUR-LANE-E01-G75-EN-FINAL-PUBLISH-ACCEPTANCE-20260830/RESULT.md`

Current production-shaped target：

- replacement run：`auto-i18n-en-aa637e1bf05d3ad21429-replacement-01`
- source/locale：`ASTRO-BASE-03 / en`
- approved candidate file SHA-256：`26dd6ccf15a37a165f2ec11f9dd0220db26b9cdbc7fc8b2641b50b551e6731d1`
- approved article SHA-256：`7a63cb36b0dae48df870647653846b9d3e20da97f1725f232d9139c70d378314`
- approved review SHA-256：`abae910fac8dbffd353d698fff25ae78ef08d2b3eab7f62b5324630dc326b1a5`
- Formal Reviewer result SHA-256：`1446c10ad80a8e942c553419bf5aa957ded3dbdd2d6bad646fa05047a6d21e2c`
- replacement registry SHA-256：`25e08420193a9640ad00cbcdf1107590a23d2e22c9d73e9ddcc4235ccf8deeef`
- prior public owner：run `codex-emergency-i18n-20260726-astro-base-03`，source SHA `5a85b2c48e4a640ca0240f5537b3dde2c399200ff884ba2395c17d60a0bef824`
- exact module：`app/web/static/article-locale-codex-emergency-i18n-20260726-astro-base-03.js`
- public registry：`app/web/static/article-locales.js`；`getArticleLocaleRecord` 使用 first-match，因此不得用 overlay 或 append 假裝 replacement。

## Source discovery 與 implementation ceiling

### 已掃描 consumer chain

| 節點 | 現況 | 本卡決定 |
|---|---|---|
| stage plan/apply/load/rollback | `scripts/agy_multilingual_pipeline.py:2864-3185` 硬綁 continuation/generation | 同一 seal contract 內加入 closed terminal owner union |
| CLI stage entry | `scripts/agy_multilingual_pipeline.py:4324-4418` continuation args 全 required | 明確 owner kind；只讓對應 branch 的 locks 必填 |
| translation apply | `scripts/agy_multilingual_pipeline.py:4188-4260` create-only，existing identity fail closed | 加入 explicit staged replacement descriptor；預設 create-only 完全不變 |
| publisher selector | `scripts/agy_content_publisher.py:2795-2895` exact run 可選 replacement | 沿用 selector；只把 seal-normalized owner locks 帶入 apply |
| publisher apply/transaction/ledger | `scripts/agy_content_publisher.py:4339-4485` 已有 journal、release、ledger owner，但 push→ledger/evidence 有 crash window | 沿用；在既有 unresolved-push/state/evidence family補 pre-push PREPARED 與 post-push reconciliation |
| push outcome/recovery | `scripts/agy_content_publisher.py:2397-2494,3683-3793` 只有 push exception才寫 unresolved control | 擴充同一 control/evidence family；不得建立第二 ledger/FSM |
| public loader | `app/web/static/article-locales.js:537-568` first-match | 只測不改；identity/URL 必須維持同一 record position |
| exact public module | 三語同 module，EN/JA/KO 有固定順序 | production code不得把該檔列為 source change；fixture 證明只換 EN |

### Production source allowlist（精確、最多 2 files）

1. `scripts/agy_multilingual_pipeline.py`
2. `scripts/agy_content_publisher.py`

### Test allowlist（精確、最多 2 files）

1. `tests/test_agy_multilingual_pipeline.py`
2. `tests/test_agy_content_publisher.py`

### Evidence allowlist

- 本卡。
- 一個與本卡同名的 review/implementation result 目錄；不得加入 production snapshot、binary 或 provider response。

### LOC ceiling

- production source：新增淨 LOC 合計 `<= 420`；其中 multilingual `<= 190`、publisher `<= 230`。
- tests：新增淨 LOC 合計 `<= 760`；其中 multilingual tests `<= 360`、publisher tests `<= 400`。
- 任一 production source file 新增 helper `<= 6`；不得建立新 module。
- 超過 ceiling 時先縮約；不能縮回即 `BLOCKED_SCOPE_EXPANSION`，不得用「需要完整」作擴張理由。

## User story

### US-001

作為 production publisher，我要在不偽造 lifecycle shape 的情況下，發布已由 Formal Reviewer 核准的 replacement-attempt candidate，並以同一 transaction 精確替換既有 locale record；任何 identity drift、歧義或中途失敗都必須在 local rollback 或 exact remote reconciliation 邊界內 fail closed。

## Functional requirements

### FR-001 — Closed terminal owner union

approved-revision plan、payload、seal、loader 與 rollback 必須共同使用一個 closed `terminal_owner` descriptor：

- `kind=continuation_generation`
  - 保留現有 `terminal_generation`、continuation state SHA、generation candidate/review/tree SHA 與 next-generation absence。
  - 原 `complete`、terminal digests、root `REJECT + hard_failure=true + findings` invariant 不變。
- `kind=replacement_attempt`
  - 鎖 exact queue registry path/content SHA、`replacement_of`、`replacement_reason`。
  - attempts 必須正規、連續且只允許 `01..03`；terminal attempt 明示為 `03`，不得有 attempt04。
  - root candidate/review SHA 必須逐 bytes 等於 attempts/03 candidate/review SHA；attempt tree SHA 必須被 seal。
  - root terminal review 保留 ordinary `REJECT + findings`；不得新增或要求偽造 `hard_failure=true`。
  - 不得存在 continuation state 或 generations tree。

owner kind 必須由 caller 明示；不得依目錄存在與否猜測。descriptor 必須成為 plan digest、operation id、payload、receipt、current seal 與 loader current-lock validation 的一部分。

`terminal_owner` 是 exact-key closed object，未知 key、缺 key或兩 branch mixed fields一律 RED：

- 共用 key只有：`kind`、`root_candidate_sha256`、`root_review_sha256`、`terminal_audit_tree_sha256`。
- `continuation_generation` 額外且只允許：`terminal_generation`、`continuation_state_sha256`、`terminal_generation_candidate_sha256`、`terminal_generation_review_sha256`。
- `replacement_attempt` 額外且只允許：`terminal_attempt`（固定 `3`）、`replacement_of`、`replacement_reason`、`replacement_state_sha256`、`terminal_attempt_candidate_sha256`、`terminal_attempt_review_sha256`。
- top-level seal維持既有 closed common keys；所有 branch-specific fields只准存在 `terminal_owner` 內，不再保留對兩 branch都可能被誤讀的裸 `terminal_generation`／`continuation_state_sha256`。

### FR-002 — Formal approval 與 source/current locks 不變

兩種 owner kind 均必須維持既有：approved candidate/review/result file SHA、article SHA、formal job/request identity、source SHA、actor SHA、queue state SHA、publisher ledger SHA。Formal Reviewer `APPROVE` 不能單獨授權 publish。

### FR-003 — Exact existing locale replacement descriptor

只有 `replacement_attempt` 且 stage seal 明示 public replacement descriptor 時，apply 才能進 replacement branch。`public_replacement` 是exact-key closed object，只允許：

- `contract`（固定 `approved-locale-existing-record-replacement`）
- `source_article_id`
- `locale`
- `old_run_id`
- `old_source_sha256`
- `old_record_sha256`
- `module_path`（canonical repo-relative）
- `module_export`
- `record_index`（只作一致性lock）
- `module_before_sha256`
- `module_after_sha256`
- `manifest_path`（固定canonical repo-relative `app/web/static/article-locales.js`）
- `manifest_sha256`
- `replacement_run_id`
- `replacement_source_sha256`
- `approved_article_sha256`
- `replacement_record_sha256`

module path 必須位於 canonical `app/web/static` 下、regular file、非 symlink；manifest 同樣必須 canonical regular file。descriptor 不得接受 absolute/parent traversal path。

缺少、增加或重複任何key都RED，不得帶 executable 欄位。record digest唯一算法是對解析後的單一 closed record呼叫既有 `compact_json_bytes(record)`；old/new均使用同一算法，不得用 pretty JSON slice或Node stringify另算。generated module grammar只接受：既有固定 comment、exactly one expected `export const <IDENTIFIER>_ARTICLE_LOCALES = ` assignment、一個 JSON array、尾端 semicolon/newline；額外 executable text、第二 export、dynamic expression或fallback parser全部 RED。

### FR-004 — Single exact record, no overlay

apply 必須解析 descriptor 指定的既有 locale module，驗證只有一個 exact old match；再用 approved record 原地替換同一 index。以下任一情況 mutation 前拒絕：

- old record SHA、module SHA、manifest SHA、runId、source SHA 不符。
- `(source_article_id, locale)` 在 public inventory 為 0 或多筆。
- 指定 module 內為 0 或多筆 match。
- public inventory first-match 與 descriptor owner 不同。
- module/export shape 非既有 generated closed form。
- symlink、non-regular、canonical path drift。

禁止新增 replacement module、manifest import/spread、overlay precedence 或改 registry order。

### FR-005 — Receipt-first transaction and idempotency

stage receipt 在 content mutation 前必須包含 old/new record、module、manifest digests與 replacement lineage；publisher plan/dry-run重算 after bytes並驗證一致。execute 仍由既有 `MutationJournal.begin/capture` 包住 apply、release與local commit/tag。remote push前必須先在既有 publisher unresolved-push/state/evidence family原子寫入 `PUSH_PREPARED` receipt。

- apply 後只有指定 module 內容可變；manifest bytes必須不變。
- 同 module其他 locale/record canonical bytes與 order不變。
- `PUSH_PREPARED` 必須鎖 exact run/candidate/stage/reviewer/replacement lineage、old/new record/module/manifest SHA、base SHA、target local commit SHA、target version/tag、expected remote main/tag before refs、publish evidence path與 publication plan digest。
- local commit/tag完成後到remote push前，PREPARED receipt必須 durable `fsync`/atomic replace成功；失敗時不得push。
- exact second execute依 closed transaction state table裁決：只可首次 execute、補 exact missing remote edge、reconciliation-only finalize、或 exact already-published；不得 bump第二version、建立第二commit/tag、重寫content或重複ledger entry。
- current 既非 exact old、亦非 exact approved after，fail closed。

`PUSH_PREPARED` receipt同樣是exact-key closed object，只允許：`schema_version`、`status`（固定 `PUSH_PREPARED`）、`phase`（固定 `translation`）、`run_id`、`stage_receipt_sha256`、`approved_candidate_file_sha256`、`approved_article_sha256`、`approved_review_file_sha256`、`formal_review_result_sha256`、`formal_job_id`、`formal_request_sha256`、`replacement_of`、`replacement_reason`、`record_before_sha256`、`record_after_sha256`、`module_before_sha256`、`module_after_sha256`、`manifest_sha256`、`base_sha`、`target_commit_sha`、`version`、`target_tag`、`expected_remote_main_before`、`expected_remote_tag_before`（必須 `null`）、`publication_plan_digest`、`ledger_path`、`publish_evidence_path`、`recorded_at`。未知/缺失key、非canonical path、digest/ref grammar錯誤均RED。

### FR-006 — Existing ledger and Git remain owners

`translation_published_runs` 的既有 entry 加入：`staging_receipt_sha256`、`replaces_run_id`、`replaced_record_sha256`、`replacement_record_sha256`、`replacement_module_before_sha256`、`replacement_module_after_sha256`、`publication_plan_digest`。不得新增另一份 ledger。Git commit/tag仍是remote public bytes owner；MutationJournal仍是pre-push local rollback owner；既有 publisher control/evidence只記錄 PREPARED/finalization狀態。

`PUSH_PREPARED` 不是新 authority：它不能單獨證明published，也不能選candidate。每次 load都必須與 approved stage receipt、Formal Reviewer identity、local commit tree/tag、remote refs與既有 translation ledger交叉驗證；finalize後由exact commit/tag + ledger entry共同形成published authority。不得把它泛化成新FSM或第二transaction ledger。

### FR-007 — Public identity preservation

execute 後：

- `article-locales.js` path、bytes與 registry order不變。
- `getArticleLocaleRecord(ASTRO-BASE-03,en)` 回傳 replacement run/new source SHA/content。
- JA、KO與所有其他 records bytes/order不變。
- existing English public URL path 不變，只有正文/metadata更新。

### FR-008 — Zero-provider, bounded publish behavior

本 Repair 本身不得呼叫 Writer/Reviewer provider。TDD fixtures 要記錄 `provider_calls=0`；plan、dry-run、所有 negative tests 要記錄 `publish_calls=0`。只有後續正式 acceptance 在 fresh gates、explicit authorization 下可以 publisher execute。

### FR-009 — Closed push reconciliation

publisher entry在 `_assert_no_unresolved_push` 阻擋一般新工作前，僅可對exact selected translation run載入並驗證同一 `PUSH_PREPARED`。reconciliation必須讀remote main與target tag（含annotated/peeled identity），並依下列closed規則：

- remote main/tag皆為expected before：執行原exact atomic push。
- remote main已是target commit、tag仍為expected absent：只push exact target tag edge。
- remote tag已是target commit、main仍為expected base：只push exact target main edge。
- remote main/tag皆為target commit：不再push，直接reconciliation-only finalize ledger/evidence。
- ledger已exact matching但publish evidence缺失：只補同一 evidence；ledger/evidence皆exact matching時回 `ALREADY_PUBLISHED`。
- 任一remote ref為第三SHA、target tag有多重/不一致 object與peeled identity、commit tree/public after bytes/stage/lineage/plan digest不符：fail closed，保留PREPARED與證據供人工判讀。

remote divergence不得被當成成功，也不得嘗試force push、delete/rollback remote tag或rollback remote main。partial remote只允許補exact missing edge，不能重發兩邊。

finalization固定為：驗remote refs/after tree → idempotent append exact ledger entry → atomic寫publish evidence → 移除exact matching unresolved/PREPARED control。crash在最後清理前，second execute驗ledger/evidence完全匹配後只清理該control並回 `ALREADY_PUBLISHED`；正常已清理狀態則以exact ledger+evidence+remote refs回 `ALREADY_PUBLISHED`。`evidence存在但ledger缺失` 不可能由此順序形成，若觀察到即fail closed。

### Closed publication transaction state table

| Local/public state | PREPARED | Ledger/evidence | Remote main/tag | 唯一裁決 |
|---|---|---|---|---|
| exact old；未commit | absent | absent | exact before/absent | 首次execute |
| exact local commit/tag；remote仍before | absent（crash after commit before seal） | absent | exact before/absent | 只在parent/base、single tag、commit tree、approved after與release namespace全exact時補PREPARED；否則fail closed |
| exact after local commit/tag | exact | absent | exact before/absent | 執行一次atomic push |
| exact after | exact | absent | target/absent | 只補target tag |
| exact after | exact | absent | base/target | 只補target main |
| exact after | exact | absent | target/target | reconciliation-only寫同一ledger/evidence |
| exact after | exact | exact ledger/evidence缺 | target/target | 只補evidence |
| exact after | exact或finalized後absent | exact/exact | target/target | 必要時只清理exact stale control，回 `ALREADY_PUBLISHED`；不做release |
| exact old + committed/published identity | 任意 | matching或非空 | 任意 | fail closed |
| other bytes／remote第三SHA／tag歧義 | 任意 | 任意 | 任意 | fail closed；不碰remote |

plan-only與dry-run必須回傳：proposed record/module after digest、publication plan digest、當前state classification、預期唯一next edge；content/ledger/evidence/version/local commit/tag/push mutation全部為0。

## Success criteria

### SC-001

Exact replacement/attempt fixture 能 plan → execute stage → load → publisher dry-run，seal 中 `terminal_owner.kind=replacement_attempt`，無 continuation/generation artifact，provider=0、dry-run mutation=0。

### SC-002

既有 continuation/generation fixture 全部維持 GREEN，seal 明示 `terminal_owner.kind=continuation_generation`，原 hard-failure與 next-generation guards不變。

### SC-003

Exact existing `(ASTRO-BASE-03,en)` fixture只替換原 module同一 index；manifest bytes、JA/KO bytes、其他 records、registry order、public URL identity不變。

### SC-004

wrong old SHA、multiple inventory match、first-match ambiguity、symlink、non-regular、path drift全部在任何 file/ledger/version mutation前 RED。

### SC-005

stage second execute、verified-operation-before-current crash recovery、stage rollback、publisher apply rollback與publisher second execute全部 deterministic、idempotent且可重建 receipt chain。

### SC-006

既有 translation ledger entry與Git transaction唯一擁有 publication/rollback；repository 中無新增 registry、DB、FSM、ledger、canonical writer或 overlay module。

### SC-007

受影響 suites、`py_compile`、`git diff --check` 全部 PASS；source/test allowlist與LOC ceiling PASS。

### SC-008

push成功後、ledger append前注入crash；第二次exact execute驗target commit/tag、sealed after bytes與lineage後，只補同一ledger/evidence。version、content、commit、tag、push counts均不增加。

### SC-009

crash matrix七個窗口全部有closed結果：before commit、after commit before seal、after seal before push、main pushed/tag missing、both pushed/ledger missing、ledger finalized/evidence missing、second execute。remote SHA/tag/bytes任一drift都fail closed且remote mutation=0。

## Trace matrix

| ID | traces_to | 驗證 |
|---|---|---|
| US-001 | FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, SC-001, SC-002, SC-003, SC-004, SC-005, SC-006, SC-007, SC-008, SC-009 | 全 E2E fixture與 transaction receipt |
| FR-001 | SC-001, SC-002, SC-004, SC-005 | lifecycle union positive/negative/regression |
| FR-002 | SC-001, SC-002, SC-004 | formal/source/current drift matrix |
| FR-003 | SC-003, SC-004 | exact descriptor validation |
| FR-004 | SC-003, SC-004 | single-record replacement與 ambiguity RED |
| FR-005 | SC-003, SC-005, SC-008, SC-009 | receipt-first、dry-run、second execute、rollback |
| FR-006 | SC-005, SC-006, SC-008, SC-009 | ledger/Git/MutationJournal/PREPARED交叉驗證 |
| FR-007 | SC-003 | Node public loader identity fixture |
| FR-008 | SC-001, SC-004, SC-007 | provider/publish counters |
| FR-009 | SC-005, SC-008, SC-009 | closed remote reconciliation/crash matrix |

Trace preflight：無 dangling ID、無 duplicate ID、無 unresolved blocking decision、每個 FR/SC 都有驗證；Jira 為 `not-applicable`，理由是本卡只交付 repo-local Repair spec，未授權外部 Jira mutation。

## Ordered vertical slices

### SLICE-LIFECYCLE-UNION — Lifecycle-neutral seal

- `traces_to`: `FR-001`, `FR-002`, `FR-008`, `SC-001`, `SC-002`, `SC-004`, `SC-005`
- blocked_by：無。
- likely files：`scripts/agy_multilingual_pipeline.py`、`tests/test_agy_multilingual_pipeline.py`。
- RED：用 production-shaped attempts/01..03、replacement registry、root mirror、approved candidate/review/formal identity建立 fixture；現況精確 missing continuation RED。另保留 continuation positive regression。
- GREEN：最小 closed terminal-owner normalization；plan/apply/load/rollback同時驗同一 descriptor。CLI只依明示 kind要求branch-specific locks。
- verify：attempt positive；generation regression；attempt04、root!=attempt03、registry lineage drift、fake hard_failure、attempts+generations混合 shape全 RED；provider calls=0。
- output：staged receipt/payload/current seal可 authoritative 表示兩種 owner，無第二份 seal。

### CHECKPOINT-01 — Authority seal checkpoint

阻擋條件：`SLICE-LIFECYCLE-UNION` 未全綠不得進 public replacement。核對 source diff仍只有 multilingual file、continuation regression零退化、沒有第三 authority owner。

### SLICE-EXACT-LOCALE-REPLACE — Receipt-first in-place record replacement

- `traces_to`: `FR-003`, `FR-004`, `FR-005`, `FR-007`, `FR-008`, `SC-003`, `SC-004`, `SC-005`
- blocked_by：`SLICE-LIFECYCLE-UNION`、`CHECKPOINT-01`。
- likely files：`scripts/agy_multilingual_pipeline.py`、`tests/test_agy_multilingual_pipeline.py`。
- RED：existing three-locale module fixture重現 `translation already exists`；加入 wrong old SHA、0/multiple exact matches、public first-match ambiguity、symlink、non-regular、other-locale bytes、manifest/order drift。
- GREEN：只在 sealed replacement descriptor存在時解析 exact module、重算 proposed bytes、原 index替換；default create-only branch完全不變。先形成 seal receipt，execute才 atomic write；current==approved after只回 idempotent result。
- verify：old/new module digest、old/new record digest、JA/KO及其他record bytes/order、manifest bytes、public loader returned run/source/content、URL path identity；provider=0、publish=0 fixture。
- output：exact changed set只含既有 locale module；不得建立新 module或改 manifest。

### SLICE-PUBLISHER-TRANSACTION — Existing journal/ledger integration

- `traces_to`: `FR-005`, `FR-006`, `FR-007`, `FR-008`, `SC-003`, `SC-005`, `SC-006`
- blocked_by：`SLICE-EXACT-LOCALE-REPLACE`。
- likely files：`scripts/agy_content_publisher.py`、`tests/test_agy_content_publisher.py`。
- RED：publisher可 select staged replacement，但目前 apply collision。首批精確節點：`test_replacement_publisher_dry_run_recomputes_after_bytes_without_mutation`、`test_replacement_publisher_rolls_back_local_apply_before_commit`、`test_replacement_publisher_ledger_entry_binds_stage_lineage_and_record_digests`。
- GREEN：collector以 seal-normalized owner current locks驗證，不直接硬讀 continuation；publisher把 sealed replacement descriptor傳給 apply，先完成 journal capture與local release commit/tag，但本slice不聲稱remote transaction已closed。
- verify：dry-run、local execute、pre-commit rollback、ledger entry schema；其他 locales/records bytes不變。任何 publish simulation 都用 fake git/publisher，不做外部 push。
- output：stage receipt → exact module change → local commit/tag的可驗證candidate，交給下一slice建立PREPARED。

### SLICE-PUSH-RECONCILIATION — Durable PREPARED and exact remote convergence

- `traces_to`: `FR-005`, `FR-006`, `FR-008`, `FR-009`, `SC-005`, `SC-006`, `SC-008`, `SC-009`
- blocked_by：`SLICE-PUBLISHER-TRANSACTION`。
- likely files：`scripts/agy_content_publisher.py`、`tests/test_agy_content_publisher.py`。
- 第一個必寫RED：`test_replacement_publish_reconciles_crash_after_push_before_ledger_without_second_release`。在fake atomic push回傳成功後、ledger append前注入crash；第二次exact execute必須version/content/commit/tag/push count不增，只補同一ledger/evidence。
- 其他精確RED：
  - `test_replacement_publish_recovers_exact_local_commit_before_prepared_seal`
  - `test_replacement_publish_prepared_before_remote_push`
  - `test_replacement_publish_completes_only_missing_remote_tag_edge`
  - `test_replacement_publish_completes_only_missing_remote_main_edge`
  - `test_replacement_publish_reconciles_ledger_finalized_evidence_missing`
  - `test_replacement_publish_second_execute_is_exactly_idempotent`
  - `test_replacement_publish_rejects_remote_commit_tag_or_after_bytes_drift`
  - `test_replacement_publish_rejects_ambiguous_remote_tag_identity`
- GREEN：擴充既有 `_unresolved_push_path(state_root)` control/evidence family，使local commit/tag後先寫closed `PUSH_PREPARED`；一般新work仍被 unresolved control擋住，只有exact selected run進reconciliation。依closed state table只push missing edge或finalize現有ledger/evidence。
- verify：PREPARED plan digest與stage/formal/lineage/old-new bytes/local commit/tag/expected refs全匹配；remote divergence時push/ledger/content=0；不得force/delete remote refs。
- output：同一 publisher transaction閉合 stage → local commit/tag → durable PREPARED → exact remote refs → existing ledger/evidence。

### CHECKPOINT-02 — Transaction/rollback checkpoint

阻擋條件：前四 slice 未全綠不得做 full affected suite。核對 mutation order必須是 stage receipt已存在 → journal begin → exact module apply → local release commit/tag → durable PREPARED → remote push/missing-edge convergence → ledger finalize → evidence finalize。PREPARED前的local failure回復至before；PREPARED後若remote已變，只能exact reconcile，不宣稱或嘗試remote rollback。

### SLICE-REGRESSION-ACCEPTANCE — Full affected acceptance

- `traces_to`: `FR-001`, `FR-002`, `FR-003`, `FR-004`, `FR-005`, `FR-006`, `FR-007`, `FR-008`, `FR-009`, `SC-001`, `SC-002`, `SC-003`, `SC-004`, `SC-005`, `SC-006`, `SC-007`, `SC-008`, `SC-009`
- blocked_by：`CHECKPOINT-02`。
- likely files：兩個 test files；production source不得再增加 seam。
- RED/GREEN：不得另開水平測試階段；此 slice只整合前四 slice已存在的 vertical tests與補跨 seam E2E fixture。
- verify：
  - attempt lifecycle positive。
  - continuation/generation regression。
  - existing locale exact update positive。
  - wrong old record/module/source SHA。
  - multiple match與first-match ambiguity。
  - symlink、non-regular、canonical path drift。
  - other locale bytes、registry order、manifest bytes。
  - second execute/idempotency。
  - crash-before-current recovery。
  - stage rollback與publisher transaction rollback。
  - before commit、after commit before seal、after seal before push。
  - main pushed/tag missing與tag pushed/main missing的exact-edge收斂。
  - both pushed/ledger missing的reconciliation-only。
  - ledger finalized/evidence missing。
  - remote divergence、multiple tag、after bytes mismatch fail closed。
  - dry-run zero mutation。
  - ledger staging/replacement receipt。
  - Node public loader/public URL identity。
  - provider=0；negative/dry-run publish=0。
  - existing create-only translation apply regression。
  - `py_compile`、targeted tests、兩個受影響完整 suites、`git diff --check`。

## Current frontier

唯一可立即開工的 slice：`SLICE-LIFECYCLE-UNION`。

不得平行先做 publisher或 public replacement，因它們依賴 seal descriptor的 closed schema；禁止再次出現「先修 staging、再現場撞 apply」的順序錯誤。

## TDD execution contract

每個有邏輯改動的 slice 固定：

`RED（public behavior） → GREEN（minimum sufficient） → affected verification → optional refactor while green`

- 測試只對 plan/apply/load/publisher/public loader public interfaces，不鎖 helper name。
- 每個 RED 先保存 before bytes/counters，再證明 failure 後完全相同。
- 不得先一次寫完所有 tests或一次寫完所有 production layers。
- checkpoint若出現第二個未預期 source seam，立即停止，不開下一 slice。

## Implementation invariants

1. `terminal_owner.kind` 是 closed enum，不接受未知值或由 filesystem猜值。
2. 同一 seal只能有一種 owner-specific field set；混合 field set fail closed。
3. continuation branch輸入、行為、receipt與rollback語意不得放寬。
4. replacement branch只能用 queue registry現有 lineage與attempts tree，不建立另一 lifecycle artifact。
5. public replacement只能由 staged seal授權；普通 approved translation仍 create-only。
6. public bytes只接受exact old或exact approved after；transaction控制狀態只接受closed state table明列的intermediate state，任何其他組合fail closed。
7. manifest/URL/registry order不變；不靠 append precedence。
8. remote push前一定已有durable PREPARED；ledger append只能在remote main/tag都驗為target commit後。
9. PREPARED前的local failure由MutationJournal/Git owner回退；remote refs一旦可能已變，禁止remote rollback，只能exact reconcile或fail closed。
10. PREPARED不是candidate/published authority；必須與stage、reviewer、commit/tag、remote refs、ledger交叉驗證。

## Stop conditions

任一命中立即 `BLOCKED_SCOPE_EXPANSION`：

- 需要修改第三個 production source file。
- 需要修改 `app/web/static/article-locales.js`、現有 locale content module或 public loader來建立 precedence。
- 需要新增 registry、DB、FSM、ledger、canonical writer、overlay module或第二套 publisher。
- 無法在 mutation前唯一定位 exact old record/module。
- module無法在保留其他record bytes/order下安全重建。
- 需要支援 replacement-02、任意 attempts數、跨多 article/module migration。
- shared continuation guard必須放寬才能讓 attempt branch通過。
- 發現 transaction/rollback owner不再是既有 MutationJournal + ledger + Git。
- durable PREPARED/reconciliation無法由既有 `agy_content_publisher.py` state/evidence/unresolved-push family承載。
- 需要新transaction ledger/FSM才能區分push windows。
- 無法以sealed after bytes + exact commit/tag + exact lineage唯一reconcile post-push state。
- 必須把unknown remote outcome視為成功，或需要force/delete/rollback remote ref。
- 相同 blocker第三次重現。

## Why not less

- 只把 continuation fields改 optional會失去 terminal owner authority。
- 複製 attempts成generations、手建 continuation或補 fake hard_failure是在偽造 lifecycle。
- 只修 stage仍會在 `translation already exists`撞第二 blocker，不能形成 acceptance。
- append replacement module不會取代 first-match record，且會造成雙 owner。
- 只依 `(article, locale)` first match更新，不能排除 duplicate/overlay歧義。
- 忽略push成功→ledger/evidence缺失窗口，會讓public已更新但內部仍未發布成為無法安全重跑的正式狀態。
- 只靠process-memory MutationJournal無法撤回或證明已成功的remote mutation。

## Why not more

- exact selector、Formal Reviewer、stage receipt族、existing unresolved-push/state/evidence family、MutationJournal、release、ledger、Git tag/push與public loader都可沿用。
- 不需要通用 lifecycle framework、歷史 locale migration、content module全面正規化或四線重跑。
- 本案只處理一個已量測的 replacement/attempt + existing locale transaction。

## Do not absorb

- 任意 lifecycle plugin/adapter registry。
- replacement chain beyond `-replacement-01`。
- 自動掃描並猜測old owner/module。
- 全站 locale dedup/migration。
- overlay/precedence layer。
- 新 transaction ledger/log subsystem、event store、DB或state machine；PREPARED只能是既有publisher transaction evidence。
- provider retry、Reviewer policy、queue/coordinator/promotion/activation改動。
- 為通過fixture而特判 `ASTRO-BASE-03`、`en`或特定檔名。

## Product fit

- operating mode：維持 Personal Autonomous Development。
- product level/capability vector：不變。
- measured gap：RCA已用 provider=0 production-shaped RED證明 stage missing seam與apply collision；獨立review再由現行 `push → ledger → evidence` 順序證明post-push durable recovery缺口。
- minimum sufficient：兩個既有 source owners內的一個 transaction closure。
- rollback/reconciliation：PREPARED前使用stage rollback + publisher MutationJournal + local Git owner；remote refs變更後絕不聲稱可rollback，只依closed receipt補exact missing edge或finalize既有ledger/evidence。任何drift fail closed。
- product-fit form：`not-applicable`，理由是 bounded bug fix，不新增 subsystem/runtime/governance/memory/multi-agent/always-on workflow。

## Verification commands（implementation 後）

Worker必須使用 repo的 `uv + .venv`；不得用系統 Python。精確 test node names由RED提交後列入 RESULT，最低要求：

```bash
.venv/bin/python -m py_compile scripts/agy_multilingual_pipeline.py scripts/agy_content_publisher.py
.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py -q
.venv/bin/python -m pytest tests/test_agy_content_publisher.py -q
git diff --check
```

另以 `git diff --numstat` 驗 LOC ceiling、`git diff --name-only`驗 allowlist、`rg`驗未新增 registry/FSM/DB/ledger/overlay module。

## Checkpoint receipts

每個 checkpoint 的 RESULT 至少包含：

- source HEAD/parent與cleanliness。
- changed-files allowlist與新增淨 LOC。
- RED test名稱、精確錯誤與before==after摘要。
- GREEN targeted/full suite結果。
- provider/publisher/production mutation counters。
- lifecycle owner descriptor與old/new public record/module digests。
- PREPARED receipt digest、target commit/tag、expected/observed remote refs與closed state classification。
- rollback/reconciliation、missing-edge convergence與second-execute結果。
- `git diff --check`。

## 最終 acceptance boundary

本 Repair 的 code acceptance 只到：所有 fixtures與affected suites GREEN、independent Reviewer GO、commit可重現。不得在Repair卡內直接 promotion或 production publish。

後續 production acceptance 必須使用新的 accepted SHA重新 promotion，再以 exact EN replacement run走 fresh Rule24/25 → stage plan雙跑一致 → stage execute/load → publisher dry-run/state classification → explicit production authorization → publisher execute → local commit/tag → durable PREPARED → exact remote convergence → ledger/evidence finalize → unchanged public URL HTTP 200且 replacement正文可見。任一 drift立即停止，不回頭擴大本 Repair。
