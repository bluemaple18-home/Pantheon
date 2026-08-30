# Pantheon 四線：Replacement Identity Envelope Repair

## 工作名稱 → 正在做什麼 → 現在狀態

`Replacement Identity Envelope Repair` → 讓 future replacement 在唯一共同建立點原子寫入既有 durable identity contract，並為唯一事故 run 提供 receipt-first、exact-run reconciliation → `READY_FOR_REREVIEW / IMPLEMENTATION_NOT_STARTED`。

## 唯一裁決

`GO_SINGLE_REGISTRATION_RECONCILIATION_SEAM`

本卡只修一個已量測缺口：`enqueue_translation_replacement()` 建立 replacement registry entry 時省略 `routing_schema_version / mode / lane / identity_envelope`，使正式 exact CLI 與 automatic seeder 都能建立無法被 fresh promotion 保存的 complete-unpublished run。

Repair 必須是一個 coherent seam，而非兩個獨立補丁：

1. future replacement 的 immutable identity 在共同 producer 建立時就存在；
2. 唯一既存事故 entry 只在 closed production shape 與所有 durable evidence 完全一致時，以同一 identity builder 補齊；
3. promotion guard 保持不動，fresh promotion 只負責驗證修後結果，不負責發明 identity。

若 discovery 顯示需要第三個 production source、第二個 identity builder、generic registry migration、publisher／promotion改動或 production JSON 手改，立即回 `BLOCKED_SCOPE_EXPANSION`，不得逐層補洞。

## Spec authority 與 measured gap

唯一 RCA authority：

- `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-REPLACEMENT-PROMOTION-IDENTITY-LIFECYCLE-RCA-20260830/RESULT.md`

RCA 唯一主裁決：

`REPLACEMENT_IDENTITY_ENVELOPE_PRODUCER_OMISSION`

Exact target：

- run：`auto-i18n-en-aa637e1bf05d3ad21429-replacement-01`
- registry：production runtime `queue/runs/1bf0bbc61ff8d10e808f6923.json`
- shape：`status=complete`、`mode=translate_existing`、`lane=i18n-rewrite`、`replacement_of=auto-i18n-en-aa637e1bf05d3ad21429`、`replacement_reason=LOCALE_PLAN_VALIDATION`
- `result.status=complete`、`result.approved_by_reviewer=0`
- run directory、attempts 01..03、root candidate/review mirrors與 isolated formal review result存在
- publisher ledger與publish transaction不存在
- lifecycle-neutral approved revision stage seal不存在；`editorial-staging/current.json`尚未由正式 stage CLI建立
- `identity_envelope` 唯一缺失

Current registry 另有四筆 missing-envelope failed tombstones；它們沒有 live run directory，屬既有 terminal receipt contract，不是本 Repair population，禁止遷移。

### Current artifact inventory

| Artifact | Current existence | 本 Repair角色 |
|---|---|---|
| exact target/source registry與translation run roots | 存在 | canonical identity/lifecycle owners |
| source/target briefs | 存在 | run/article/locale/source lineage owners |
| canonical lane archived requests與attempt operation receipts | 存在 | request/prompt/schema/result lineage cross-owners |
| target attempts 01..03 | 存在 | replacement execution lifecycle owner |
| root candidate/review mirrors | 存在 | terminal attempt audit副本，只cross-check |
| isolated formal re-review RESULT／formal-review-result | 存在 | 本 Repair不讀取；只供後續stage重新驗證 |
| lifecycle-neutral approved revision stage seal／`editorial-staging/current.json` | **不存在** | 不得偽造；後續由既有54ad正式stage CLI產生 |
| publisher ledger target record／publish transaction／public receipt | **不存在** | 必須維持不存在，證明尚未publish |
| identity envelope | **不存在** | execute唯一registry補欄位 |

## CodeGraph／限域 source discovery

本卡未進 implementation。既有 source topology 已由 RCA 與限域查詢閉合：

- `scripts/agy_multilingual_pipeline.py::translation_identity_envelope`
- `scripts/agy_multilingual_pipeline.py::enqueue_article_translations`
- `scripts/agy_multilingual_pipeline.py::enqueue_translation_replacement`
- `scripts/agy_gemini_coordinator.py::replace_failed_translation_run_exact`
- `scripts/agy_gemini_coordinator.py::seed_failed_translation_replacements`
- `scripts/agy_gemini_coordinator.py` 現有 subcommand parser／exact-run locks／closed JSON readers
- `scripts/pantheon_content_runtime_promotion.py::_queue_identity_snapshot` 僅為不修改的 acceptance consumer

共同 call chain 已固定：

```text
exact replacement CLI ─┐
                       ├─ enqueue_translation_replacement
automatic seeder ──────┘        └─ registry state producer
```

因此 A 只能修共同 enqueue；不得分別在 exact CLI 與 seeder 複製 envelope 寫入。B 可使用 coordinator 現有 CLI 檔、exact selector與 lock primitives，但不得新增第三支 migration script或 production module。

## User story

### US-RIE-001｜Durable replacement identity

作為 production operator，我要所有正式 replacement 從建立起就帶有與 normal translation 相同 schema／validator 的 immutable identity，且唯一既存事故 run 能在精確、可回溯、零外部呼叫的 reconciliation 後通過原 promotion guard，而不重跑內容、不改 lifecycle、不遷移其他 registry entries。

## Durable authority contract

### Registry identity

future replacement state 必須在第一次 atomic write 同時包含：

- `routing_schema_version`：復用 normal translation 現行唯一 routing schema constant／contract；不得另定版本。
- `mode=translate_existing`。
- `lane`：只能由已驗證 terminal source state、normalized replacement brief與現行 lane resolver一致導出，且只能是 `i18n-new` 或 `i18n-rewrite`。
- `identity_envelope`：必須由既有 `translation_identity_envelope(article_id, lane)`／同一 canonical validator schema產生，不得建立 replacement-only envelope schema。
- `replacement_of` 與 `replacement_reason`：維持既有 exact lineage，並與 identity routing同時驗證。

`identity_envelope` 證明 `schema_version / mode / lane / article_ids / digest`；replacement lineage仍由既有 state fields擁有。兩者必須 exact matching，但不得把 lineage塞入新 envelope schema。

### Routing schema 單一 owner

本 Repair 不得在兩個 source各寫一份 `1`，也不得新增 replacement-only routing validator。實作必須將現有 normal translation 的 exact constant保留為單一 import-safe owner：

- canonical value仍是現行 `ROUTING_SCHEMA_VERSION` 契約，schema value不變；若為解除 coordinator ↔ multilingual import方向而需移動symbol，只能機械搬到 `scripts/agy_multilingual_pipeline.py`，並移除 coordinator內的literal definition。
- `scripts/agy_gemini_coordinator.py` 必須直接引用該唯一 shared symbol，不得另設數值alias或fallback literal。
- lane/mode/routing tuple仍由 coordinator既有 routing resolver／validator驗證；共同 enqueue只接收已驗證 source terminal tuple、以同一shared symbol再次exact比對，並負責一次性寫入。
- `translation_identity_envelope()`仍是唯一 envelope builder；不得因routing constant搬位而改schema或digest算法。

若無法在兩個既有source內保持「一個constant definition + 一個既有validator + 一個既有builder」，立即 `BLOCKED_SCOPE_EXPANSION`。

### Evidence ownership

- replacement brief、source terminal state與registry lineage：建立時的 immutable identity authority。
- canonical attempts tree：擁有 exact replacement execution lifecycle；不單獨擁有 registry identity。
- root candidate/review mirrors：只是 terminal attempt 的 audit副本，只能 cross-check，不能單獨驅動 mutation。
- isolated formal review result：目前存在，只證明 repaired candidate可進 staging；不是 stage seal、不是 reconciliation prerequisite、不得參與 expected envelope推導或 eligibility判定。
- lifecycle-neutral approved revision stage seal：目前不存在；只能在 reconciliation完成後由既有 54ad正式 stage CLI另行驗證／產生。本 Repair不得建立、模擬或宣稱它存在。
- publisher ledger：publish後 authority；事故 target 尚未 publish，因此正確缺席。
- promotion：只驗證與保存，不得 reconstruction、backfill或放寬 guard。

## Functional requirements

### FR-RIE-001｜Future producer 原子寫入完整 identity

`enqueue_translation_replacement()` 在建立新 entry 前必須：

1. 驗證 source terminal state、canonical run directory、base brief、current source SHA、closed replacement reason與一次性 lineage。
2. 由已驗證 brief取得唯一 source article ID；多 article、空 article或歧義 shape一律 fail closed，不得挑第一筆。
3. 由 source state的現行 validated routing與brief/source lineage決定 exact lane；不得用 run ID、locale、timestamp或路徑名稱猜 lane。
4. 使用 normal translation 現有唯一 routing schema symbol與 canonical identity builder產生 tuple/envelope；不得在 Repair內另寫數值literal或第二validator。
5. 在 replacement state第一次 atomic write中一起寫入 routing tuple、envelope與既有 lineage。

exact CLI 與 automatic seeder必須不加特例即可同時取得此行為。不得在 callers事後補欄位。

### FR-RIE-002｜Future idempotency 與 drift closure

replacement state已存在時，共同 enqueue必須驗證：

- registry path／run directory／brief均 canonical且非 symlink。
- `run_id / run_dir / replacement_of / replacement_reason`完全相同。
- `routing_schema_version / mode / lane / identity_envelope`完全等於由derived canonical authority chain重新推導的 expected value。
- brief、source SHA與source terminal lineage未漂移。

相同 bytes重跑回同一 identity且不得重寫 state；缺 envelope、錯 lane、錯 digest、不同 source/reason或任何 extra candidate identity皆 fail closed。Future producer的 idempotency不得默默兼任 legacy backfill；事故 reconciliation只能走 FR-RIE-003 的明示入口。

### FR-RIE-003｜唯一事故 target 的 exact plan-only

在 `scripts/agy_gemini_coordinator.py` 現有 CLI source內新增語意專屬 subcommand；不得重用或模糊 `replace-failed-translation-run` 的「建立 replacement」語意。命令須要求：

- exact replacement run ID；
- exact target registry before SHA-256與source registry SHA-256；
- exact source/target brief digests；
- exact archived request與operation receipt digests；
- attempts 01..03 closed-tree digest；
- root candidate／review mirror digests；
- expected source run ID、replacement reason、lane與article ID；
- `--plan-only` 或 `--execute`，互斥且不得皆缺。

operator只提供 identities與optimistic-lock digests，不能提供任意artifact path作authority。所有path必須由canonical roots、exact run/job identity與既有命名函式確定性導出：

| Artifact | Durable owner／derived canonical path | Mutation authority角色 |
|---|---|---|
| target registry | exact `_state_path(target_run_id, queue_root)` | 唯一被補 envelope 的registry owner |
| source registry | exact `_state_path(replacement_of, queue_root)` | source terminal/routing/lineage cross-owner |
| source run | exact `queue_root/translation-runs/<replacement_of>` | source brief與terminal lifecycle owner |
| target run | exact `queue_root/translation-runs/<target_run_id>` | replacement lifecycle owner |
| source/target brief | 各自canonical run root下固定 `brief.json` | article/locale/source SHA與run lineage owner |
| attempts | target run root下固定 `attempts/01..03`；每個closed artifact依既有固定檔名 | semantic execution lifecycle owner；不單獨產生registry identity |
| provider request | 由attempt operation receipt的exact job ID與validated lane導出 `queue_root/lanes/<lane>/archive/<job_id>.json` | request/prompt/schema/result lineage cross-owner |
| root mirrors | target run root下固定 `candidate.json`／`review.json` | terminal attempt audit副本，只可cross-check |
| publisher ledger | 由現行runtime manifest／正式publisher state root導出的既有canonical ledger path | 只證明尚未publish；不產生identity |
| reconciliation receipt | `queue_root/translation-replacement-decisions/<sha256(target_run_id)[:24]>.json` | receipt-first control evidence，不是identity owner |

每一個root、parent ancestry與leaf都必須經existing closed-path primitive驗證：absolute canonical realpath、root containment、所有ancestry component非symlink、leaf為預期regular file／directory。supplied digest必須等於derived path bytes，只是optimistic lock；digest不能把錯誤root的副本提升為authority。

plan-only 不得 glob／掃描 registry自動挑一筆，也不得依 timestamp找最新 evidence。它必須證明：

1. target precisely 等於 `complete + run_dir exists + ledger absent + envelope missing + replacement lineage present`。
2. source/target registry、brief、canonical lane archive request、attempt operation receipts與attempt artifacts逐層綁定同一 run、source article、locale、request/prompt/schema/result digests。
3. attempts精確為 01..03；不存在 attempt04、generation tree、第二 replacement、第二 candidate identity或queue ambiguity。
4. root candidate/review bytes exact mirror terminal attempt；它們只作cross-check，移除任一canonical owner時，正確bytes副本不得讓plan通過。
5. publisher ledger、public transaction與tombstone均不存在。
6. expected target identity只能由 canonical source registry+source brief、target registry+target brief與canonical archived request lineage的交集導出，再交給既有builder；attempts/root mirrors/digests均不能單獨驅動mutation。
7. isolated formal review result即使存在也不得被讀為本命令input，不得影響plan digest、eligibility或expected envelope；approved revision stage seal目前不存在。

plan-only輸出 canonical JSON，至少包含 before registry digest、expected after digest、expected envelope、receipt path、唯一 expected write set與所有 zero-call counters；plan-only本身零寫入。

### FR-RIE-004｜Receipt-first exact execute

execute 必須先重跑 FR-RIE-003，取得同一 plan digest並在 exact-run lock內再次驗證 authority未變，之後按以下 forward-only順序：

1. 在既有 `translation-replacement-decisions/` evidence family，以 target run opaque hash建立唯一 reconciliation receipt；路徑須證明與source-run keyed既有decision receipt不同。
2. receipt 必須以exclusive create形成；已存在時只能進FR-RIE-005 closed replay，禁止overwrite。新receipt先durable atomic write，記錄 action、exact run/source lineage、derived canonical authority paths、before registry digest、expected envelope、expected after digest、所有 authority artifact digests與plan digest。
3. 僅對 exact registry state atomic加入 `identity_envelope`；既有 routing tuple必須已正確且只驗證，不得順便改寫。
4. 重讀 registry並驗證 after digest與 envelope。

receipt 是 audit/control evidence，不是第二個 identity authority。它不得授權其他 run、不得被 promotion當成 envelope替代品。

### FR-RIE-005｜Crash recovery 與 idempotency

同一 exact execute連跑時只允許下列兩種收斂狀態：

- receipt存在、registry仍為exact before digest：依receipt完成唯一缺失的envelope write。
- receipt存在、registry已為exact expected after digest：回 `already_reconciled`，不再寫任何bytes。

receipt缺失而registry已有 envelope、receipt/registry digest漂移、receipt path collision、partial JSON、不同plan digest或任何第三狀態均 fail closed。不得清除receipt、不得累加第二張成功receipt。

### FR-RIE-006｜只允許唯一事故 population

Reconciliation 必須同時要求：

- exact run ID由operator明示，且run ID為一次性 `-replacement-01` lineage。
- `status=complete`、`result.status=complete`、`approved_by_reviewer=0`。
- replacement run directory存在且所有closed evidence通過。
- `identity_envelope`恰為缺失，不是invalid、partial或drift。
- publisher ledger與publish transaction缺席。

以下全部不可 reconciliation：四筆failed missing-run tombstones、active/failed/reserved state、已publish run、沒有run directory、其他 replacement、normal run、invalid envelope或任一 ambiguity。Isolated formal review存在或不存在均不改變run identity reconciliation判定；stage seal尚不存在也不是blocker，因本卡不得處理candidate approval。

### FR-RIE-007｜Promotion guard與其他 lifecycle不變

不得修改：

- `scripts/pantheon_content_runtime_promotion.py`。
- promotion snapshot／identity validator／manifest schema。
- Writer、Reviewer、provider、stage、publisher、queue runner或service activation。
- registry status、result、approved flag、last job、replacement lineage或routing tuple。

修後 promotion plan GREEN 是 consumer acceptance，不是 source改動理由。

## 為何 B 不能由「正式重新 enqueue」取代

不做 B 並重新 enqueue 並非更小或更安全：

1. target 已是正式 producer建立的唯一 `replacement-01`，且已完成 canonical attempts 01..03與root mirrors；共同 enqueue 的 future idempotency在 missing-envelope既存 state上必須 fail closed，不能默默backfill。
2. source lineage禁止第二層 replacement；重新 enqueue只會命中同一 defective state，或要求刪除／改名既存run，兩者都不是合法 recovery。
3. 刪除 registry/run directory再建立會摧毀terminal audit與semantic budget；建立 `replacement-02`則改變既有一次性lineage contract。
4. isolated formal review雖存在，但它不是run identity authority；重新執行 Writer／Reviewer/provider既浪費已完成semantic work，也仍不能補回producer omission。

因此最小安全 contract 是：future producer fail closed + exact current reconciliation。B 不是 generic migration，也不是「找到資料就補」；它只接受一個有完整封存 authority chain的 measured production shape。

## Exact TDD matrix

### RED-RIE-001｜Future direct producer

以 production-shaped failed translation source呼叫共同 enqueue。修前replacement state缺 `routing_schema_version / mode / lane / identity_envelope`；修後一次建立即完整，且 envelope 等於 normal translation canonical builder輸出。

### RED-RIE-002｜兩個正式入口覆蓋

分別由 public exact replacement CLI與automatic seeder建立 fresh fixture replacement。修前兩者都缺 envelope；修後兩者不加caller patch即可持有相同 schema與validator通過的full identity。

### RED-RIE-003｜Exact current reconciliation

建立 exact production-shaped target fixture：complete replacement、derived canonical source/target registries與run roots、canonical lane archive requests、attempts 01..03、root mirrors、ledger absent、envelope missing；isolated formal review可另存但不得作input，stage seal必須不存在。修前 fresh promotion planner回：

`preserved run identity envelope is missing or invalid`

修後：

1. plan-only zero write並產生single-run plan；
2. execute只新增一張receipt並對exact registry加入envelope；
3. 未修改promotion source的同一planner GREEN；
4. execute第二跑為 `already_reconciled`，receipt與registry bytes不變。

### NEG-RIE-001｜Future producer fail-closed matrix

至少覆蓋：

1. source lane、brief article或source SHA drift。
2. replacement reason／source lineage drift。
3. existing state缺 envelope、invalid digest、wrong lane/mode/routing version。
4. multi-article／empty-article ambiguity。
5. second replacement或brief/state collision。

每個case都須證明before==after且provider/publisher calls=0。

### NEG-RIE-002｜Reconciliation fail-closed matrix

至少覆蓋：

1. wrong exact run ID、registry path/digest或run directory。
2. active、failed、reserved、wrong result或approved flag。
3. failed missing-run tombstone（含盤點的四筆shape）。
4. ledger已存在、publish receipt存在或public transaction已開始。
5. identity envelope已存在但invalid／drift；不得「修正」它。
6. replacement request／queue residue缺失、重複、跨lane或digest不一致。
7. attempt缺號、attempt04、operation receipt drift、candidate/review mismatch。
8. root mirror不同；或只提供correct bytes的root mirror而canonical terminal attempt owner缺失。
9. source article、locale、lane、replacement_of或reason任一drift。
10. reconciliation receipt collision、partial、不同plan digest或registry第三狀態。
11. symlink、non-canonical path、unknown artifact或第二候選identity。
12. canonical regular file但位於錯誤root、correct-bytes副本、跨run同bytes、operator-supplied path不等於derived path。
13. isolated formal review result缺失、存在或bytes改變時，identity plan不得因此改變；若implementation嘗試讀它作authority，測試必須RED。
14. fake／copied `editorial-staging/current.json` 或自稱stage seal的artifact不得被接受；真正stage seal目前不存在。
15. operator未明示任一required identity／digest，或提供derived root以外的path。

所有負向case必須在registry、receipt、queue、run/content bytes mutation前拒絕。

## Protected topology 與 call accounting

### Plan-only protected bytes

所有 surfaces before==after：

- complete target registry state；
- source terminal registry／brief／run tree；
- replacement brief、attempts 01..03、root candidate/review mirrors；
- isolated formal review result與related review evidence（存在但不被reconciliation讀取）；
- `editorial-staging/current.json`／approved revision stage seal absence；
- shared與四條lane的 outbox/processing/inbox/archive/failed；
- publisher ledger、stage/publish transaction、generated locale module與manifest；
- runtime manifest、promotion state、LaunchAgent plist與service topology；
-其餘136筆registry entries與四筆failed tombstones。

### Execute唯一允許差異

只允許：

1. `translation-replacement-decisions/<target-opaque-id>.json` 新增exact reconciliation receipt；
2. exact target registry JSON只新增canonical `identity_envelope`，其餘keys/value不變。

不得改 `status / result / approved_by_reviewer / routing_schema_version / mode / lane / replacement_of / replacement_reason / last_job_id / updated_at`。為保持事故時間線可稽核，reconciliation不得偽裝成generic lifecycle update。

### Zero-call／zero-mutation counters

Plan與execute皆必須實證：

- provider、Writer、Reviewer、Publisher calls = 0。
- scheduler／runner／`cycle_once`／`_advance` calls = 0。
- semantic generation／attempt新增 = 0。
- new replacement／new run／queue job新增 = 0。
- content、manifest、ledger、service、promotion、commit、tag、push、network mutation = 0。

## File allowlist 與 LOC ceiling

### Registration source（唯一 future producer owner）

1. `scripts/agy_multilingual_pipeline.py`

只允許修改 canonical identity derivation、replacement create與existing-state idempotency；source net新增 `<= 80` LOC、刪除 `<= 20` LOC。

### Existing CLI adapter（B 的唯一第二 source）

1. `scripts/agy_gemini_coordinator.py`

只允許在現有 coordinator CLI檔加入exact plan/execute reconciliation、receipt-first狀態機與parser routing；source net新增 `<= 220` LOC、刪除 `<= 30` LOC。

### Tests（exactly one file）

1. `tests/test_agy_gemini_coordinator.py`

此一test file須同時覆蓋共同 enqueue、exact CLI、automatic seeder、production-shaped reconciliation、promotion consumer與negative matrix；test net新增 `<= 480` LOC、刪除 `<= 30` LOC。

### Evidence

1. 本卡。
2. `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-REPLACEMENT-IDENTITY-ENVELOPE-REPAIR-20260830/RESULT.md` 及必要的純文字／JSON test receipts。

不得新增production module、test helper module或binary evidence。Production source changed files必須exactly 2；test files exactly 1。第三個source、第二個test file或LOC超限一律 `BLOCKED_SCOPE_EXPANSION`，不得自行提高上限。

## Why not less / why not more / do not absorb

### why_not_less

- 只修future producer：唯一事故target仍被promotion永久擋住。
- 只修事故target：exact CLI與automatic seeder下一筆仍重現缺口。
- promotion臨時reconstruct：把producer缺口擴成每個consumer各自猜identity，且放寬正確guard。
- 手改JSON：沒有plan、receipt、idempotency或可重現驗證，不是正式seam。
- 只驗digest不驗derived root：可讓canonical correct-bytes副本冒充durable owner，仍不是closed reconciliation。
- 要求isolated formal review：把candidate advisory authority錯升成run identity prerequisite；不會提高identity derivation強度。

### why_not_more

正常 coordinator register與normal translation producer已符合identity invariant；isolated formal review、stage seal、publisher ledger、promotion guard各自authority清楚。本卡只復用derived canonical roots與現有closed readers，不需要新registry、FSM、DB、ledger、canonical writer、中間status、approval migration或四線重跑。

### do_not_absorb

禁止：

- generic registry-wide backfill／migration／startup auto-heal。
- 遷移四筆failed missing-run tombstones。
- 掃描registry、glob residue、依timestamp或最新mtime自動選run/job。
- 新 identity schema／replacement-only builder／第二 authority receipt family。
- 修改或刪除production registry/run artifacts；手工patch JSON。
- 改 status/result/approved flag/routing/queue/content/ledger。
- 呼叫provider、Writer、Reviewer、Publisher或重跑semantic generation。
- 修改promotion guard、publisher transaction、stage seal、routing resolver或service activation。
- 讀取isolated formal review來推導run identity／eligibility，或由本Repair建立approved revision stage seal。
- 接受operator任意path、錯root correct-bytes副本或root mirror作canonical owner替代品。
- 建replacement-02、Gen04、新run或新candidate。
- 為APF/private copied-queue helper擴scope。

## Stable trace matrix

| Requirement | Success criteria | Slice |
|---|---|---|
| US-RIE-001 | SC-RIE-001..006 | SLICE-RIE-FUTURE, SLICE-RIE-CURRENT, SLICE-RIE-SEAL |
| FR-RIE-001 | SC-RIE-001, SC-RIE-002 | SLICE-RIE-FUTURE |
| FR-RIE-002 | SC-RIE-001, SC-RIE-004 | SLICE-RIE-FUTURE |
| FR-RIE-003 | SC-RIE-003, SC-RIE-004, SC-RIE-005 | SLICE-RIE-CURRENT |
| FR-RIE-004 | SC-RIE-003, SC-RIE-004, SC-RIE-005 | SLICE-RIE-CURRENT |
| FR-RIE-005 | SC-RIE-003, SC-RIE-004 | SLICE-RIE-CURRENT |
| FR-RIE-006 | SC-RIE-004, SC-RIE-005 | SLICE-RIE-CURRENT |
| FR-RIE-007 | SC-RIE-003, SC-RIE-006 | SLICE-RIE-SEAL |

Trace preflight：無 dangling reference、重複ID、未解 blocking decision或缺驗證方式。Jira、architecture diagram與data product皆 `not-applicable`：這是既有 producer／CLI的bounded contract repair，不建立新subsystem。

## Success criteria

### SC-RIE-001｜Future producer完整

direct shared enqueue、exact replacement CLI與automatic seeder建立的fresh replacement皆在第一次registry write持有same-schema validated envelope與exact routing/lineage；caller無duplicate backfill。

### SC-RIE-002｜Future negative閉合

existing missing/invalid/drift envelope、routing/source/lineage ambiguity全部在mutation前fail closed；相同valid state重跑bytes不變。

### SC-RIE-003｜Exact current recovery

production-shaped target的plan-only只從derived canonical paths讀取且zero write；execute只新增one exclusive receipt與one envelope；第二跑完全idempotent。未修改promotion source的fresh promotion plan由原RED轉GREEN。

### SC-RIE-004｜Closed population

四筆failed tombstones、其他run、ledger-existing、wrong lifecycle、artifact drift、wrong-root/correct-bytes副本、cross-run同bytes、ambiguity與crash third-state全部RED且protected bytes不變。Isolated formal review有無或bytes變化均不改identity plan；fake stage seal不得被讀取。

### SC-RIE-005｜No external work

provider/Writer/Reviewer/Publisher/scheduler calls、semantic generation、queue job、content/ledger/service/Git/network mutation全部為0。

### SC-RIE-006｜Regression與scope

affected coordinator/multilingual/promotion tests、`py_compile`、`git diff --check`、changed-file allowlist與LOC ceilings全部PASS；promotion guard diff=0。

## Ordered implementation slices

### SLICE-RIE-FUTURE｜Producer invariant vertical path

`traces_to: [US-RIE-001, FR-RIE-001, FR-RIE-002, SC-RIE-001, SC-RIE-002]`

Blocking edges：本卡Reviewer GO；無其他implementation blocker。這是current frontier。

1. RED：在唯一test file鎖direct enqueue、exact CLI與automatic seeder三條fresh path均缺full identity。
2. GREEN：只在共同 enqueue以唯一shared routing constant與既有builder寫routing tuple/envelope，並收緊existing-state exact validation；coordinator不得保留第二個routing literal。
3. Verify：三條path GREEN、normal envelope schema相同、negative matrix RED、zero external calls。

### Checkpoint CP-RIE-001｜Producer ownership seal

獨立檢查：caller不得事後寫envelope、不得新增builder、不得改promotion。若future producer仍有第二個write owner，不得進current reconciliation。

### SLICE-RIE-CURRENT｜Exact receipt-first reconciliation

`traces_to: [US-RIE-001, FR-RIE-003, FR-RIE-004, FR-RIE-005, FR-RIE-006, SC-RIE-003, SC-RIE-004, SC-RIE-005]`

Blocking edges：`CP-RIE-001 PASS`；exact production fixture、derived canonical roots與required artifact digests已固定。

1. RED：production-shaped fixture在promotion planner穩定重現missing-envelope NO-GO；plan-only subcommand尚不存在。
2. GREEN plan：在existing coordinator CLI source加入exact selector與closed evidence recomputation；所有path由authority root導出，operator digests只作lock，零寫入輸出canonical plan。
3. GREEN execute：lock後revalidate，先寫single durable receipt，再只補exact envelope；實作before/after兩態idempotency。
4. Verify：negative matrix全RED；same promotion planner GREEN；所有protected surfaces與zero-call counters成立。

### Checkpoint CP-RIE-002｜Mutation allowlist seal

核對execute byte diff只能是receipt + exact registry envelope。若需要改routing/status、第二張receipt、重建run或讀取未明示scan結果，立即 `BLOCKED_SCOPE_EXPANSION`。

### SLICE-RIE-SEAL｜Affected regression與交付

`traces_to: [US-RIE-001, FR-RIE-007, SC-RIE-006]`

Blocking edges：`CP-RIE-002 PASS`。

不新增功能；重跑affected replacement/coordinator/promotion tests、`py_compile`、`git diff --check`與LOC/allowlist檢查。RESULT須包含RED/GREEN、negative matrix、receipt/registry before-after SHA、protected topology、zero-call/mutation accounting與promotion guard diff=0。

## Verification boundary

實作者至少交付：

- RED-before/GREEN-after的direct enqueue、exact CLI、automatic seeder receipts。
- exact production-shaped promotion RED → reconciliation → same planner GREEN。
- plan-only bytes before==after。
- execute exact two-path idempotency與crash window tests。
- wrong-root correct-bytes／cross-run copy／root-mirror-only provenance tests。
- isolated formal review presence/absence/drift identity-independence與stage-seal-absent test。
-完整NEG-RIE-001/002 matrix。
- affected coordinator、multilingual與promotion test nodes；不得因unrelated full-suite baseline failure修改其他檔案。
- repo-approved `py_compile` 等價命令。
- `git diff --check`、`git diff --numstat`、exact changed-file allowlist。

本卡階段與implementation交付階段均不得執行production、provider、promotion apply、service activation、publish、commit、tag或push。

## Rollback

- Code rollback：revert本Repair的單一accepted commit，即恢復pre-Repair producer／CLI行為；promotion guard不受影響。
- Production reconciliation不可刪除receipt或手改回缺envelope。若execute後需回退，停止後續promotion並以該receipt、before/after digests走獨立incident rollback裁決；不得把已驗證identity當成可隨意清除欄位。
- Repair尚未production execute前，rollback只需移除candidate diff與test/evidence，不碰production。

## Stop conditions

任一成立立即停止並交 `BLOCKED_SCOPE_EXPANSION`：

- 需要第三個production source或第二個test file。
- 需要新registry／ledger／FSM／DB／identity schema／authority owner。
- 需要修改promotion、publisher、stage、routing resolver或service code。
- 需要掃描選run、猜identity、遷移tombstones或generic auto-heal。
- 需要改target除identity envelope外任一registry欄位。
- 需要刪除／重建run、重跑provider/Writer/Reviewer、建立new generation/replacement。
- receipt-first兩態無法在既有coordinator seam內完成。
- 同一blocker連續三次仍失敗。

## Reviewer gate 與交付格式

本卡現在只可進independent design review。Reviewer必須回答：

1. future producer與current reconciliation是否確為同一identity invariant，而非兩套authority；
2. 每個input是否由canonical authority root確定性導出，副本是否只能cross-check；
3. isolated formal review是否完全退出identity/eligibility，stage seal absence與後續54ad boundary是否清楚；
4. routing schema是否只有一個constant owner／一個validator／一個builder；
5. B 是否只接受唯一measured production shape，四筆failed tombstones是否確實排除；
6. receipt-first crash/idempotency matrix是否closed；
7. two-source/one-test allowlist與LOC ceiling是否足夠且無第三seam；
8. promotion guard、status、approval、queue、content與provider boundaries是否保持不動。

Reviewer verdict只可為：

- `GO_BOUNDED_REPAIR`，或
- `NO_GO_SCOPE_OR_CONTRACT_GAP`。

Reviewer GO前不得implementation。Repair RESULT只可收斂為：

- `READY_FOR_INDEPENDENT_CODE_REVIEW`，或
- `BLOCKED_SCOPE_EXPANSION`。

本卡未授權commit、push、production、promotion、service activation或publish。
