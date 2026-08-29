# Pantheon four-lane exact replacement plan-only bounded Repair

## 工作名稱

`EXACT-REPLACEMENT-PLAN-ONLY-REPAIR-20260830`

## 狀態

`READY_FOR_IMPLEMENTATION`

本卡只授權一個 bounded source seam：為既有 failed-translation replacement lifecycle
增加正式 CLI 的 exact source-run plan／execute boundary。不得藉此修改 replacement
內部生命週期、執行 provider、推進 replacement、處理其他 lane，或重開 Gen03。

## Spec authority

- `CARD-PANTHEON-FOUR-LANE-EN-GEN03-PLAN-CONSUME-RCA-20260830.md`
- `PANTHEON-FOUR-LANE-EN-GEN03-PLAN-CONSUME-RCA-20260830/RESULT.md`
- `PANTHEON-FOUR-LANE-EN-GEN03-REPLACEMENT-BOUNDARY-REVIEW-20260830/RESULT.md`

已接受的上游裁決：

- 原 EN run 的唯一內容根因是 `GEN03_AUTHORITATIVE_TOPOLOGY_REUSE`。
- 原 run 已在 Gen03 終止，repair `2/2`、semantic generation `3/3`；不得 resume、
  retry 同一 job 或建立 Gen04。
- 既有 `enqueue_translation_replacement()` 已擁有 fresh identity、lineage、source SHA
  revalidation、獨立 budget、一次性 replacement 與 idempotency。
- 唯一 measured gap 是 production CLI 沒有同時滿足 exact source run、zero-write
  plan-only、single replacement creation 與 zero runner 的正式入口。

## CodeGraph／source discovery

依專案規則先查 CodeGraph；main workspace index 未命中 coordinator replacement
symbols，回傳的是無關 prototype entry points。之後只限域檢查：

- `scripts/agy_gemini_coordinator.py`
- `scripts/agy_multilingual_pipeline.py::enqueue_translation_replacement`
- `tests/test_agy_gemini_coordinator.py`
- `tests/test_agy_multilingual_pipeline.py` 既有 replacement tests

結果：正式 parser、exact state selection、closed replacement reason、lane routing與
既有 helper import 均已在 coordinator；本 Repair 只需修改 coordinator 一個 source
檔與其一個 test 檔。`agy_multilingual_pipeline.py` 不需修改。若實作時發現必須修改
第二個 source seam，本卡立即轉為 `BLOCKED_SECOND_SOURCE_SEAM`，不得擴張 allowlist。

## Measured gap

現有 unscoped `--lane-mode cycle` 只有在 `selected_run_ids is None` 時才會呼叫
`seed_failed_translation_replacements()`；指定 `--exact-run-id` 反而關閉 replacement
seeding。unscoped cycle 還可能推進 KO／JA、呼叫 `_advance()` 與 runner。現有
`replace-failed-external-job` 是 external job replacement，不是 terminal translation
run replacement，禁止借用或混合語意。

因此 current formal operator interface 無法做到：

1. 精確鎖定一個 failed terminal source run；
2. plan-only 完整驗證 identity／lineage／source SHA 而零寫入；
3. execute 時只建立 fresh replacement run；
4. 不自動 consume replacement、不呼叫 runner/provider/publisher；
5. 不改其他 KO／JA／lane bytes。

## User story

### US-001｜Exact terminal translation replacement

作為 production operator，我要用正式 CLI 精確指定一個 eligible failed translation
run，先取得零寫入 plan，再於明確 execute 下只建立一次 fresh replacement，使原
terminal audit與其他 lane維持不變，且 replacement 後續仍必須由正常 coordinator
入口另行推進。

## Functional requirements

### FR-001｜正式 exact selector

新增一個語意專屬的 coordinator subcommand；名稱可由實作者在本卡語意內選定，但
不得重用 `replace-failed-external-job`。命令至少要求：

- `--run-id <exact-source-run-id>`
- `--expected-registry-digest <sha256>`
- `--expected-run-dir <path>`
- `--plan-only` 或 `--execute`，兩者互斥且不得兩者皆缺

`--run-id` 是 terminal source run identity，不是 provider job ID 或 replacement ID。
入口只能讀取 exact registry record；不得掃描並自動選取另一個 failed run。

### FR-002｜Fail-closed plan-only

`--plan-only` 必須零寫入並輸出 canonical JSON plan。它至少證明：

- exact registry digest、run ID、run directory均相符；
- source state 是 `failed`，closed recovery reason可由既有
  `_translation_replacement_reason()` 推導；
- source run不是 `-replacement-01`，且沒有既有第二層 replacement；
- base brief identity合法；每個 current source SHA與brief中的 SHA相符；
- proposed replacement ID固定為 `<source-run-id>-replacement-01`；
- proposed lineage、reason、fresh run directory與state path均可決定；
- expected write set只含 fresh replacement brief／state；
- `runner_invoked=false`、`provider_invoked=false`、`publisher_invoked=false`。

Plan-only stdout JSON就是可保存的 operator receipt；不得在 production queue、registry、
run root或lane root另寫 plan receipt。

### FR-003｜Thin execute routing

`--execute` 必須重做 FR-002 的 exact identity與source SHA檢查，之後只把 exact terminal
state與closed recovery reason傳給既有
`multilingual.enqueue_translation_replacement()`。不得複製、改寫或繞過該 helper
內部的 identity、lineage、brief、source revalidation或idempotency契約。

Execute stdout receipt至少包含：

- `status=replacement_created` 或既有同 identity的 idempotent結果；
- source run ID、replacement run ID、replacement reason；
- replacement run directory與state path；
- `source_terminal_preserved=true`；
- `runner_invoked=false`、`provider_invoked=false`、`publisher_invoked=false`；
- `replacement_consumed=false`。

入口不得呼叫 `cycle_once()`、`_advance()`、`process()`、Gemini client、publisher、
promotion、tag或push。建立後 replacement 保持 `active` 且尚無 semantic attempt；下一
次推進必須由另一個正式 coordinator invocation另行授權。

### FR-004｜Terminal與budget boundary保持

原 source run必須維持 failed terminal，Gen03 repair `2/2`與所有 attempts／lane audit
bytes不變；不得建立 source Gen04、清理source error、改 source registry或重投原 job。
Fresh replacement使用新的 run identity、空 attempts與自己的 generation 01／repair
budget；不得繼承 Gen03 external plan、locale plan、fact mapping或repair history作為
authoritative planning artifact。

### FR-005｜Closed negative與idempotency

以下全部 fail closed且不得產生任何寫入：

- exact source run不存在、registry digest或run directory不符；
- source state不是failed，或failure不在closed replacement reasons；
- source brief/run identity不符；
- current source SHA drift；
- source本身已是replacement；
- replacement identity已存在但bytes／lineage不符；
- 要求第二層replacement。

同一 source、同一bytes與同一reason重跑execute只能回到同一 replacement identity，
不得建立第二個 run、重置其狀態或重複消耗budget。

### FR-006｜既有 unscoped cycle語意不變

不得修改既有 lane sweep selection、per-lane bounded seeding、skip decision、migration、
runner routing或 `cycle --exact-run-id` 目前不自動seed replacement的語意。新入口是
operator-only exact seam，不取代或重寫既有 automatic lane sweep。

### FR-007｜隔離與零外部呼叫

Plan與execute測試都必須以 before／after bytes證明非目標 KO／JA registry、translation
run、lane queue與publisher state不變。provider、runner、`_advance`與publisher使用
`FailIfCalled`／monkeypatch計數，所有 calls均為0。

## Success criteria

### SC-001｜Exact positive plan

對 isolated eligible failed source run執行正式 CLI plan-only：return code 0、stdout
schema完整、proposed replacement identity正確、expected write set精確，且全 fixture
bytes before==after。

### SC-002｜Exact positive execute

同一 fixture執行正式 CLI execute：exactly one replacement brief與registry state形成；
source terminal bytes不變；replacement lineage/reason/source identity正確；attempts與
outbox均不存在；runner/provider/publisher calls=0。

### SC-003｜Negative closure

nonfailed／ineligible、wrong registry digest、wrong run directory、source SHA drift與
second replacement全部return non-zero或structured rejected，且before==after。

### SC-004｜Idempotency

同一 execute連跑兩次只保留同一 replacement run；第二跑不新增檔案、不改已存在的
replacement bytes、不重複生成 semantic attempt。

### SC-005｜Isolation

Exact EN fixture的KO／JA與其他 lane bytes before==after；不建立或修改其他 replacement。

### SC-006｜Regression

既有 internal replacement tests、unscoped lane cycle tests、coordinator affected suite、
`py_compile`與`git diff --check`全部PASS；既有 shared helper與validator source diff為0。

## Trace matrix

| Requirement | Acceptance | Slice |
|---|---|---|
| US-001 | FR-001..FR-007 | SLICE-ERP-001, SLICE-ERP-002, SLICE-ERP-003 |
| FR-001 | SC-001, SC-002, SC-003 | SLICE-ERP-001, SLICE-ERP-002 |
| FR-002 | SC-001, SC-003, SC-005 | SLICE-ERP-001 |
| FR-003 | SC-002, SC-004, SC-005 | SLICE-ERP-002 |
| FR-004 | SC-002, SC-004 | SLICE-ERP-002 |
| FR-005 | SC-003, SC-004 | SLICE-ERP-001, SLICE-ERP-002 |
| FR-006 | SC-006 | SLICE-ERP-003 |
| FR-007 | SC-001, SC-002, SC-003, SC-005 | SLICE-ERP-001, SLICE-ERP-002 |

Trace preflight：沒有 dangling reference、重複ID、未解 blocking decision或缺驗證方式。
Jira、architecture diagram、data flow皆 `not-applicable`：本卡是既有單一 CLI seam 的
bounded bug fix，不建立新產品需求、架構節點或資料平台。

## Implementation slices

### SLICE-ERP-001｜Exact plan-only vertical path

`traces_to: [US-001, FR-001, FR-002, FR-005, FR-007, SC-001, SC-003, SC-005]`

Blocking edges：上游 RCA與replacement boundary review已閉合；無其他 blocker。

TDD checkpoint：

1. **RED**：先以 public `main()`／CLI參數建立 exact positive plan、nonfailed、wrong
   registry digest、wrong run dir、source drift與other-lane byte isolation tests；修前因
   subcommand不存在而RED。
2. **GREEN**：只在 coordinator新增argument parser與一個thin plan function；使用既有
   state／lane／brief／source loader／SHA primitives，輸出canonical plan JSON，零寫入。
3. **Verify**：全 fixture bytes不變；`_advance`、runner、provider、publisher均0 calls。

交付的是可獨立使用的exact zero-write preflight，不等待execute slice才有價值。

### SLICE-ERP-002｜Exact replacement creation vertical path

`traces_to: [US-001, FR-001, FR-003, FR-004, FR-005, FR-007, SC-002, SC-003, SC-004, SC-005]`

Blocking edges：`SLICE-ERP-001` GREEN且plan schema固定。

TDD checkpoint：

1. **RED**：新增exact execute、二次execute idempotency、replacement lineage exhausted、
   existing collision與zero-runner tests。
2. **GREEN**：execute重跑相同preflight後，只呼叫既有
   `enqueue_translation_replacement()`；將其結果包成stable stdout receipt。
3. **Verify**：只形成fresh replacement brief/state；source terminal、KO／JA／lane bytes
   不變；replacement attempts/outbox不存在；所有外部與推進calls=0。

### Checkpoint CP-001｜Boundary seal

`SLICE-ERP-001`與`SLICE-ERP-002`通過後，獨立檢查source diff。若出現第二個source
檔、internal helper改動、generic selector、lane/EN特判或任何runner call，立即退件，
不得進 regression slice。

### SLICE-ERP-003｜Regression與交付證據

`traces_to: [US-001, FR-006, SC-006]`

Blocking edges：`CP-001` PASS。

不新增功能；只跑既有 affected tests與明示的 unscoped cycle regression，證明新入口
沒有改 automatic sweep semantics。完成 `py_compile`、targeted suite、affected
coordinator suite與`git diff --check`，產生reviewable receipt。

### Current frontier

`SLICE-ERP-001` 是唯一 frontier。不得先做execute或修改helper。

## File allowlist與LOC ceiling

唯一 source allowlist：

- `scripts/agy_gemini_coordinator.py`

唯一 test allowlist：

- `tests/test_agy_gemini_coordinator.py`

Evidence allowlist：

- 本卡指定的單一 Repair result／review receipt路徑，由主線另行命名。

Changed LOC ceiling（以 `git diff --numstat` 計，generated evidence不計）：

- source：新增＋修改合計不超過 **120 LOC**；刪除不超過 **20 LOC**。
- tests：新增＋修改合計不超過 **260 LOC**；刪除不超過 **20 LOC**。
- source files changed：exactly 1。
- test files changed：exactly 1。

若要修改 `scripts/agy_multilingual_pipeline.py`、第二個source檔、shared validator、runner
或publisher，裁決即為 `BLOCKED_SECOND_SOURCE_SEAM`；不得自行提高LOC ceiling。

## 禁止範圍

- 不修改 `enqueue_translation_replacement()` 或其internal lifecycle。
- 不新增registry、FSM、DB、ledger、queue、manifest schema或第二套replacement owner。
- 不新增EN、run ID、article ID、locale或lane特判；功能適用所有既有eligible i18n runs。
- 不放寬closed replacement reasons、source SHA、run path、registry digest或lineage驗證。
- 不自動呼叫coordinator cycle、`_advance()`、runner/provider/reviewer/publisher。
- 不自動consume、plan、write或review fresh replacement的generation 01。
- 不修改或刪除原 Gen03 artifacts、lane archive/inbox/attempt或terminal registry。
- 不執行production、promotion、service activation、provider、publish、tag或push。
- 不用private Python one-liner取代正式 CLI。
- 不把translation run replacement與external job replacement合併。

## Why not less

只用internal helper或unscoped lane cycle不足：前者不是正式operator boundary；後者不能
exact、不能plan-only，且可能推進KO／JA與runner。只新增文件或測試也無法補上已量測
缺失的public CLI seam。

## Why not more

既有helper已完整擁有fresh identity、lineage、source revalidation、budget與idempotency；
不需要改multilingual pipeline、重寫automatic sweep、抽象generic replacement framework
或增加持久authority。CLI只需做exact fail-closed preflight與thin execute routing。

## Do not absorb

- 不吸收generic retry/recovery/migration framework。
- 不吸收跨lane batch replacement、scheduler hook或always-on automation。
- 不吸收新的provider disclosure、semantic repair或publisher acceptance。
- 不吸收Gen03 plan validator、Gen04/Gen05 lifecycle或promotion工作。
- 不吸收未量測的future replacement variants。

## Rollback

Code rollback只需回退本卡新增的coordinator subcommand／thin router與對應tests；既有
automatic sweep及`enqueue_translation_replacement()`保持原樣。因本Repair本身禁止
production execution，實作與review階段不會留下production replacement state。

後續若主線另行授權production execute，已建立的replacement是durable audit，不得以
code rollback刪除；只能停止後續consume並依既有terminal/lineage契約處置。

## Verification commands

實作者須依實際新增test names限域執行，至少包含：

```sh
<repo-python> -m py_compile scripts/agy_gemini_coordinator.py
<repo-python> -m pytest -q tests/test_agy_gemini_coordinator.py -k 'translation_replacement and (exact or seed or lane_cycle)'
<repo-python> -m pytest -q tests/test_agy_multilingual_pipeline.py -k 'enqueue_translation_replacement'
git diff --check
git diff --numstat -- scripts/agy_gemini_coordinator.py tests/test_agy_gemini_coordinator.py
```

最終 independent review必須核對：

- changed files完全符合allowlist與LOC ceiling；
- plan-only production-shaped fixture真正zero-write；
- execute只建立replacement且zero runner；
- source terminal 2/2、fresh identity/lineage/budget與source SHA invariant；
- KO／JA／other lane protected bytes before==after；
- unscoped cycle semantics未改；
- provider/coordinator advance/publisher calls=0；
- 沒有第二source seam或scope expansion。

## Completion gate

```text
READY_FOR_IMPLEMENTATION
  iff SLICE-ERP-001 is the only frontier
  and source allowlist remains exactly one coordinator file

BLOCKED_SECOND_SOURCE_SEAM
  if implementation requires any second source file or helper lifecycle change

RE_REVIEW_REQUESTED
  after RED→GREEN checkpoints, affected regressions, diff/LOC checks all PASS
```

本卡完成不等於production replacement已建立，也不等於EN文章可publish。Repair經獨立
review、commit、push與新promotion後，主線才可另行執行exact plan-only與production
execute acceptance。
