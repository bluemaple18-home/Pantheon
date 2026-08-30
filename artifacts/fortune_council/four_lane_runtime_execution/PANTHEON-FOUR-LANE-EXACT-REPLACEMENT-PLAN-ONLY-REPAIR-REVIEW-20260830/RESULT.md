# Pantheon exact replacement production-fixture re-review

## 裁決

`GO`

未發現阻塞問題。Production five-field fixture gap已在同一coordinator source seam關閉；
global strict validator、multilingual helper與raw production brief均未修改。先前consumed、
lock drift、orphan residue、five-bucket、routing／identity-envelope與symlink findings全部
維持PASS。

本GO只接受clean worktree candidate，不授權commit、push、promotion、production
replacement、provider、runner或publisher。

## Review authority

本輪只讀：

- worktree：`/private/tmp/pantheon-exact-replacement-f456`
- HEAD：`d7b09a99bd006544dd703a49f4ce774d32554c66`
- candidate：D7B加同worktree未提交production-fixture fix

沒有以stale主workspace source判斷candidate。Main workspace只更新本review receipt。

## Findings

無P0／P1／P2 finding。

## Production fixture gap closure

### Trusted-state normalization：PASS

`replace_failed_translation_run_exact()`現以：

```text
multilingual._normalize_registered_translation_brief(
    _brief(run_dir),
    run_dir,
    trusted_state=state,
)
```

取代raw brief直接進global strict validator。`state`已先通過exact run selector、registry
digest、canonical run dir與identity integrity；execute又在source run identity lock內重跑
相同preflight。

既有normalizer只接受：

- canonical四欄translation brief；或
- exact五欄legacy brief，唯一額外欄是`lane=i18n-rewrite`。

五欄path還要求trusted state的run ID、canonical run dir、status、lane與identity envelope
全部一致。錯lane、額外第六欄、state routing drift與envelope drift仍fail closed。Global
`validate_translation_brief()`保持四欄strict，沒有generic unknown-field stripping。

### Existing helper authority：PASS

D7B既有`multilingual.enqueue_translation_replacement()`已獨立對base raw brief呼叫相同
normalizer，並傳`trusted_state=terminal_state`。Coordinator只修preflight，execute仍只
呼叫既有helper；沒有修改第二source、helper lifecycle或validator。

### Legacy exact plan-only：PASS

Shared fixture現在預設production 0.3.368五欄shape：

```text
schema_version, run_id, mode, lane, articles
lane=i18n-rewrite
```

Plan-only同時參數化驗canonical四欄與legacy五欄；兩者均：

- return code 0；
- exact replacement ID／reason／expected write set正確；
- enqueue、cycle、runner calls=0；
- 全temp-root bytes before==after。

### Legacy exact execute：PASS

Execute positive使用五欄source brief。結果：

- exactly one replacement brief/state；
- replacement state `active`；
- replacement brief canonical四欄，沒有`lane`；
- source raw五欄brief與terminal registry bytes before==after；
- replacement沒有attempts或matching outbox；
- immediate second execute回同一identity `already_exists`；
- second execute後全fixture bytes與first execute後相同；
- runner/provider/publisher沒有被呼叫。

### Negative authority closure：PASS

Exact suite涵蓋並拒絕：

- legacy brief wrong lane；
- unexpected sixth field；
- state routing drift；
- identity-envelope drift；
- source SHA、run ID、run dir與registry digest drift；
- nonfailed source與second replacement。

所有negative case structured rejected且全bytes before==after。

## Prior findings regression

### Consumed／complete／failed replacement：PASS

- attempt residue拒絕；
- complete／failed existing replacement拒絕；
- pristine active existing replacement才可idempotently `already_exists`。

### Identity lock／write-before drift：PASS

- execute lock內重跑完整preflight；
- registry在第一次read後漂移時，第二次locked read於helper前拒絕；
- replacement brief/state不存在。

### Orphan replacement residue：PASS

- state absent + orphan attempt，plan與execute拒絕；
- matching brief + state absent + orphan attempt，plan與execute拒絕；
- execute cases helper=0，bytes stable。

### Five queue buckets：PASS

Matching namespace出現在下列任一bucket均拒絕：

- outbox
- processing
- inbox
- archive
- failed

Shared root與四lane root都在掃描範圍，沒有EN或單一lane hardcode。

### Canonical／symlink：PASS

Source registry/run/brief與replacement run/brief/state authority維持canonical closure；source
run symlink與replacement target symlink均fail closed。

### Production-shaped terminal／isolation：PASS

Fixture具Gen01／02 Reviewer REJECT、Gen03
`PLANNING_CONTRACT_FAILURE / terminal_stage=PLANNING`、attempts exact 01／02／03與無Gen04。
KO、JA、四lane與publisher protected bytes包含在snapshot中。

## Spec axis

`PASS`

- Exact selector、plan／execute互斥、registry digest與run-dir authority成立。
- Plan-only對canonical與production legacy brief都zero-write。
- Execute只建立fresh canonical replacement，不consume、不推進semantic generation。
- Terminal Gen03 repair 2/2、source SHA、lineage與idempotency保持。
- Wrong legacy context、consumed／orphan／queue／path drift全部fail closed。
- Automatic cycle default與existing helper semantics未改。

## Standards axis

`PASS`

- Correctness：production acceptance finding與歷次review findings全關閉。
- Regression：exact、affected、selector/reason與helper suites全綠。
- Security：trusted-state normalization保持closed authority；global validator未放寬。
- Maintainability：唯一coordinator source seam；沒有duplicate loader、registry、FSM、DB或
  second authority。
- Testing：canonical與legacy positive、execute canonical output、negative legacy context、
  bytes isolation與舊findings全部有exact fixture。

## 獨立驗證

於clean worktree執行：

```text
exact replacement positive/negative/idempotency:
30 passed, 387 deselected

card affected replacement slice:
33 passed, 384 deselected

existing exact selector + closed replacement reason:
12 passed, 405 deselected

existing multilingual enqueue helper:
2 passed, 276 deselected

py_compile scripts/agy_gemini_coordinator.py:
PASS

git diff --check (source/test/implementation RESULT):
PASS
```

## Allowlist／LOC seal

Clean worktree current diff只有：

- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`
- `PANTHEON-FOUR-LANE-EXACT-REPLACEMENT-PLAN-ONLY-REPAIR-20260830/RESULT.md`

Repair累計diff相對accepted f456 base，亦等於D7B parent加current fix：

```text
119  1  scripts/agy_gemini_coordinator.py
260  0  tests/test_agy_gemini_coordinator.py
```

- source exactly 1、test exactly 1；符合allowlist。
- source `119/1`低於`120/20` ceiling。
- test `260/0`等於`260/20` ceiling。
- multilingual helper、runner、publisher、shared validator diff=0。
- `second_source_seam=false`。

## Remaining risk

- Full coordinator file既有campaign schema drift與launchd installer hang仍未被本candidate
  修復；其stack不進exact replacement seam，不阻塞本bounded GO，但不得宣稱full suite
  PASS。
- Test LOC已達ceiling；接受前不得附加其他功能或scope。
- Production plan-only需在candidate接受、push與新promotion後重新執行；本review沒有用
  source worktree直接改production actor。

## Final gate

```text
status: GO
verdict: GO
spec_axis: PASS
standards_axis: PASS
production_fixture_gap_closed: true
blocking_findings: 0
source_files_changed: 1
test_files_changed: 1
second_source_seam: false
production_mutation: 0
provider_calls: 0
runner_calls: 0
publisher_calls: 0
commit: 0
push: 0
```

Candidate可回主線進行精確allowlist integration。後續promotion與production plan／execute
仍須由主線依正式authority重新驗收；本GO不直接授權任何production mutation。
