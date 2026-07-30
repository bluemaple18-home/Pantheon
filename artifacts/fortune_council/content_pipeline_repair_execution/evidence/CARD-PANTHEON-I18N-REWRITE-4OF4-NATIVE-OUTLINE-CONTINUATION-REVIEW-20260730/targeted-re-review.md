# Native Outline Continuation Targeted Re-Review

- chain: `pantheon-i18n-rewrite-4of4-runtime-stability-p0-20260730`
- role: `original independent reviewer`
- review cycle: `2`
- repair budget used: `1`
- verdict: `REVIEW_NO_GO`
- repair candidate: `bcb1ae53215996a9d4504bdb3247e1090afbb3ee`
- required direct parent: `cc76cce1eb713ab6e1cf202392b7f4ae35c62071`
- original reviewed candidate: `f0b70b4bba41a952f9b8bc2c12d3a2bc5c13502e`
- original Review evidence commit: `cc76cce1eb713ab6e1cf202392b7f4ae35c62071`
- repair thread: `019fb1d1-f44f-7401-8f8f-78c6e4ddbc26`
- original Review thread: `019fb1c4-9a1b-7831-a8f5-16d38db5992a`

## Context receipt

- Repair candidate存在，direct parent精確等於原 Review evidence commit；本獨立
  worktree已detached到repair candidate，開工前clean。
- Repair diff只有`agy_multilingual_pipeline.py`、對應direct tests與Repair專屬
  evidence／handoff，沒有hidden generated或environment file。
- CodeGraph status／context query仍回報本worktree未初始化。因targeted re-review
  只允許在原Review evidence目錄新增證據，未執行會在該路徑外建立`.codegraph`
  的prepare；標記`CONTEXT_DEGRADED`並限域review repair diff、direct tests、
  原probes與production caller。

## Original finding dispositions

### P0C-REV-001 — NOT CLOSED

已關閉部分：

- generation 04 rebuild plan成功、article pending後，replay不再把generation 04
  plan與自己比較。
- 原Review article-pending probe與第一個continuation generation的plan-pending
  probe均通過；root candidate／review不變，generation不前進。

仍阻擋：

- generation 04完成REJECT後，同一process首次建立generation 05 plan prompt時，
  `prior_plan`是in-memory dict；plan pending後重跑，`prior_plan`改由sorted-key
  JSON artifact載入。
- `_plan_prompt()`在`scripts/agy_multilingual_pipeline.py:784`使用未排序的
  `json.dumps(prior_plan)`，兩次logical replay的prompt SHA-256分別為：
  - `88e6edf489bb5c4dc7032143a879b1a81602701495829b71e481cb2584ff90bb`
  - `7ac643c7478d6cc83e1a60d03b62e4c49dad712513664062ab92351cae084acb`
- Outbox request identity因此漂移；後續generation的plan-pending仍可能建立第二個
  request／enqueue，違反bounded idempotency。

Disposition：`UNRESOLVED_P1`，對應新 finding `P0C-REREV-001`。

### P0C-REV-002 — NOT CLOSED

已關閉部分：

- en全CJK semantic fields、ja／ko全英文或繁中semantic fields會被拒絕。
- direct native en／ja／ko fixtures、proper names、ASCII acronyms與numbers通過。
- `source_structure_not_copied`未進入語言判定。

仍阻擋：

- `scripts/agy_multilingual_pipeline.py:687-695`把intent、queries、angle、H2與
  coverage notes合併後只做一次aggregate script ratio。
- 韓文intent／queries／angle／coverage notes可替四個全英文H2墊高Hangul count，
  validator接受整份plan；article phase又必須逐字沿用英文H2。
- 這不是proper noun或acronym例外，而是critical outline authority完整使用錯誤
  語言，仍會先消耗article provider／semantic budget。

Disposition：`UNRESOLVED_P1`，對應新 finding `P0C-REREV-002`。

### P0C-REV-003 — CLOSED

- 第一continuation generation現在固定以已驗證root `review.json`作最後finding
  authority；attempt history只在它之前提供repeat detection。
- 原Review root-only marker probe已由failure轉為PASS，root-only deterministic／
  Reviewer finding會進入第一個plan prompt。

Disposition：`CLOSED`。

### P0C-REV-004 — CLOSED

- active state驗證starting review且terminal hashes必須為null。
- complete state鎖terminal candidate／review SHA-256；candidate與review一起漂移
  仍fail closed，且complete replay不呼叫client。
- 原Review transaction/candidate/review/state atomic write與unlink interruption
  probes全部通過；recovery會先驗證terminal payload hashes。

Disposition：`CLOSED`。

### P0C-REV-005 — CLOSED

- `MIRRORED_STRUCTURE`已進closed rebuild code set。
- 同article consecutive會rebuild；cross-article與non-consecutive controls不會。
- 原Review synonym heading／same fact topology probe通過。

Disposition：`CLOSED`。

### P0C-REV-006 — CLOSED

- attempts必須從`01`開始contiguous，原gap probe通過。
- state的completed／next generation與generation directories會一起驗證。
- targeted future `generations/09` probe成功fail closed。

Disposition：`CLOSED`。

## New findings

### P0C-REREV-001 — P1 — later-generation plan replay request identity仍漂移

- category: correctness / idempotency / lineage
- file: `scripts/agy_multilingual_pipeline.py:784`
- evidence: `targeted_re_review_probes.py::test_later_generation_plan_pending_replay_keeps_prompt_identity`
- concrete failure path: 一個repair generation完成後立即enqueue下一generation plan；
  首次prompt使用in-memory prior plan，pending replay改用persisted sorted-key prior
  plan，未canonicalize的JSON序列化令prompt hash與Outbox job identity改變。
- violated requirement: P0C-REV-001要求plan pending同logical continuation不得
  enqueue兩次或漂移request identity。
- minimal repair direction: plan prompt中所有structured fragments至少以canonical
  sorted-key serialization輸出，並加入「前一generation完成後，下一generation
  plan pending再replay」的request／job ID regression test。
- confidence: high

### P0C-REREV-002 — P1 — aggregate locale gate可由其他欄位掩護錯語言H2

- category: correctness / prompt authority
- file: `scripts/agy_multilingual_pipeline.py:687`
- evidence: `targeted_re_review_probes.py::test_locale_gate_rejects_wrong_language_outline_when_other_fields_are_native`
- concrete failure path: ko plan保留母語intent、queries、angle與coverage notes，但
  四個ordered H2全部為英文；aggregate Hangul count仍令plan通過，article被迫使用
  英文section authority。
- violated requirement: P0C-REV-002要求locale-specific native plan且non-native
  plan在article phase前fail closed。
- minimal repair direction: 對critical field groups／list items分別驗證目標語言，
  尤其每個H2與query；proper noun、ASCII acronym、number只作局部容許，不能以其他
  欄位的目標文字替整欄錯語言內容墊分。
- confidence: high

沒有新增P0、P2或P3 finding。

## Fresh verification

### Required suite

```text
<existing-venv-python> -m pytest tests/test_agy_multilingual_pipeline.py tests/test_agy_gemini_outbox.py tests/test_agy_seo_copy_pipeline.py tests/test_agy_content_publisher.py tests/test_agy_gemini_coordinator.py tests/test_agy_gemini_v4_broker.py tests/test_agy_gemini_reviewer_cutover.py -q
```

結果：`474 passed, 1 warning in 85.81s`。warning是既有
`test_preflight_test_command_selectors_resolve_to_top_level_tests` 的
`DeprecationWarning: invalid escape sequence '\/'`。

### Original Review adversarial probes

```text
<existing-venv-python> -m pytest artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REVIEW-20260730/adversarial_review_tests.py -q
```

結果：`12 passed in 0.07s`。

### Targeted re-review probes

```text
<existing-venv-python> -m pytest artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REVIEW-20260730/targeted_re_review_probes.py -q
```

結果：`2 failed, 1 passed in 0.06s`。

- 兩個failure是以targeted requirement為expected behavior的可重現P1 findings。
- 一個pass證明已存在future generation directory會fail closed。

### Repair diff check

```text
git diff --check cc76cce1eb713ab6e1cf202392b7f4ae35c62071 bcb1ae53215996a9d4504bdb3247e1090afbb3ee
```

結果：PASS，無輸出。

## Stop boundary

- 未修改production code、direct tests、Implementation evidence、原Review evidence
  或Repair evidence；只新增本cycle專屬targeted re-review evidence／probes。
- 未呼叫provider、未讀寫production `.work`、未建立queue／approval／apply／
  publish／ledger／registry／sitemap／feed／redirect。
- 未push、deploy、publish、修復candidate或建立新task／replacement／第二Reviewer。

## Verdict

`REVIEW_NO_GO`

`P0C-REV-001`與`P0C-REV-002`仍各有一條可重現P1 failure path；其餘四筆原
finding已關閉。
