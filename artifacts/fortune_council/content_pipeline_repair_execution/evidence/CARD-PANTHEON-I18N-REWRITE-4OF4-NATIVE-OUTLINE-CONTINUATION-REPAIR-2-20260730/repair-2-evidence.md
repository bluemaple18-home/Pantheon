# Native Outline Continuation Repair-2 Evidence

- card: `CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REPAIR-2-20260730`
- chain: `pantheon-i18n-rewrite-4of4-runtime-stability-p0-20260730`
- role: `repair`
- cycle: `2`
- repair cycle: `2`
- status: `DELIVERED_REPAIR_2_CANDIDATE`
- direct parent: `5d75d1802e379e022ae5682fd9d6ebe019d804f6`
- Repair-1 candidate: `bcb1ae53215996a9d4504bdb3247e1090afbb3ee`
- targeted re-review evidence commit: `5d75d1802e379e022ae5682fd9d6ebe019d804f6`
- formal thread: `019fb1d1-f44f-7401-8f8f-78c6e4ddbc26`
- context: `CONTEXT_DEGRADED`（CodeGraph 未在本 worktree 初始化；依契約降級為 allowlist 限域 source、direct tests 與 Review probes）

## R2-SL-01 — Canonical structured prompt replay

### RED

Targeted probe與新增direct test均重現later-generation plan pending replay的完整
prompt bytes漂移：

- first pending prompt SHA-256:
  `88e6edf489bb5c4dc7032143a879b1a81602701495829b71e481cb2584ff90bb`
- replay prompt SHA-256:
  `7ac643c7478d6cc83e1a60d03b62e4c49dad712513664062ab92351cae084acb`

差異只位於generation 04 `prior_plan`：第一次使用in-memory insertion order，
replay使用persisted sorted-key JSON order。

### Repair

- 新增單一`_canonical_json()`，直接沿用既有`compact_json_bytes()`的
  sorted-key／compact separators／UTF-8規則。
- plan prompt中的locale contracts、source fact package、structure blacklist、
  prior plan、findings與rebuild authority全部使用同一canonical serialization。
- 未修改Outbox request identity算法或Outbox production/tests。

### GREEN

- direct test證明兩次完整prompt bytes與prompt SHA完全相同。
- generation 05只保留一個`plan-operation.json`，沒有runtime retry operation，
  沒有`external-plan.json`，state維持completed `[4]`／next `5`。
- root candidate／review不變，沒有前進generation或建立第二operation。
- targeted re-review replay probe轉為PASS。

Finding disposition：`P0C-REREV-001`已由Repair-2 candidate處理，等待原Reviewer
targeted re-review；本Repair不宣稱Review GO。

## R2-SL-02 — Per-field native authority gate

### RED

- targeted probe證明ko的native intent／queries／angle／coverage notes可替四個全英文
  H2墊高aggregate Hangul ratio。
- 新增15個direct cases，分別只替換en／ja／ko的單一critical item：
  `native_search_intent`、一個query、`article_angle`、一個H2或一個
  `coverage_note`；修復前全數未拋出錯誤。
- 另以ja／ko全大寫一般英文heading證明單純把大寫字視為acronym會誤放行。

### Repair

- locale authority改為逐item檢查，不再合併欄位計分。
- en要求單item English authority高於CJK；ja允許kana與現代日文漢字自然混合，
  也允許不含kana的短漢字heading，但拒絕全英文與繁中字形主導item；ko要求
  Hangul authority。
- ASCII-only例外只接受proper name、產品名、acronym或number形態；常見一般英文
  authority words即使全大寫也不視為acronym。
- `source_structure_not_copied`仍只作blacklist，不進母語判定。
- 未加入外部語言套件，未呼叫provider。

### GREEN

- per-field negative、native positive、proper name／product／acronym／number positive、
  日文純漢字短heading與全大寫一般英文negative共25個focused cases通過。
- targeted wrong-language outline probe轉為PASS。
- article phase前即fail closed，不會讓其他母語欄位掩護錯語言query／H2。

Finding disposition：`P0C-REREV-002`已由Repair-2 candidate處理，等待原Reviewer
targeted re-review；本Repair不宣稱Review GO。

## Preserved findings regression

- `P0C-REV-003`：root review final authority probe維持PASS。
- `P0C-REV-004`：active／terminal identity與root transaction recovery probes維持PASS。
- `P0C-REV-005`：`MIRRORED_STRUCTURE` consecutive／control與topology probes維持PASS。
- `P0C-REV-006`：attempt gap與future generation directory probes維持PASS。
- Repair-1 plan-pending與article-pending replay tests維持PASS。

## Fresh verification

Direct multilingual tests:

```text
<canonical-checkout>/.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py -q
```

Result: `64 passed in 0.12s`。

Original Review adversarial probes:

```text
<canonical-checkout>/.venv/bin/python -m pytest artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REVIEW-20260730/adversarial_review_tests.py -q
```

Result: `12 passed in 0.06s`。

Targeted re-review probes:

```text
<canonical-checkout>/.venv/bin/python -m pytest artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REVIEW-20260730/targeted_re_review_probes.py -q
```

Result: `3 passed in 0.04s`。

Required suite:

```text
<canonical-checkout>/.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py tests/test_agy_gemini_outbox.py tests/test_agy_seo_copy_pipeline.py tests/test_agy_content_publisher.py tests/test_agy_gemini_coordinator.py tests/test_agy_gemini_v4_broker.py tests/test_agy_gemini_reviewer_cutover.py -q
```

Result: `492 passed, 1 warning in 84.67s`。warning為既有
`test_preflight_test_command_selectors_resolve_to_top_level_tests` 的
`DeprecationWarning: invalid escape sequence '\/'`。

`git diff --check`: PASS。

`rg '\[DBG-'`: PASS，無debug instrumentation。

## Changed-file boundary

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- 本Repair-2專屬`repair-2-evidence.md`
- 本Repair-2專屬`handoff.md`

全部位於Repair-2 allowlist。未修改Outbox、既有Implementation／Review／targeted
re-review／Repair-1 evidence或probes，也未修改deterministic、Reviewer、SEO、
canonical、安全或publication gate。

## Residual risks and forbidden actions

- per-item validator是deterministic script／authority gate，不取代母語Reviewer對
  語意、自然度與品牌命名的判斷。
- 本Repair只使用synthetic fixtures；未呼叫provider、未讀寫production `.work`。
- 未建立production queue、approval、apply、publish、ledger、registry、sitemap、
  feed或redirect。
- 未push、deploy、publish或建立Review、replacement、sub-agent或其他task。
- 本candidate仍須同一原Reviewer做targeted re-review；本Repair不宣稱Review GO。
