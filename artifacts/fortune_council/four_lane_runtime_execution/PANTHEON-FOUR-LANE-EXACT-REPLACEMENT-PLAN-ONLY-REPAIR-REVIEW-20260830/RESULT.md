# Pantheon four-lane exact replacement plan-only Repair 第三次 re-review

## 裁決

`GO`

未發現阻塞問題。第二次 review 的
`STATE_ABSENT_ORPHAN_REPLACEMENT_RESIDUE` 已關閉；第一次 review 的 consumed-state、
write-before-drift、routing／identity-envelope與canonical／symlink findings亦全部維持
GREEN。此GO只接受 bounded code candidate，不授權production、provider、publisher、
promotion、commit或push。

## Findings

無P0／P1／P2 finding。

## 最新P1 closure

### Orphan attempt、state不存在：CLOSED

`scripts/agy_gemini_coordinator.py:2964` 現在不依賴replacement state存在才驗directory
shape：

- replacement directory不存在：允許fresh create。
- replacement directory為空：允許fresh create。
- directory只有exact matching `brief.json`：允許partial idempotent completion。
- directory含`attempts/`、candidate、review或任何其他entry：在plan與execute helper前
  fail closed。

獨立重跑四個正式fixture：

- no-state + orphan attempt + plan-only；
- matching brief + no-state + orphan attempt + plan-only；
- no-state + orphan attempt + execute；
- matching brief + no-state + orphan attempt + execute。

四者均return non-zero／structured rejected，`FailIfCalled`證明execute helper=0，且temp
root全bytes before==after。

### 五個queue bucket：CLOSED

Exact namespace residue現在逐一掃描：

- `outbox`
- `processing`
- `inbox`
- `archive`
- `failed`

五個negative fixture均在plan階段拒絕且bytes不變。Source沒有只掃EN或單一lane；shared
root與四條lane root都涵蓋。

## 全finding regression

### Consumed／complete／failed existing replacement：PASS

- replacement state存在時必須exact八欄schema、`status=active`與lineage一致。
- replacement directory必須exactly只有`brief.json`。
- existing attempt、complete、failed與五種queue residue全部reject。
- immediate second execute仍只回同一identity的`already_exists`，不重置state、不形成
  attempts或第二replacement。

### Identity lock與write-before drift：PASS

- execute先完成read-only plan，再取得source run identity lock。
- lock內完整重跑registry digest、run/brief、routing、Gen03 budget、source SHA、target
  path、replacement identity與queue residue。
- locked receipt drift會在helper前reject。
- race fixture令第一次read後source registry `failed→active`；第二次lock內read拒絕，
  replacement brief/state均不存在。

### Routing／identity-envelope：PASS

- `_active_run_integrity_block()`與existing identity-envelope primitives共同驗證state、brief、
  mode、lane與article identity。
- 只接受既有`translate_existing`的`i18n-new`／`i18n-rewrite` authority。
- routing drift與identity-envelope drift均reject。
- 沒有EN、locale、article ID或單一lane hardcode。

### Canonical／symlink boundary：PASS

- source registry parent、source run／brief、replacement run／brief／state與各parent均有
  canonical／symlink closure。
- source run symlink與replacement target symlink負向fixture均reject且bytes不變。
- 沒有shell、subprocess、command interpolation、secret或network新增。

### Production-shaped Gen03 2/2與isolation：PASS

Fixture具：

- source state `failed / LocalePlanValidationError`；
- routing／identity-envelope完整；
- Gen01與Gen02 Reviewer `REJECT`；
- Gen03 `PLANNING_CONTRACT_FAILURE / terminal_stage=PLANNING`；
- attempts exact `01/02/03`，無Gen04；
- current source SHA匹配；
- KO、JA、四lane與publisher protected bytes。

Plan與所有negative case使用全temp-root snapshot證明before==after；execute positive只形成
replacement brief/state及既有source identity lock使用，不建立attempt、queue job或
publisher mutation。

## Spec axis

`PASS`

- FR-001：正式CLI exact selector與required mutually-exclusive plan／execute成立。
- FR-002：plan-only只讀、canonical stdout plan、identity／lineage／source SHA／write-set
  完整。
- FR-003：execute在lock內重驗後只呼叫既有helper；runner/provider/publisher均0，fresh
  replacement未consume。
- FR-004：source terminal Gen03 repair 2/2保持，無Gen04；replacement是fresh identity與
  budget。
- FR-005：identity drift、second replacement、collision、consumed/pristine drift、queue
  residue、source drift與race全部fail closed；second execute idempotent。
- FR-006：automatic cycle仍使用default `allow_existing_replacement=false`，既有exact
  cycle selector語意未變。
- FR-007：四lane、KO／JA、publisher protected bytes維持；無外部呼叫。

## Standards axis

`PASS`

- Correctness：原兩個P1與P2、最新orphan P1全部關閉。
- Regression：automatic seed／lane cycle／exact selector／closed reason與internal helper
  targeted suites全綠。
- Security：canonical path、symlink、routing identity與closed selector均fail closed；無
  command injection、secret或外部I/O新增。
- Maintainability：唯一coordinator source seam；沒有新增registry、FSM、DB、authority或
  second helper owner。
- Testing：positive、negative、idempotency、race、five-bucket、production-shaped budget與
  protected bytes均有exact fixture。

## 獨立驗證

```text
exact replacement positive/negative/idempotency:
27 passed, 387 deselected

card affected replacement slice:
30 passed, 384 deselected

existing exact selector + closed replacement reason:
12 passed, 402 deselected

existing multilingual enqueue helper:
2 passed, 260 deselected

py_compile scripts/agy_gemini_coordinator.py:
PASS

git diff --check (source/test):
PASS
```

Full-file既有campaign schema drift與launchd installer hang維持前次獨立分類：current diff
沒有修改campaign fixture、multilingual coverage validator或installer，既有failure stack
未進本次exact replacement seam。這兩項不構成本candidate finding，但也不能把未完成的
full-file suite宣稱為PASS。

## Changed-file／LOC seal

```text
120  1  scripts/agy_gemini_coordinator.py
260  0  tests/test_agy_gemini_coordinator.py
```

- source exactly 1、test exactly 1，符合allowlist。
- source/test新增量剛好達120／260 ceiling；刪除量合規。
- `scripts/agy_multilingual_pipeline.py`、runner、publisher、shared validator diff均為0。
- `second_source_seam=false`。
- main worktree仍有unrelated tracked／untracked artifacts；後續只能精確stage本卡source、
  test、implementation RESULT與本review receipt。

## Remaining risk

- Full coordinator file不是全綠；已知baseline schema drift與installer hang須由其既有scope
  處置，不能拿本次targeted GO掩蓋。
- Source/test均已達LOC ceiling；接受前不得再附加功能或擴scope。
- 本GO不證明production replacement已建立，也不授權後續semantic/provider/publish。

## Final gate

```text
status: GO
verdict: GO
spec_axis: PASS
standards_axis: PASS
blocking_findings: 0
second_source_seam: false
production_mutation: 0
provider_calls: 0
runner_calls: 0
publisher_calls: 0
commit: 0
push: 0
```

Candidate可回主線進行精確allowlist integration。後續production plan／execute、promotion、
provider與publish仍須由主線依各自正式gate另行裁決。
