# Pantheon Acceptance B：gen05 outline topology authority RCA 結果

## 最終主裁決

`TOPOLOGY_GUARD_OVERREACH`

Scoped re-review 更正原 RESULT：原先把 same-generation lifecycle replay 升為唯一主因，沒有先裁清內容 authority，定性不完整。Exact gen05 bytes 證明：

- gen05 persisted external plan 是 gen05 正式 provider call 依 **gen05 current source-ref map** 產生，不是從 gen04 或舊 generation allocation 攜回。
- gen03 與 gen05 的 normalized H2 wording/order 相同，但 authoritative fact/source-ref-to-H2 item mapping 不同。
- provider-time structured contract 把 topology 明定為依 source_ref 排序的 `planned_h2_slot` sequence；gen03 mapping 同時被標成 `INVALIDATED`，prior headings 只以 `non_authoritative_hints` 進入 prompt。
- guard 的 OR predicate 單靠 normalized heading equality 即拒絕，即使 authoritative item topology equality=false。它把 non-authoritative prior outline hints 升成獨立 topology veto，超過 structured authority contract。

`STALE_GEN05_PLAN_REUSED` 不成立；`OUTLINE_REBUILD_CONTRACT_GAP` 不是主裁決。Provider prompt 的自然語言確實另寫「禁止沿用 prior heading order」，但 schema 沒有 prior-heading inequality，structured topology contract又把 minimum change 定義為 meaningful item 的 `planned_h2_slot` 變更，且 prior headings 明列為 non-authoritative hints。這是文字政策與 structured authority 不一致的 contract clarity risk；實際拒絕點仍是 guard overreach。

## 啟動與限制

- cwd：`<repo-root>`
- HEAD：`6766fff999de7af09efc227230e69efd25795108`
- worktree：registered detached worktree；CodeGraph `ready`，indexed HEAD 相符。
- 本輪只讀 production artifacts、accepted actor source/tests/history，並在 task-owned tmp 跑 provider=0 harness。
- 未呼叫 provider、未建立 gen06、未改 production/source/tests、未建立新卡或 Repair。

## Formation chain：gen05 persisted plan 如何形成

1. `continuation/state.json` 在 gen04 terminalization後為 `next_generation=5`、`abandoned=[4]`、`semantic_budget=1`。
2. `generations/05/source-ref-map.json` mtime：`2026-08-27T20:13:27.810488+08:00`。artifact 自帶 `generation=5`、`schema_version=1`。
3. map 的 22 個 fact IDs 逐項、順序均等於當時/current `_source_fact_package(brief)`；refs 是 `source_ref_01` 至 `source_ref_22`。
4. 正式 planning provider call 在 `2026-08-27T20:13:32+08:00` 開始並完成，model=`gemini-3.5-flash-lite`、role=`writer`、transport=`_outbox_transport`、status=`success`、fresh headless process=true。
5. receipt：prompt SHA-256 `906a41e84195373b7816ba8b6968a932e1133b2e557772c340a5a42194ff0cba`；schema SHA-256 `b2d821ad016108bb11b91dba5eefacbc1fd12bd3450603a87f2910eb33c83bf3`。
6. 用 provider-time actor commit `e3a2bbd188a0d25f15a02cde1b2b6820df5dd583` 與 exact brief/prior/history/map 重建 prompt/schema，兩個 digest 都與 receipt 精確相同，證明 formation source。
7. `external-plan.json` mtime：`2026-08-27T20:13:32.321146+08:00`；它的 22 個 source_ref 逐項、順序完全等於步驟 2 的 gen05 map。artifact SHA-256 `bf883da733a66e4b411a466d93e2d52717846c920c0bfdae8ed9ecb72ecabb9c`。
8. 本輪 provider=0 只重新讀取、hydrate、validate 這份 persisted artifact；不是本輪新產物。
9. 後續 safety authority commit `18c6f563f50bd7ae35d53728fca78e3343d6aeac` 以 success receipt 驗證 legacy provider-safety schema，再由本機 current facts canonicalize safety。這不改 source_ref assignment。

因此 gen05 external plan 是 **current gen05 allocation 的正式產物**。後續 retry 的確重讀同一 bytes，但那是 secondary lifecycle replay，不是 `STALE_GEN05_PLAN_REUSED` 所指的舊 generation authority 污染。

## Prior baseline 與 exact guard

Prior owner 是 `continue_writer_reviewer()` → `_last_locale_plan([attempts, generations], before_generation=5)`：

- 精確 baseline：`<run>/attempts/03/locale-plan.json`
- generation=3、schema_version=1
- SHA-256 `c7c0eb857d3b87e3aa254aa1af07552205859a5f61e889ee42c4f56501771810`
- gen04 無 `locale-plan.json` 且 committed=false，不是 prior。
- gen05 因 `before_generation=5` 且無 `locale-plan.json`，不可能把自己當 prior。

Exact guard：

```text
rebuild_outline
AND prior exists
AND (
  normalized_outline(rebuilt) == normalized_outline(prior)
  OR (
    outline_topology(rebuilt) is non-empty
    AND outline_topology(rebuilt) == outline_topology(prior)
  )
)
```

本次 sub-predicate：

- pipeline rebuild authority=true
- normalized H2 equality=true
- fact/source-to-section topology equality=false
- overall OR=true，因此 error 是 `locale plan rebuild reused prior outline topology for article-01`

normalized H2 canonical digest：prior/current 都是 `5c4330d5d0aa04034c18b356cef359ee744249bfd2bbf7880314b25b5e4a26d3`。

Authoritative item topology digest：

- prior gen03：`ed536081443ad9b51237cce9c8f4d6dff93533f124f20a0926e255dfd98f2b0b`
- current gen05：`6cee3544f340cb4c5d62077d04bf375b2d6b42f3f8dd14693de6f133515c2a11`
- equality=false

## Authoritative vs non-authoritative mapping table

| 欄位／關係 | Authority owner | 如何進入 gen05 | Prior vs gen05 | 裁決 |
|---|---|---|---|---|
| current fact identity | local `_source_fact_package(brief)` | gen05 map 建立前由 current brief deterministic projection | 15 prior IDs stale、15 current IDs new、僅 7 shared | authoritative current identity，非 stale |
| `source_ref → source_fact_id` | local `source-ref-map.json` | gen05 20:13:27 建立，generation=5 | map 22 IDs == current package 22 IDs | authoritative current mapping |
| external `source_ref` coverage/order | provider proposal + schema；local map resolves identity | 20:13:32 provider output | refs 01..22 逐項等於 gen05 map | current gen05 allocation |
| fact/source-ref → `planned_h2_slot` | provider proposal；structured rebuild contract；local canonicalization/validation | external coverage mapping hydrate 成 current fact IDs | topology digest不同；7 shared IDs 中 2 個換 slot，另有15 new/15 stale | authoritative item mapping 已重建 |
| `safety_boundary` | current local fact authority（18c6後） | legacy receipt授權讀取舊欄位，本機覆寫為 current safety | 不以 provider bytes為 authority | 不影響 topology 裁決 |
| prior `ordered_h2_outline` | gen03 committed editorial artifact；cross-version prompt view降為 hint | `legacy_authority.non_authoritative_hints.sections` | wording/order 相同 | non-authoritative prior hint，不足以單獨證明 item topology reuse |
| gen05 `ordered_h2_outline` | provider proposed editorial wording；只有 plan commit後才成 article section authority | external plan 直接輸出 | 4 headings wording/order與 gen03相同 | outline-only equality；不是 authoritative item-mapping equality |
| section count | schema（exactly 4） | provider schema | prior=4、gen05=4 | schema shape，相同不代表 mapping reuse |
| source structure | local brief；prompt negative constraint | source has 5 H2，planned has 4 H2 | 無任何 source heading wording 被重用 | source structure未複製 |
| `article_angle` | provider editorial proposal；prior只是 hint | external plan | 相同 | non-authoritative comparison signal |
| search intent / query phrasings | provider editorial proposal | external plan | 兩者皆不同 | 非 topology authority |
| planning commit | local pipeline | 需通過 hydrate/validate 後寫 `locale-plan.json` | gen05 不存在 | external plan尚未 promotion |

Shared 7 個 fact 的 slot comparison：

| fact_id | gen03 | gen05 | changed |
|---|---:|---:|---:|
| `fact-4415396b13a0` | h2-1 | h2-2 | yes |
| `fact-4464fd5767ce` | h2-2 | h2-2 | no |
| `fact-6fc8c0a85cc1` | h2-3 | h2-3 | no |
| `fact-ad6419346192` | h2-3 | h2-3 | no |
| `fact-cefbe5b21d98` | h2-3 | h2-3 | no |
| `fact-ed7ec3e401ba` | h2-3 | h2-4 | yes |
| `fact-f729514cc45f` | h2-4 | h2-4 | no |

連同 15 個 current-only IDs，這已滿足 structured contract 的「至少一個有意義 fact 的 planned_h2_slot 必須與 prior plan 不同」。

## Exact contract／prompt／schema authority analysis

Provider-time prompt 同時存在兩組訊號：

1. prose：`rebuild_outline ... 為 true 時，禁止沿用 prior plan 的 heading order、section topology 或同義詞替換版。`
2. structured rebuild contract：
   - `topology_definition` = 依 source_ref 順序排列的 `coverage_mapping.planned_h2_slot` 序列。
   - `minimum_change` = 至少一個有意義 fact 的 planned_h2_slot 必須與 prior 不同。
   - `insufficient_changes` = 只換 H2／同義詞、只改標題順序文字、只改 coverage_note。
3. provider-time legacy authority：`legacy_mapping_status=INVALIDATED`，15 stale／15 missing，`stable_source_provenance=false`。
4. structured constraints：`prior_ref_to_h2_slot=[]`、`forbidden_prior_topology_signature=[]`。
5. prior headings/angle 只放在名為 `non_authoritative_hints` 的 payload。
6. provider schema要求四個 H2 strings，但沒有 prior heading digest、forbidden heading enum、或 cross-field inequality。

因此 section headings 沒有被 structured contract/schema 明定為 authoritative **topology identity**。Prose 要求 heading change是額外 editorial policy，但它與同一 prompt 的 authority labels／topology definition衝突。Guard 不能把這段 prose 直接升格為 `reused prior outline topology` 的充分條件，而忽略 authoritative item mapping 已變更。

若 Owner 仍要「H2 wording/order 也必須變」作為獨立 product requirement，應另立可驗證的 outline wording authority與獨立 failure code；不能借用 topology equality 取代 authority contract。

## 三選一排除

### `STALE_GEN05_PLAN_REUSED`：排除

map 先於 provider output約 4.5 秒建立；兩者 generation=5 identity與 22 refs逐項相符。provider-time prompt/schema digest亦由 e3a2 exact source重建匹配。沒有 gen04/舊 allocation bytes進入 gen05 source_ref mapping。

### `OUTLINE_REBUILD_CONTRACT_GAP`：非主裁決

存在 prose/structured contract 不一致，屬 clarity gap；但 authoritative mapping contract已有明確 topology definition，而 gen05 已符合。實際 fail由 guard 額外的 normalized heading branch單獨觸發，因此主因是 guard overreach。

### `TOPOLOGY_GUARD_OVERREACH`：成立

控制變數 `rebuild_outline=false` 時 exact gen05 artifact可 hydrate；rebuild=true 時唯一 true sub-predicate是 normalized H2 equality。Authoritative topology digest不同、current map完整，卻被當成 reused topology拒絕，直接證明 overreach。

## Secondary lifecycle factor（不得取代主裁決）

Post-hydration deterministic failure catch只寫 `planning-result.json` 後 raise，未建立 terminal decision；因此 persisted gen05 artifact會 provider=0同 generation replay。這是 secondary lifecycle gap：它解釋錯誤為何重複，**不證明內容 plan 違反 authoritative topology**。

對本 exact case，先修 lifecycle並 terminalize gen05會把一份 authoritative mapping已更新、只被 overreaching guard拒絕的 plan標成 abandoned，會固化錯誤裁決。因此 lifecycle repair不能取代 authority repair。

## 最小 Repair frontier（不實作）

1. 將 `validate_locale_plan()` 的 rebuild topology判定對齊 structured authority：`reused prior outline topology` 只由 authoritative item mapping equality觸發；不得由 normalized heading equality單獨觸發。
2. 保留 heading normalization作為可觀測 comparison，但若產品要求 H2 wording/order必須與 prior不同，另建明確、獨立的 outline wording contract／failure code，並在 provider-facing structured payload提供 prior heading digest或 exact forbidden headings；不要稱為 item topology。
3. 加 exact gen05 fixture regression：current gen05 map + changed fact-to-slot allocation + equal H2 wording 應通過 topology guard；相同 item allocation即使換同義 H2仍應 RED。
4. Secondary lifecycle gap若另修，須用真正 mapping-invalid fixture驗證 once-only terminalization；不得以本 exact gen05 plan當 invalid fixture。

why_not_less：只改 error wording仍會錯拒；只修 lifecycle會錯誤 abandon；只改 prompt不能解決 persisted exact bytes被 guard錯判。

why_not_more：不需改 source-ref map、fact extractor、safety authority、model route、provider transport、semantic budget、queue、gen04 lifecycle或 production artifacts。

do_not_absorb：不做 provider retry、gen06、同 generation改字規避、刪 gen05、replacement queue、FSM/database、Reviewer/Promotion/G8、deploy/publish。

## Provider=0 RED 與 production bytes保護

Evidence：

- `<task-tmp>/pantheon-b-gen05-outline-topology-rca-20260827/exact_gen05_red.py`
- `<task-tmp>/pantheon-b-gen05-outline-topology-rca-20260827/red-result.json`
- `<task-tmp>/pantheon-b-gen05-outline-topology-rca-20260827/authority_audit.py`
- `<task-tmp>/pantheon-b-gen05-outline-topology-rca-20260827/authority-result.json`

Re-review後再次實跑 exact RED：

- error 兩次相同：`deterministic locale plan failure: locale plan rebuild reused prior outline topology for article-01`
- planning/article/reviewer/publish calls全為0
- state與semantic budget不變；gen06不存在
- failure receipt第二跑不重複累加，SHA-256均為 `bb374c813d88de3859315c5c9349a14cf0c816a6602481ebeb223efea3b3a81b`
- production tree 44 files，bytes before==after，changed files=[]

## Acceptance snapshot

```text
status: GO（RCA scoped re-review only；Repair未實作）
primary_verdict: TOPOLOGY_GUARD_OVERREACH
formation: gen05 current map → one formal provider call → persisted external plan → provider=0 revalidation
authoritative_mapping: current/new，fact topology digest differs from gen03
outline_only_signal: normalized H2 digest equal
secondary_factor: post-hydration lifecycle replay gap
remaining_risk: production gen05仍被 overreaching guard fail closed並停在 generation 5
next_step: 主線依最小 Repair frontier裁定是否建立原 chain唯一 bounded Repair
```
