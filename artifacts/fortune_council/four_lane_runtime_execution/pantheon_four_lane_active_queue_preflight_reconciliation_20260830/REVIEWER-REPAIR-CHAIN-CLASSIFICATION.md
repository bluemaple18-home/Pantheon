# EN Reviewer → repair lifecycle classification

## 單一裁決

`EXPECTED_BOUNDED_REPAIR`

Reviewer job `86f55643cebd103cec1faae8e0da841ab0000f96` 已成功處理；其 generation 01 review 為 `REJECT`，finding 類別只有 `SOURCE_SYNTAX_TRANSFER` 與 `NON_NATIVE_SEARCH_INTENT`，沒有 deterministic hard failure。coordinator 隨後 materialize 的 Writer job `226c8096659799de31bf237c17f3186c6f72ac1d` 是 generation 02 的 **locale-plan repair operation**，不是直接文章 repair，也不是 role drift。

現行 production semantic budget 是 `max_repairs=2`。fresh loop 可執行 generation 01 初始嘗試，加 generation 02、03 兩次 repair；目前已完成 initial generation 01，已 allocation generation 02，因此 current repair count 是 `1/2`，semantic generation usage 是 `2/3`。沒有 budget drift。

本卡只讀 identity、digest、status 與 finding code；沒有讀取或輸出 prompt、schema、文章或 reviewer message 正文。

## Exact current evidence

| edge | immutable observation |
|---|---|
| run | `auto-i18n-en-aa637e1bf05d3ad21429` |
| lane / namespace | `i18n-rewrite` / `f2324fee6f9d81fe4febbc6e` |
| registry | `active`；`last_job_id=226c8096659799de31bf237c17f3186c6f72ac1d`；legacy flat `generation=null`；updated `2026-08-30T02:40:54+08:00` |
| completed Reviewer | job `86f55643cebd103cec1faae8e0da841ab0000f96`；role `reviewer`；model `gemini-3.1-flash-lite`；request SHA-256 `86f55643cebd103cec1faae8e0da841ab0000f963e98ce26819d1356bb369622` |
| Reviewer binding | prompt SHA-256 `691c9e97f12662464d6939e6f93384ae8c7f1f335c7096d48fb885442f0e910b`；schema SHA-256 `3895a88af266c8f9ebde177ade284b9feab2075dd2375c53ac09bccee0d07940`；`reviewer-operation.json=status=success` |
| Reviewer outcome | article identity `ASTRO-BASE-03:en`；verdict `REJECT`；finding codes `SOURCE_SYNTAX_TRANSFER`, `NON_NATIVE_SEARCH_INTENT`；`hard_failure=null`；deterministic findings count `0` |
| repair Writer | job `226c8096659799de31bf237c17f3186c6f72ac1d`；role `writer`；model `gemini-3.5-flash-lite`；operation level `external_generation` |
| repair request binding | request SHA-256 `226c8096659799de31bf237c17f3186c6f72ac1d8ac360d1818deaa271b9249b`；prompt SHA-256 `e60b19a2faa5979af0cf5287d37879a6ec11b541b5096c32216312963f88f6cf`；schema SHA-256 `27eae7d09a73e2df2c0bb6f2c3e08a07fb586fd188042d74712a216277be4fac` |
| repair operation receipt | `attempts/02/plan-operation.json` 的 role/model/prompt/schema逐字匹配 envelope；`status=pending`、`error_type=ExternalJobPending` |
| queue placement | exact job只有 `i18n-rewrite/outbox` 一份；raw SHA-256 `d1f4bab999fd1340fbdb0fff5669ae780369a64fa5d638333e12d40ef68724ab`；processing/inbox/archive/failed/attempt全部不存在 |
| generation 02 state | 只有 `attempts/02/plan-operation.json`；沒有 external plan、locale plan、article operation、candidate、reviewer operation或 review |

`operation_level=external_generation` 本身不足以辨識 stage；authoritative stage binding 是 run-local operation receipt的 prompt/schema digest。repair job 的 schema digest與 locale-plan schema一致，且 `plan-operation.json` 是唯一 pending receipt，因此它是 generation 02 plan Writer。

## Budget、exactly-once 與 role chain

Live actor `scripts/agy_gemini_outbox.py` 將 `OUTBOX_MAX_REPAIRS=2` 傳給 multilingual runner。`scripts/agy_multilingual_pipeline.py::_validate_semantic_budget` 又把合法值封閉在 0–2；`_run_fresh_writer_reviewer` 執行 `range(1, max_repairs + 2)`，所以最多是三個 semantic generations，而不是 initial 加三次 repair。

每個 generation 的固定角色順序由 `_run_locale_generation` 鎖定：

```text
Writer locale plan
  → local hydrate/validate
  → Writer translated article
  → local deterministic findings
  → independent Reviewer
```

Reviewer REJECT後，loop把 findings加入 history並進入下一 generation；下一筆必須先是 plan Writer。現況正好符合這條 transition。相同 external request的 deterministic job identity會復用既有 outbox/processing/archive request；operation output存在時又直接復用，不重生同 stage。current filesystem只有一份 generation 02 plan receipt與一份 matching outbox，支持「exactly one expected repair Writer pending」，不支持 duplicate或 role drift。

## Controls：成功與 terminal reject

- Unit control `test_candidate_outline_mismatch_enters_semantic_repair` 鎖定 generation 01 REJECT後進入一次 repair，下一輪 Reviewer APPROVE；`test_valid_locale_plan_reaches_candidate_persistence` 鎖定單 generation角色順序為 Writer plan → Writer article → Reviewer。
- Unit control `test_replacement_third_generation_gets_explicit_prior_topology_contract` 以 `max_repairs=2` 鎖定兩次 REJECT後可進 generation 03，第三次 Reviewer APPROVE即停止。
- Production-shaped terminal-reject control `auto-i18n-ja-1414b75a404721e95e74` 保存 attempts 01/02/03；三代皆是 plan Writer success → article Writer success → Reviewer success，三個 Reviewer verdict皆 REJECT。registry最後仍轉 `complete`。這證明 semantic budget耗盡是 lifecycle terminal boundary，但 `complete` 不等於 reviewer approved，也不等於 publishable。

## 後續預期 lifecycle 與 terminal boundary

處理 current repair plan Writer後，仍需按順序逐步 coordinator consume／materialize：

1. generation 02 plan response成功 consume，hydrate/validate locale plan；materialize恰好一筆 generation 02 article Writer。
2. generation 02 article response成功 consume，hydrate candidate、產 deterministic findings；materialize恰好一筆 generation 02 Reviewer，model `gemini-3.1-flash-lite`。
3. generation 02 Reviewer recheck若 `APPROVE` 且 findings空，loop停止、root candidate/review transaction寫入，coordinator回 complete，registry才可 terminalize `complete`。
4. 若 generation 02 Reviewer仍 REJECT，repair count成為 `1/2 completed`，再 materialize generation 03 plan Writer，這是最後一次 repair。
5. generation 03 Reviewer後無論 APPROVE或REJECT，semantic loop都到 budget terminal。APPROVE才具 reviewer-approved eligibility；REJECT只能 lifecycle terminalize，禁止誤稱可 publish。

因此 current registry保持 active是正確狀態；尚未達 Reviewer recheck或 terminal boundary。

## Pending external disclosure

- data category：generation 02 locale-plan repair prompt。由 registered brief的結構化 source identity／source-ref mapping、prior locale plan、Reviewer finding codes與 repair history組成，搭配 closed external locale-plan JSON schema；不包含 credential value。
- purpose：針對 `SOURCE_SYNTAX_TRANSFER` 與 `NON_NATIVE_SEARCH_INTENT` 重新規劃英文 article的 native structure與 search intent，之後才生成修訂文章。
- destination/model：formal `i18n-rewrite` Gemini Writer route，`gemini-3.5-flash-lite`。

這是新的 provider disclosure；前一 Reviewer call不自動授權本次 Writer call。本分類卡沒有執行。

## 唯一正確 pending selector（禁止本卡執行）

`--exact-run-id` 必須使用 pipeline run ID：

```text
--exact-run-id auto-i18n-en-aa637e1bf05d3ad21429
```

不得使用 repair job ID或 request SHA。其正式 service仍是 `com.pantheon.agy-gemini-i18n-rewrite`，actor/manifest boundary仍是 f456/g73，manifest digest仍須為 `11fb6be90bc282add14a8a41cdb1258add550004049ce866a9bdf0d926aeaf04`。完整 operator command沿用同 root `OPERATOR-SELECTOR-RCA.md` 所列 command，只把 current immutable preflight target鎖成 repair job `226c8096...ac1d` 與其 current digests；本卡不重複或執行 mutation command。

Immediate runner postconditions：

- wrapper `executed/0`，child必須 `processed` exact job `226c8096659799de31bf237c17f3186c6f72ac1d`；不得 idle或處理其他 job。
- exact outbox/processing歸零；形成 exactly one matching inbox、archive與 succeeded production-attempt，request SHA不變。
- `attempts/02/plan-operation.json` 在 runner後仍可保持 pending；只有下一次 exact coordinator consume才可改 success並 materialize article Writer。
- 不得在同一 runner call直接出現 article Writer、Reviewer、candidate、publish或 registry terminal mutation。

## Stop conditions

- 執行前，repair envelope raw SHA、request/prompt/schema digest、namespace、role/model任一漂移。
- exact processing/inbox/archive/failed/attempt任一已存在；尤其 attempt存在時禁止重送。
- lane outbox不是唯一一檔、registry不再 active，或 `last_job_id`不是 `226c8096...ac1d`。
- manifest/barrier/readiness不是 f456/g73，或 background consumer已 loaded，造成 operator race。
- child idle、failed、處理其他 job，或單次 runner形成多筆 attempt。
- coordinator consume plan後沒有 materialize恰好一筆 generation 02 article Writer；或 article consume後沒有 materialize恰好一筆 Reviewer recheck。
- generation 02後直接 terminalize、跳過 Reviewer、越過 generation 03，或生成 generation 04；任一都改判 `BUDGET_DRIFT`／`ROLE_DRIFT` 並停止。
- Reviewer REJECT後被當成 approved／publishable，或 lifecycle `complete`被當成 Reviewer APPROVE。

## Status

- classification：`EXPECTED_BOUNDED_REPAIR`
- semantic budget：`max_repairs=2`
- current repair count：`1/2 allocated`；`0/2 completed`
- generation usage：`2/3 allocated`；generation 01 completed，generation 02 plan pending
- exactly-one repair Writer：PASS／pending
- role drift：否
- budget drift：否
- payload正文 read/output：`0`
- provider call：`0`
- production mutation：`0`
- pending selector executed：`false`
- next status：`RE_REVIEW_REQUESTED`
