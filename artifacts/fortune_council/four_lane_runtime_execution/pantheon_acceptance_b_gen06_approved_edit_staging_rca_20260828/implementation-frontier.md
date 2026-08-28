# Bounded Repair implementation frontier

## Decision

允許下一張且只能一張 bounded Repair：`approved edited candidate stage seal`。不在本 RCA 實作。

## Exact files／functions／CLI

### `scripts/agy_multilingual_pipeline.py`

- 新增 `plan_approved_edited_candidate_stage(...)`：唯讀驗證所有 input／current locks，回傳 deterministic `plan_digest` 與 `READY_TO_EXECUTE`。
- 新增 `apply_approved_edited_candidate_stage(..., expected_plan_digest)`：沿用 continuation run lock；只在 run dir 建立 `editorial-staging/<operation_id>/` 與最後寫入的 `editorial-staging/current.json` seal。
- 新增 `load_approved_edited_candidate_stage(...)`：驗證 current seal、payload SHA 與 terminal audit locks，供 publisher 使用。
- 新增 CLI `stage-approved-edited-candidate`；預設 plan-only，`--execute --expected-plan-digest` 才 apply。
- 不覆寫 root `candidate.json`／`review.json`、Gen06、continuation state或 queue registry；stage payload 使用獨立 candidate/review/formal-result copies。

### `scripts/agy_content_publisher.py`

- `collect_ready_translation_runs`：在既有 root clean-review path 之外，僅接受 `load_approved_edited_candidate_stage` 驗證通過的 current seal；stage 不得繞過 published/deferred ledger lifecycle。
- `publish_ready_translation_runs`：對 staged tuple 使用 staged candidate/review 建 approval/apply；成功 ledger entry 加 `staging_receipt_sha256`，既有 release transaction不拆、不改。
- 不新增 publisher CLI、不改 version/tag/push semantics。

### Tests

- `tests/test_agy_multilingual_pipeline.py`：plan read-only、exact positive、candidate/review/formal mismatch、stale root／Gen06／continuation／queue／ledger lock、plan digest drift、apply atomicity、same-input idempotence、conflicting second stage fail-closed、rollback receipt、Gen07 absence。
- `tests/test_agy_content_publisher.py`：valid seal可被 exact selector讀取、tamper/missing seal拒絕、deferred/published不可繞過、dry-run零 mutation、publish ledger綁 receipt digest、terminal Gen06 bytes保留。
- 本 RCA 的 `red_harness_missing_approved_edit_stage.py` 必須轉 GREEN。

## Required SHA locks

- run ID：`auto-i18n-ja-1414b75a404721e95e74`；terminal generation：`6`。
- approved candidate file：`6a77700f41bbc4e3ee274e8b018f694bb7912ab57c4f56df687a944e3c2f3d5c`；article：`a64d8a33b0b70933134452491c10058e820dd93d5c748d3cc220bbfc25da7b9c`。
- approved review file：`817c8507bee7a26b23dbad7b87871c6f5d043a2725ce133be7f9337540429c8b`；formal result：`8394f603d024d64019881c44457fd3fbd279d3854764e8ea3be624fdae80ff19`。
- current root candidate：`09aa9ea8187a5884dd255d8d51020c32bbad4a1747c6c6f86b50973e3630ecee`；root/Gen06 review：`4176d9306c5e49e5ab4bbd3860ed5eb2669c9490a506d20c4d7ef7e321bce3c9`。
- continuation state：`9b0b90943928d255454cab496dba502701e046446579a193820ac0205145818b`；queue registry：`397afcc959e1b8383541241fd3aed231e6b2545d6173b60155d8b8ed61d150ca`；publisher ledger：`0fc223530e1f8af7d0b495e28e4a336471a2349ceabd93074459827cbe93d8f9`。
- source article SHA：`1088d4dfae649824b9691d260e1754e528295a2b877a79a1d8e665054fe6db23`；actor SHA：`831c536043d85a6cafe813c08a4f06921f0dd0e2`。

## Audit／rollback／idempotence

- seal 必須含所有 input/current SHA、formal job identity、plan digest、operation id、created paths、before current-pointer digest、terminal Gen06 tree digest與 `provider_calls=0`。
- apply 先寫 immutable payload + rollback receipt，最後 atomic replace `current.json`；publisher只信 current seal。
- rollback receipt只允許刪除本 operation 建立的 stage並恢復 exact prior current pointer；不得碰 root／Gen06／continuation／queue／ledger。
- 相同 input + locks重跑回 `ALREADY_STAGED`；相同 run的不同 payload或任一 current drift fail closed。

## Minimum sufficient

- `why_not_less`：薄 wrapper、manual copy 或直接 `apply` 都缺 formal binding、current locks、atomic seal、rollback與 publisher reader contract。
- `why_not_more`：既有 publisher release transaction與 queue registry可沿用；不需要 Gen07、replacement run、campaign replay、promotion、database、registry或第二套 FSM。
- `do_not_absorb`：不把 staging泛化成 universal artifact system；不改 provider/coordinator；不清除 deferred history；不 publish/tag/push；不建立新 generation。
