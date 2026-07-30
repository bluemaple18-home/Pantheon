---
card_id: CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-IMPLEMENTATION-20260730
chain_id: pantheon-i18n-rewrite-4of4-runtime-stability-p0-20260730
parent_card_id: CARD-PANTHEON-I18N-REWRITE-4OF4-RUNTIME-STABILITY-P0-MAINLINE-20260730
role: implementation
cycle: 2
status: CARD_DRAFTED
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: P0-C 涉及多語 prompt authority、兩階段 provider artifact、既有 production lineage continuation與 semantic repair budget；錯誤會生成異題內容或手動污染 production state，需 strict 實作與獨立 Review。
project_id: local-0020d4379451d545eb08362962f1def0
repo_identity: github.com/bluemaple18-home/Pantheon
required_parent_base_ref: codex/pantheon-i18n-runtime-stability-mainline
required_parent_base_sha: 88bb43c07061532ba0669cf033a88f0561e1e347
ownership: P0-C native locale planning, repeated-finding outline rebuild, and deferred-run continuation
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-IMPLEMENTATION-20260730/
created_at: 2026-07-30 Asia/Taipei
---

# Pantheon i18n-rewrite Native Outline Continuation

## Root question

如何讓既有 `fortune-0039` deferred translation run在不手改 candidate／review／queue／
ledger的前提下，依法建立新的 locale-specific search-intent與 outline generation，
再以 source fact package原生重寫，讓 repeated Reviewer findings真正重建結構而非
句面替換？

本卡只實作與測試 repo契約，不呼叫真實 provider、不修改 production `.work`、
不 push、deploy、publish或安裝 LaunchAgent。

## Confirmed source gap

- `LOCALE_EDITORIAL_CONTRACTS` 目前把 en／ja／ko audience、structure與 SEO 全部
  硬寫成 Tarot card meanings；`fortune-0039` 實際主題是八字「用神」。
- `_writer_prompt()` 雖說「從零重寫」，但沒有 schema-valid locale plan artifact；
  文章生成仍直接看到完整 source結構。
- `run_writer_reviewer()` 固定使用 `attempts/01..03`。三個 deferred production runs
  已有完整 01..03 artifacts，再執行只會重讀舊 external candidate／review，
  無法建立合法新 generation。
- Production runs必須保留原 run ID、brief、candidate／review lineage與既有
  findings；不得刪檔、覆蓋 attempt或人工編稿。

## Requirements

### P0C-FR-001 — Topic-neutral locale authority

- 移除 Tarot-specific audience、SEO keywords與 fixed outline。
- Locale contract只保留各語言的母語 voice、syntax、search phrasing規則與禁止項。
- Topic、query intent與 outline必須從當前 source fact package產生；不得由 shared
  constant預設文章主題。

### P0C-FR-002 — Two-phase plan then article

- 每一個 semantic attempt先產生 schema-valid、sanitized locale plan artifact，
  至少包含：
  - locale；
  - native search intent／query phrasing；
  - article angle；
  - ordered H2 outline；
  - source fact／safety coverage mapping；
  - source structure elements explicitly not copied。
- Article Writer只接收 source fact package、locale contract與已驗證 plan；不得把
  source H2／段落數／敘事順序當 outline。
- Plan與article operation各有獨立 receipt與 idempotent artifact path。

### P0C-FR-003 — Repeated finding rebuild

- Reviewer finding驅動 targeted repair。
- 若同一 machine／Reviewer finding code跨連續 generation重複，下一次必須建立
  `rebuild_outline=true` 的新 plan，並明確禁止沿用上一 plan的 heading order與
  section topology。
- 不能只改句面或把相同 outline換同義詞。

### P0C-FR-004 — Existing deferred lineage continuation

- 提供 deterministic continuation入口，沿用既有 run ID／brief／source hash與
  final REJECT findings。
- 既有 `attempts/01..03` immutable；新工作寫入唯一、遞增且可重放的 generation／
  attempt path，不覆蓋舊 artifacts。
- Continuation有 bounded semantic budget、stable operation identity與狀態檔，
  重跑不得重複建立 provider request。
- Root candidate／review只有在新 generation完成後由 pipeline原子更新；未取得
  schema-valid payload、pending或transport failure時不前進 semantic generation。
- 不得建立 approval／apply／publish／ledger副作用。

## Production lineage fixtures

測試使用 synthetic copies模擬下列真實狀態，不得讀寫真實 `.work`：

- `auto-i18n-en-41190e6915d8a7f145f4`
  - `AI_TEMPLATE_STYLE`
  - `SOURCE_SYNTAX_TRANSFER`
- `auto-i18n-ja-d3752bcf0390126bdb3a`
  - `LITERAL_TRANSLATION`
  - `SOURCE_SYNTAX_TRANSFER`
  - `AI_TEMPLATE_STYLE`
- `auto-i18n-ko-149a513358e0e81cadcd`
  - `NON_NATIVE_SEARCH_INTENT`
  - `AI_TEMPLATE_STYLE`

優先驗證 ko continuation，因 finding最少；實作不得綁死單一 locale或 run ID。

## Allowlist

- `scripts/agy_multilingual_pipeline.py`
- `scripts/agy_gemini_outbox.py`，僅在 continuation routing確實需要時
- 直接受影響的 `tests/test_agy_multilingual_pipeline.py`
- 直接受影響的 `tests/test_agy_gemini_outbox.py`
- 本卡專屬 evidence／handoff

## Forbidden scope

- 不修改 deterministic、Reviewer、SEO、canonical、安全或 publication gate。
- 不手改或讀寫真實 production candidate、review、queue、approval、apply、
  publish、ledger。
- 不人工撰寫最終 en／ja／ko文章。
- 不修改 frontend、article registry、sitemap、feed、redirects。
- 不呼叫 provider、不 push、不 deploy、不 publish。
- 不改 P0-A runtime manifest或 P0-B retry taxonomy／budget。
- 不建立 Review、Repair、replacement或其他 task；完成後只回主線。
- 不使用 hidden sub-agent。

## Required RED scenarios

1. Non-Tarot source的 locale plan／article prompt不得出現 Tarot-specific intent、
   keywords或 outline。
2. Writer article phase缺 plan、plan schema invalid、locale/source hash不符時
   fail closed且不建立 candidate。
3. Repeated `AI_TEMPLATE_STYLE`／`SOURCE_SYNTAX_TRANSFER`／
   `NON_NATIVE_SEARCH_INTENT` 觸發 outline rebuild，plan topology不可沿用。
4. Existing attempts 01..03的 deferred run continuation建立唯一下一 generation，
   保留原 artifacts與 run identity。
5. Pending／transport／schema failure不前進 semantic generation、不覆寫 root
   candidate／review、不建立 approval／publish side effects。
6. 重跑相同 continuation operation維持相同 request identity且不重複 enqueue。

## Verification

至少 fresh執行：

```text
.venv/bin/python -m pytest \
  tests/test_agy_multilingual_pipeline.py \
  tests/test_agy_gemini_outbox.py \
  tests/test_agy_seo_copy_pipeline.py \
  tests/test_agy_content_publisher.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_gemini_v4_broker.py \
  tests/test_agy_gemini_reviewer_cutover.py -q
git diff --check
```

Changed files必須完全落在 allowlist。形成單一 candidate commit與完整
RED／GREEN evidence，狀態只能是 `DELIVERED_CANDIDATE`。

## Delivery format

- Candidate commit SHA與direct parent
- Changed files
- P0C-FR-001..004 acceptance mapping
- RED→GREEN與fresh suite結果
- `git diff --check`
- Remaining risks與未執行的 production actions
