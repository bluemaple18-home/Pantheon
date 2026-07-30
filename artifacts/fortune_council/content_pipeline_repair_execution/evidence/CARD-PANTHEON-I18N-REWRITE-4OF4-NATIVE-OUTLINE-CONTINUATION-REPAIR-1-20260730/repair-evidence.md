# Native Outline Continuation Repair-1 Evidence

- card: `CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REPAIR-1-20260730`
- chain: `pantheon-i18n-rewrite-4of4-runtime-stability-p0-20260730`
- role: `repair`
- cycle: `2`
- repair cycle: `1`
- status: `DELIVERED_REPAIR_CANDIDATE`
- direct parent: `cc76cce1eb713ab6e1cf202392b7f4ae35c62071`
- reviewed candidate: `f0b70b4bba41a952f9b8bc2c12d3a2bc5c13502e`
- review evidence commit: `cc76cce1eb713ab6e1cf202392b7f4ae35c62071`
- formal thread: `019fb1d1-f44f-7401-8f8f-78c6e4ddbc26`
- context: `CONTEXT_DEGRADED`（CodeGraph 未在本 worktree 初始化；依契約降級為 allowlist 限域 source、tests 與 evidence 查找）

## Finding mapping

### P0C-REV-001 — pending rebuild article replay

- prior plan lookup 只接受 `state.next_generation` 之前的完成 generation，不再把當前 pending generation 的 plan 與自己比較。
- article input 改用 canonical sorted-key serialization，讓首次 in-memory plan 與 replay persisted plan 產生相同 request identity。
- direct tests同時鎖定 plan-pending 與 article-pending：不前進 generation、不重寫 roots、article request prompt identity不漂移。

### P0C-REV-002 — non-native locale plan

- `native_search_intent`、native query phrases、article angle、ordered H2 與 coverage notes 統一進入 locale-aware Unicode script-ratio validation。
- `ja`／`ko` 拒絕全英文與繁中主導 semantic plan；`en` 拒絕 CJK 主導 semantic plan。
- `source_structure_not_copied` 明確不進入語言判定；proper noun、ASCII acronym與number可與足量目標語言共存。
- direct en／ja／ko 正向與反向 fixtures均通過；未加入外部語言套件或 provider判定。

### P0C-REV-003 — root review authority

- continuation finding history固定排序為 `legacy attempts → verified root review → continuation generations`。
- 第一 continuation generation以root final review為最後 authority；後續 generation仍由最新完成 generation接手。
- direct root-only marker已證明進入第一個plan repair prompt，deterministic／Reviewer root findings不再被attempt history蓋過。

### P0C-REV-004 — complete replay identity drift

- continuation state新增terminal candidate／review SHA-256；active state要求terminal hashes為null並持續核對starting review。
- complete state要求root candidate／review精確符合terminal hashes；合法地一起替換candidate與review仍會fail closed。
- root write-ahead transaction寫入terminal identity；recovery在改寫roots前先驗證transaction payload hashes。
- complete replay維持零client call；transaction interruption與unlink recovery probes均通過。

### P0C-REV-005 — repeated MIRRORED_STRUCTURE

- `MIRRORED_STRUCTURE` 已加入closed rebuild-code policy。
- 同article consecutive finding觸發rebuild；cross-article與non-consecutive controls不觸發。
- 既有topology validator仍拒絕只換同義heading但沿用相同fact grouping。

### P0C-REV-006 — attempts gap

- 已一併修復，無 residual P2。
- 建立或載入state前，attempt目錄必須精確為從`01`開始的連續兩位數序列。
- `completed_generations`、`next_generation`與generation目錄必須一致；active state只額外允許唯一一個pending next-generation目錄。

## RED evidence

- pending rebuild article replay：direct與Review probe均重現
  `locale plan rebuild reused prior outline topology`。
- wrong-script plan：direct五個wrong-script cases與Review probe均重現「未拋出ValueError」。
- root review authority：direct與Review probe均證明plan prompt缺少
  `ROOT-REVIEW-AUTHORITY-MARKER`。
- complete identity drift：direct與Review probe均證明drifted roots可直接回放。
- repeated mirrored structure：direct與Review probe均證明rebuild authority為false。
- attempts gap：direct與Review probe均證明`01/03`或`01/03/04` lineage可建立state。

所有RED命令都觸及目標症狀；沒有import、fixture或environment failure。

## Fresh verification

Direct multilingual suite:

```text
<canonical-checkout>/.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py -q
```

Result: `46 passed in 0.11s`。

Required suite:

```text
<canonical-checkout>/.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py tests/test_agy_gemini_outbox.py tests/test_agy_seo_copy_pipeline.py tests/test_agy_content_publisher.py tests/test_agy_gemini_coordinator.py tests/test_agy_gemini_v4_broker.py tests/test_agy_gemini_reviewer_cutover.py -q
```

Result: `474 passed, 1 warning in 83.77s`。warning為既有
`test_preflight_test_command_selectors_resolve_to_top_level_tests` 的
`DeprecationWarning: invalid escape sequence '\/'`。

Review adversarial probes:

```text
<canonical-checkout>/.venv/bin/python -m pytest artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REVIEW-20260730/adversarial_review_tests.py -q
```

Result: `12 passed in 0.04s`。

`git diff --check`: PASS。

## Changed-file boundary

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- 本Repair專屬`repair-evidence.md`
- 本Repair專屬`handoff.md`

全部位於Repair allowlist。未修改outbox、既有Implementation／Review evidence、
Review adversarial probes、deterministic／Reviewer／SEO／canonical／安全或
publication gate。

## Residual risks and forbidden actions

- locale判定是deterministic script-ratio gate，不取代母語Reviewer對語意與文體的判斷。
- 本Repair只使用synthetic fixtures；未呼叫provider、未讀寫production `.work`。
- 未建立production queue、approval、apply、publish、ledger、registry、sitemap、
  feed或redirect。
- 未push、deploy、publish或建立Review、replacement、sub-agent或其他task。
- 本candidate仍需原Reviewer targeted re-review；本Repair不宣稱Review GO。
