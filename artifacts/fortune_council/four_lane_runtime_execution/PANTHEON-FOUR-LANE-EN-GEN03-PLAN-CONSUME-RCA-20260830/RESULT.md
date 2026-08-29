# EN Gen03 plan consume RCA 結果

## 單一裁決

`GEN03_AUTHORITATIVE_TOPOLOGY_REUSE`

EN generation 03 Writer transport成功，failure不是 provider、queue、registry、repair budget或跨版本 lifecycle故障。first-bad是 generation 03 persisted external plan：它改了 normalized H2 wording，但保留了 generation 02 完全相同的 authoritative fact-to-section topology。兩個連續 Reviewer history又共同命中 `SOURCE_SYNTAX_TRANSFER`，所以 local pipeline正確令 `rebuild_outline=true`；current authoritative topology guard因此 fail closed。

Exact high-level error：

```text
deterministic locale plan failure: locale plan rebuild reused prior outline topology for article-01
```

Direct validator message：

```text
locale plan rebuild reused prior outline topology for article-01
```

這不是舊 Gen05 `TOPOLOGY_GUARD_OVERREACH` 重現。舊案是「headings相同、authoritative topology不同」卻被舊 OR predicate拒絕；本案恰好相反：headings不同、authoritative topology相同。commit `79884d8bff7256aa9d1adcb7133162d7ac30b86d` 已把 guard縮到 topology equality，本案命中的是修正後仍應拒絕的 invariant。

## CodeGraph 與 source boundary

- 先查 live actor CodeGraph；該 checkout沒有初始化 graph，回 `CodeGraph not initialized`。
- 改查 main workspace CodeGraph，定位 `LocalePlanValidationError`、`_run_locale_generation`、`_continue_writer_reviewer_unlocked`；index提供的是較舊 source line，僅作 seam candidate。
- 依卡片切到限域 live actor `rg`／line read，確認 current actor `f456a4d8c21ce0a237254d31e6662339a1d522fb` 的實際 predicate、artifact catch與coordinator registry transition。

沒有因 graph缺失而擴張掃描或修改 source。

## Last-good 與 first-bad

### Last-good

同類型 deterministic plan-consume／hydrate edge的 last-good 是 **generation 02 plan consume**：

- `attempts/02/plan-operation.json`：Writer `gemini-3.5-flash-lite`、`status=success`。
- `attempts/02/planning-result.json`：`planning_contract_status=PASS`、`transport_status=EXTERNAL_PLAN_AVAILABLE`。
- `attempts/02/locale-plan.json`存在；後續 article Writer、candidate與Reviewer也都形成。
- generation 02 Reviewer為 `REJECT`，finding codes是 `SOURCE_SYNTAX_TRANSFER`、`MIRRORED_STRUCTURE`；不是 deterministic hard failure。

若按時間上的最後成功 edge，則是 generation 03 provider Writer transport本身：job `7af8867e8b2684434d8efde7f6b74cba93c6a613` 的 production attempt為 `succeeded`，inbox／archive完整。它成功交付 response，不代表response通過本機 plan contract。

### First-bad

Artifact-level first-bad是：

- `attempts/03/external-plan.json`
- raw SHA-256 `3aa9ee7b5f7a4db0f3f6b228d84f534e0de6bd58bf1b15f9d856ae78e474cbf1`
- bound job `7af8867e8b2684434d8efde7f6b74cba93c6a613`
- request SHA-256 `7af8867e8b2684434d8efde7f6b74cba93c6a6138a09909443f50dd2d218a891`
- prompt SHA-256 `5dd52b1ce79223be61ff35b97869e4ed4e05a03dba8fde914c7c96266ab7e8b6`
- schema SHA-256 `27eae7d09a73e2df2c0bb6f2c3e08a07fb586fd188042d74712a216277be4fac`

它的 normalized outline digest `4734c6bba41d57360f3b619dafd7e3905f5568d374c5bbbc22c4d6b4a99465a2` 與 prior Gen02 digest `86ea417db10e3a68d7bf77e382d6501b4953f2c7210539dc34fbcc72a27c0da9` 不同；但兩者 canonical topology digest同為：

```text
582c347873dfeb1309b8d6dd19777cf7b079990b7e79562a9bdd7b62459e21d7
```

所以 first-bad mechanism是 provider plan只換 heading表面而沒有重分配 fact-to-section topology。

`first_bad_commit=NONE`：本次 invalid bytes是 external provider artifact，不是 git commit。程式史需分開記錄：

- `f0b70b4bba41a952f9b8bc2c12d3a2bc5c13502e` 首次加入 reused-topology fail-closed guard，但當時同時含 heading equality的過寬 OR branch。
- `79884d8bff7256aa9d1adcb7133162d7ac30b86d` 移除 heading-only branch，只保留 authoritative topology equality，並補「不同 headings、相同 topology必須拒絕」與「相同 headings、不同 topology必須允許」控制。
- current actor `f456a4d8c21ce0a237254d31e6662339a1d522fb` 保留 798 predicate，只新增 legacy registered brief normalization。它讓本 legacy brief合法進入current pipeline，沒有引入 topology failure。

因此 798是 current rejection mechanism的authoritative implementation commit，不是壞 commit；錯誤根因仍是 Gen03 external plan內容。

## Exact artifact formation chain

1. Gen01 Reviewer `REJECT`：`SOURCE_SYNTAX_TRANSFER`、`NON_NATIVE_SEARCH_INTENT`。
2. Gen02 plan通過，article與Reviewer完成；Gen02 Reviewer再 `REJECT`：`SOURCE_SYNTAX_TRANSFER`、`MIRRORED_STRUCTURE`。
3. `_rebuild_authority()` 只看最近兩代 history；共同 finding code含 `SOURCE_SYNTAX_TRANSFER`，且屬 `REBUILD_FINDING_CODES`，因此 `article-01=true`。
4. `_run_fresh_writer_reviewer()` 在 `max_repairs=2` 下進入最後的 generation 03，使用 Gen02 committed locale plan作 prior，materialize plan Writer job `7af8867e...a613`。
5. Formal i18n-rewrite runner成功形成 exactly one production attempt、archive與inbox；outbox／processing消失。這一步 transport成功。
6. Coordinator re-entry由 `_load_or_generate_external_locale_plan()` consume persisted response，形成 `attempts/03/external-plan.json`並把 `plan-operation.json`設成 `success`。
7. `_hydrate_locale_plan()` 依 local source facts canonicalize plan，`validate_locale_plan()` 比對 Gen02 prior；`rebuild_outline=true`且 non-empty topology完全相同，拋 direct `ValueError`。
8. `_run_locale_generation()` catch該 ValueError，寫 `planning-result.json`：`EXTERNAL_PLAN_AVAILABLE / PLANNING_CONTRACT_FAILURE / terminal_stage=PLANNING`與 exact terminal reason，接著包成 `LocalePlanValidationError`。
9. Coordinator `_advance()` generic exception boundary把 registry `active→failed`，寫 `error_type=LocalePlanValidationError`；registry schema只保留 error type，不保存message，message authority是 `planning-result.json`與reproducible exception。

Gen03沒有形成 `locale-plan.json`、article operation、candidate、Reviewer operation或review；article／reviewer／publish calls因此都是 0。

## Durable invariant

### Registry

- run `auto-i18n-en-aa637e1bf05d3ad21429`
- lane `i18n-rewrite`
- status `failed`
- `last_job_id=7af8867e8b2684434d8efde7f6b74cba93c6a613`
- `error_type=LocalePlanValidationError`
- legacy registry `generation=null`，identity envelope與run directory保持不變
- raw SHA-256 `7b98f9c9eb11f32bce7768046dcd48a51c4ca4c4edd9f28dfae8b8bbf736cff8`

### Generation root

- lifecycle root是 `attempts/01..03`，不是 continuation `generations/04..`。
- Gen01、Gen02有committed locale plan／candidate／review。
- Gen03只准保留 successful transport audit三件：`plan-operation.json`、`external-plan.json`、`planning-result.json`。
- Gen03 planning result raw SHA-256 `5bc3b6fd49d040818ea67e3460b84716a742604a33811822fe41a0875963857d`。
- 不得把 rejected external plan升格成 locale plan或跨過 article／Reviewer boundary。

### Lane residue

- exact Gen03 job：outbox absent、processing absent、failed absent；inbox present、archive present、production-attempt present且 `attempt_status=succeeded`。
- inbox raw SHA-256 `a5a71bdb74be7f0858f3ce1c6a4f3570e24c58b4f585008b93f465095107e7c5`。
- archive raw SHA-256 `2b0d489562dd7858a1dce1c44b1bad22f2c5de8201a79fe2cef2bc8e9ddf8673`。
- attempt raw SHA-256 `eb9a6220172c5fd4961a7a885af4027c030fa0e97fe7a47e4ef3749ae7287595`。

這些是已成功外傳／回收的不可刪 audit，不能再投遞同一 request。

### Repair budget

- runtime `OUTBOX_MAX_REPAIRS=2`；fresh loop範圍是 generation 01 initial + generation 02／03兩次 repairs。
- Gen03是 repair `2/2`、semantic generation `3/3`，已是最後 allocation。
- 它在 planning validation終止，沒有 Gen03 Reviewer，但不能因此暗中建立 generation 04；同一 run的fresh semantic budget已無下一 generation。

## Provider=0 exact RED

已實跑：

```sh
PYTHONDONTWRITEBYTECODE=1 \
  <python-3.12> \
  /tmp/pantheon-en-gen03-plan-consume-rca-20260830/red_fixture.py
```

Fixture只把 exact production run與registry複製到 isolated temp queue；registry唯一調整是把 `run_dir`重定位到temp copy，以通過current legacy trusted-state path binding。brief、attempt artifacts、external plans、reviews及所有 semantic bytes保持原樣；client為 `FailIfCalled`。

結果：

- `status=RED`
- high-level與direct error逐字符合本 RCA
- `provider_calls=0`
- `rebuild_authority.article-01=true`
- `normalized_outline_equal=false`
- `topology_equal=true`
- 把唯一控制變數 `rebuild_by_slot` 改為 false時 exact Gen03 artifact可 hydrate，證明 failure只由 required rebuild + reused authoritative topology形成
- temp `planning-result`形成同一 `PLANNING_CONTRACT_FAILURE`與terminal reason

Protected immutable snapshot涵蓋 exact EN run／registry、i18n-rewrite與i18n-new lane residues、全部 current KO／JA translation runs、publisher ledger、current publish-canary run，以及live source／test seam，共396 files：

```text
before = ca72338acf9429841ff36f5d87c5ee0fbaea7b3c31f78ba1da0116ce8b9912f6
after  = ca72338acf9429841ff36f5d87c5ee0fbaea7b3c31f78ba1da0116ce8b9912f6
changed_files = []
```

另外以current live actor tests驗證 predicate兩面與第三代repair contract：

```text
3 passed, 275 deselected
```

涵蓋：不同 headings／相同 topology拒絕、相同 headings／不同 topology允許，以及第三代repair必須產生不同 topology。測試因live actor唯讀而只警告無法建立 `.pytest_cache`，沒有source/test mutation。

## 與 Gen04／Gen05 seam 的關係

### Gen04：不同根因

舊 Gen04是 continuation `generations/04` 的 partial allocation／terminalization／semantic-budget accounting：缺 source-ref map與完整 planning outcome，需要保留audit、abandon allocation，再把authority移到Gen05。它依賴 `continuation/state.json`、partial-generation decision與authority transition。

本 EN run沒有 `continuation/`或 `generations/`，而是fresh `attempts/03`；Gen03 provider outcome完整、planning failure明確、registry已failed。不是 Gen04 lifecycle seam。

### Gen05：同 validator family，不同根因

舊 Gen05 exact case在 repair前是：normalized headings相同，但 authoritative topology不同；舊 guard仍因 heading equality拒絕，所以裁決 `TOPOLOGY_GUARD_OVERREACH`。798 repair後，這種plan會通過。

本 EN case是：normalized headings不同，但 authoritative topology完全相同；這正是current tests要求拒絕的 synonym／surface-only rebuild。因此只有 error文字與validator family相同，內容authority判定相反；不是舊 Gen05 regression或 lifecycle replay。

## Authoritative owner 與跨版本 boundary

| authority | owner | 本案裁決 |
|---|---|---|
| registered run/lane/identity | coordinator registry | f232 namespace與i18n-rewrite identity不變 |
| legacy brief normalization | current local actor f456 + trusted registry | 只移除legacy lane field進入strict brief contract，不改source semantic bytes |
| prior plan | local committed `attempts/02/locale-plan.json` | Gen03唯一合法baseline |
| rebuild requirement | local `_rebuild_authority` from last two Reviewer histories | common `SOURCE_SYNTAX_TRANSFER`使Gen03 rebuild=true |
| external plan | provider proposal | transport成功，但未通過local promotion gate |
| fact-to-section topology | local canonical source facts + `_outline_topology` validator | Gen02/Gen03 digest相同，invalid rebuild |
| planning outcome | local `_run_locale_generation` | authoritative `PLANNING_CONTRACT_FAILURE` |
| terminal run status | coordinator `_advance` | authoritative registry failed |
| semantic budget | outbox constant + fresh loop | final Gen03 allocation，禁止Gen04 |

跨版本上，run/brief始於legacy flat格式；f456只透過registry-bound normalization讓它合法執行。Gen02與Gen03 operations及本次consume都在current f456/g73 boundary形成；沒有舊 actor把Gen04／Gen05 continuation state帶進來。Promotion只替換actor／manifest並保留queue bytes，無權把invalid plan變成valid，也不是retry seam。

## Existing operational seams 與 boundary

- Generic `resume`：會把registry改回active，但保留 exact invalid Gen03 cache；下一 coordinator consume只會 provider=0重現同一 failure。它不是合格 recovery，禁止使用。
- `retry-same-generation-locale-plan`：正式 seam只接受 continuation `generations/<NN>` 加 `continuation/state.json` 的 active next-generation shape。本案是fresh `attempts/03`且沒有continuation state，正式 preflight應 fail closed；不得硬套。
- Failed translation replacement：coordinator現有 `_translation_replacement_reason()` 明確把 terminal `LocalePlanValidationError`分類為 `LOCALE_PLAN_VALIDATION`，`seed_failed_translation_replacements()` 可在新 run identity `-replacement-01` 下重新開始。這才是跨越本 run terminal／budget boundary的正式既有 seam；它不修改或刪除舊 run audit。
- Replacement仍是production mutation並會導向新的 semantic/provider calls；本 RCA沒有 plan、execute、seed或授權它。下一步只能由主線另行鎖定 existing replacement seam的zero-write preflight與明確provider disclosure budget，不得由本卡默示執行。

Publisher boundary保持關閉：沒有Gen03 candidate／Reviewer APPROVE，舊 run又是failed，因此promotion、replacement decision或status文案都不能授權 publish。

## Why not less / why not more / do not absorb

### why_not_less

只把registry `resume`或清掉 `error_type`不足：invalid external-plan bytes與success transport residue都還在，重入只會相同 RED；手改plan、刪cache或重送同 job又會破壞audit與at-most-once invariant。

### why_not_more

不需要 source/test Repair。Current guard已精確區分 heading wording與authoritative topology，三個相關 tests PASS，exact fixture又證明唯一真 predicate是 topology equality。現成 failed-translation replacement已提供跨terminal identity boundary；不需新增migration、registry、FSM或第二套retry。

### do_not_absorb

- 不放寬 topology validator，不把換標題視為結構重建。
- 不新增 Gen04、補寫 Gen03 locale plan、手改 provider payload或覆寫planning result。
- 不對同 job重送 provider，不刪 inbox／archive／attempt。
- 不把 continuation same-generation retry硬套到fresh attempts lifecycle。
- 不開 Repair、新authority、generic migration、registry、FSM、promotion或publisher工作。
- 不把 failed／replacement eligibility誤稱為Reviewer approved或publishable。

## Acceptance snapshot

```text
status: GO（RCA only；run仍 terminal failed）
primary_verdict: GEN03_AUTHORITATIVE_TOPOLOGY_REUSE
last_good_same_edge: generation 02 plan consume/hydrate PASS
last_good_transport_edge: generation 03 Writer provider transport succeeded
first_bad: generation 03 external-plan content → authoritative topology validator
first_bad_commit: NONE（external artifact；79884d8是正確 guard）
provider_calls_in_rca: 0
production_mutation_in_rca: 0
publish_calls_in_rca: 0
protected_bytes: 396 files, before == after, changed=[]
same_root_as_gen04: no
same_root_as_old_gen05: no；同 validator family、相反 authority facts
bounded_next_boundary: existing failed-translation replacement zero-write preflight only；需另行授權
```
