# Native Outline Continuation Implementation Evidence

- card: `CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-IMPLEMENTATION-20260730`
- chain: `pantheon-i18n-rewrite-4of4-runtime-stability-p0-20260730`
- role: implementation
- cycle: 2
- status: `DELIVERED_CANDIDATE`
- direct parent: `8bb80b888561b1a06afa9550f535f6e865724871`
- context: `CONTEXT_DEGRADED`（CodeGraph 未在本 worktree 初始化；依契約降級為 allowlist 限域原始碼查找）

## Acceptance mapping

### P0C-FR-001 — Topic-neutral locale authority

- `LOCALE_EDITORIAL_CONTRACTS` 只保留 en／ja／ko 的 voice、syntax、native search phrasing 與 avoid 規則。
- 移除 Tarot audience、keywords 與 fixed outline；topic、query intent 與 H2 改由當次 source fact package 產生。
- non-Tarot 八字「用神」fixture 驗證三個 locale 的 plan／article prompt 均不含 Tarot-specific intent 或 keywords。

### P0C-FR-002 — Two-phase plan then article

- 每個 semantic generation 先建立 strict locale-plan schema，再建立 article；兩階段分別使用 `plan-operation.json`／`article-operation.json` receipt 與各自的 external output。
- plan artifact 綁定 run、generation、locale、source hash、native intent/query、angle、ordered H2、逐 fact safety coverage、source topology blacklist 與 rebuild authority。
- article prompt 只接收去除來源 H2／段落拓撲且以 fact ID 排序的 source fact package、locale contract 與 validated plan。
- article H2 必須逐項等於 plan 的 ordered outline；缺 plan、schema drift、locale/source hash drift 或 coverage drift 均在 candidate 前 fail closed。

### P0C-FR-003 — Repeated finding rebuild

- 連續兩個 generation 的同 article finding code 取交集；`AI_TEMPLATE_STYLE`、`SOURCE_SYNTAX_TRANSFER`、`NON_NATIVE_SEARCH_INTENT` 觸發下一代 `rebuild_outline=true`。
- rebuild plan 會收到前一 plan／既有 rejected candidate topology；validator 同時比較 heading order 與逐 fact section grouping，禁止只換同義 heading 而沿用相同 topology。
- targeted repair 只傳 findings，不再把前一篇 article 全文交回 Writer，避免句面替換。

### P0C-FR-004 — Existing deferred lineage continuation

- `continue_writer_reviewer()` 建立 stable operation ID、bounded semantic budget、`next_generation`／`completed_generations` 狀態檔。
- 既有 `attempts/01..03` 唯讀保留；新工作寫入 `generations/04..`，沿用 run ID、brief、source hash與 final REJECT findings。
- pending／transport／invalid plan 不前進 generation、不覆寫 root candidate／review；同一 pending operation 重跑維持相同 prompt/request identity且 queue 僅一筆。
- root candidate／review 只在新 generation完成且 continuation達到 APPROVE或 bounded終點後更新；write-ahead root transaction使中斷後可重放，再以 atomic file replacement寫 candidate、review與完成 state。未建立 approval／apply／publish／ledger副作用。

## RED evidence

Command:

```text
.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py -q -k 'topic_neutral or article_phase or repeated_native or deferred_lineage or pending_continuation or writer_prompt'
```

Result: `8 failed`。失敗點證明 base 尚無 source fact package、locale plan schema／artifact、plan-gated article prompt、rebuild topology與 continuation入口；既有 runner也不會建立 `locale-plan.json` 或 `generations/04`。

## GREEN and regression evidence

Focused GREEN:

```text
.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py tests/test_agy_gemini_outbox.py -q -k 'locale_plan or article_phase or invalid_generated_plan or outline_rebuild or repeated_native or deferred_lineage or pending_continuation or root_update or translation_continuation_pending'
```

Result: `13 passed, 163 deselected in 0.09s`。

Fresh required suite:

```text
.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py tests/test_agy_gemini_outbox.py tests/test_agy_seo_copy_pipeline.py tests/test_agy_content_publisher.py tests/test_agy_gemini_coordinator.py tests/test_agy_gemini_v4_broker.py tests/test_agy_gemini_reviewer_cutover.py -q
```

Result: `460 passed, 1 warning in 82.49s`。warning 是既有
`test_preflight_test_command_selectors_resolve_to_top_level_tests` 的
`SyntaxWarning: invalid escape sequence '\/'`。

## Changed-file boundary

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- `tests/test_agy_gemini_outbox.py`
- 本 evidence
- 本卡 `handoff.md`

全部位於卡片 allowlist；未修改 outbox retry taxonomy／budget、deterministic gate、
Reviewer contract、SEO、canonical、安全或 publication gate。

## Remaining risk and forbidden production actions

- 本卡只用 synthetic fixtures；未讀寫 production `.work`，未呼叫真實 provider。
- 未人工撰寫 en／ja／ko 最終文章，未建立 production queue、approval、apply、publish 或 ledger 紀錄。
- 未 push、deploy、publish，未安裝 LaunchAgent。
- candidate 仍需主線安排獨立 Review；本 implementation thread 不建立 Review／Repair task。
