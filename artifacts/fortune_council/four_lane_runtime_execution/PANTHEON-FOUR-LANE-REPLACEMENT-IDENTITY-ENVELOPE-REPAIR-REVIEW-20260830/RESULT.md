# Pantheon 四線 Replacement Identity Envelope Repair 獨立文件審查

## Scoped re-review 狀態

`REREVIEW_COMPLETE`

本次只重驗原兩個 P1、routing schema單一owner、allowlist／LOC、負向矩陣與 protected boundaries。未修改 source、tests、production；未執行 provider、publisher、promotion、service、commit、tag、push或network。

## Findings

未發現阻塞問題。

## 原 P1 closure

### P1-1｜Derived canonical authority provenance

`CLOSED`

修訂後 FR-RIE-003 不再接受 operator-supplied artifact path作authority。Operator只提供 exact identities與 optimistic-lock digests；所有 mutation-driving paths均由既有 durable roots與identity確定性導出：

- target/source registry：既有 `_state_path(run_id, queue_root)`。
- target/source run：canonical `queue_root/translation-runs/<run_id>`。
- briefs、attempts 01..03、root mirrors：只能位於各 exact run tree固定相對位置。
- provider request：由 canonical attempt operation receipt的exact job identity與validated lane導出既有 lane archive path。
- publisher ledger：由現行 runtime manifest／正式 publisher state root導出。
- reconciliation receipt：既有 `translation-replacement-decisions/` family內，以target run opaque hash確定唯一位置。

每個root、ancestry與leaf皆要求canonical realpath、root containment、非symlink ancestry與預期file type。Supplied digest只作lock，不能提升錯root副本為owner。NEG-RIE-002已加入wrong-root correct-bytes、cross-run同bytes、operator path不等於derived path與root-mirror-only負向case；因此任意自洽副本無法驅動registry mutation。

Expected envelope只能由canonical source/target registry、brief、routing tuple與archived request lineage交集，交由既有builder確定性產生；attempts與root mirrors只證明closed execution/cross-check，不成為第二identity authority。

### P1-2｜Formal review／stage seal authority separation

`CLOSED`

卡片已校正current artifact inventory與authority boundary：

- isolated formal review result存在，但本Repair不得讀取；它不參與identity derivation、eligibility或plan digest。
- lifecycle-neutral approved revision stage seal／`editorial-staging/current.json`目前不存在；本Repair不得建立、模擬或宣稱它存在。
- stage seal只能在reconciliation後由既有54ad正式stage CLI另行驗證／產生。

NEG-RIE-002已要求isolated formal review presence／absence／bytes drift不得改變identity plan，並拒絕fake/copied stage seal。這不再混淆candidate approval與registry lifecycle identity。

## Coherent invariant 判定

`PASS_SINGLE_IDENTITY_INVARIANT`

Future producer與current reconciliation不是兩套authority：

1. future exact CLI與automatic seeder都只經共同 `enqueue_translation_replacement()`；routing tuple與envelope在replacement state第一次atomic write同時存在。
2. current事故target只在同一canonical identity chain、同一builder、同一validator下補回唯一缺欄位；receipt僅是crash-control evidence，不是identity authority。
3. existing-state missing／invalid envelope仍在future producer fail closed，沒有偷做generic backfill。
4. current reconciliation只接受exact `complete + unpublished + replacement-01 + live run tree + envelope missing` shape；四筆failed missing-run tombstones、其他run、normal run、已publish或invalid/drift envelope全部排除。

這是一個producer invariant及其唯一measured pre-invariant事故收斂，不是producer fix外加任意migration。

## Routing schema owner

`PASS_SINGLE_OWNER`

卡片明定：

- canonical schema value維持現行 `ROUTING_SCHEMA_VERSION`，不得在兩source複製literal。
- 若import方向需要調整，只能將symbol機械搬到 `scripts/agy_multilingual_pipeline.py`，並刪除coordinator原literal definition。
- coordinator直接引用唯一shared symbol，不得alias/fallback literal。
- lane/mode tuple仍由coordinator既有resolver／validator驗證；共同enqueue只接收並exact核對已驗證tuple。
- `translation_identity_envelope()`維持唯一builder與既有digest schema。

因此仍是一個constant owner、一個既有validator、一個既有builder；若實作無法在兩個既有source內維持，卡片要求立即 `BLOCKED_SCOPE_EXPANSION`。

## Receipt-first／idempotency

`PASS_CLOSED_TWO_STATE_RECOVERY`

- Receipt使用derived target-run opaque path、exclusive create；不得覆寫既有source-run decision receipt。
- 新receipt先durable atomic write，再對exact target registry只新增envelope。
- Crash後只允許receipt + exact-before完成write，或receipt + exact-after回`already_reconciled`。
- Receipt缺失但registry已變、partial/collision/different plan digest、registry第三態全部fail closed。
- 成功receipt不清除、不累加；第二跑receipt與registry bytes不變。

## Mutation與lifecycle boundary

`PASS`

Execute唯一允許差異：

1. 一張existing-family reconciliation receipt。
2. exact target registry新增canonical `identity_envelope`。

以下維持不變：status、result、`approved_by_reviewer`、last job、routing tuple、replacement lineage、updated_at、queue、attempts、candidate/review、content、ledger、manifest、services與promotion state。Provider、Writer、Reviewer、Publisher、scheduler與network calls均為0；不建立replacement-02、Gen04、新run或新candidate。

Promotion guard／snapshot／manifest schema不修改；修後fresh promotion plan僅作既有consumer acceptance。

## Allowlist／LOC／negative matrix

`PASS_BOUNDED`

- Production source exactly 2：`scripts/agy_multilingual_pipeline.py`、`scripts/agy_gemini_coordinator.py`。
- Tests exactly 1：`tests/test_agy_gemini_coordinator.py`。
- Source ceilings維持`+80/-20`與`+220/-30`；tests維持`+480/-30`。
- 第三source、第二test file、新helper module或超LOC直接`BLOCKED_SCOPE_EXPANSION`。
- Positive matrix覆蓋direct producer、exact CLI、automatic seeder、production-shaped reconciliation與未修改promotion planner RED→GREEN。
- Negative matrix覆蓋future identity/routing/source/lineage drift、四failed tombstones、wrong lifecycle、publish-started、attempt/root drift、wrong-root副本、cross-run bytes、symlink／ancestry、receipt collision／第三態、formal-review independence與fake stage seal。

## Why not less／more

- 只修future producer無法解開唯一current事故target；只補current target會讓兩個正式producer入口繼續重現缺口。
- 重新enqueue／replacement-02會破壞一次性lineage與既存semantic audit；手改JSON沒有receipt/idempotency contract。
- 不需新registry、ledger、FSM、DB、identity schema、canonical writer、approval authority、promotion/publisher/stage修改或四線重跑。

## Remaining implementation risks

- 兩個source LOC ceiling偏緊；實作者必須復用現有closed readers、path primitives與locks，不得以省LOC省略root containment或negative closure。
- `ROUTING_SCHEMA_VERSION` symbol搬位必須是機械ownership relocation；若造成import cycle、第二literal或validator分叉，應停線而不是擴檔。
- Evidence RESULT必須實測exclusive receipt collision、crash兩態與wrong-root correct-bytes副本；文件GO不等於code acceptance或production授權。

## Spec axis

`PASS`。原P1均已原地閉合；current reconciliation與future producer共享同一identity derivation contract，沒有引入approval或promotion authority。

## Standards axis

`PASS_WITH_IMPLEMENTATION_VERIFICATION_REQUIRED`。Authority provenance、crash recovery、mutation allowlist、rollback、negative matrix與防膨脹stop conditions已可執行且可驗證。

## Verdict

`GO_BOUNDED_REPAIR`

允許依卡片進入implementation，但不授權commit、push、production、promotion、service activation或publish。實作若需要第三source／test、任意path authority、formal-review/stage-seal依賴、routing第二owner或target其他欄位mutation，立即回`BLOCKED_SCOPE_EXPANSION`。
