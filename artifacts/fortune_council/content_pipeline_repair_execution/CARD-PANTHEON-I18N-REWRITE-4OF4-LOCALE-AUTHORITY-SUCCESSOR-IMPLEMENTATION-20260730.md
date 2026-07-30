---
card_id: CARD-PANTHEON-I18N-REWRITE-4OF4-LOCALE-AUTHORITY-SUCCESSOR-IMPLEMENTATION-20260730
chain_id: pantheon-i18n-rewrite-4of4-locale-authority-successor-p0-20260730
parent_chain_id: pantheon-i18n-rewrite-4of4-runtime-stability-p0-20260730
parent_card_id: CARD-PANTHEON-I18N-REWRITE-4OF4-RUNTIME-STABILITY-P0-MAINLINE-20260730
role: implementation
cycle: 1
status: READY_TO_DISPATCH
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: locale authority validator 位於 provider 前的 fail-closed publication boundary，且前一 strict chain 已因 heuristic 例外耗盡兩代 Repair；新 chain 必須重新鎖定封閉契約、保留既有 continuation invariants，並接受獨立 Review。
project_id: c2xpbmdzaG90OmVudl9lXzZhMTdiMzc4MTg1ODgzMmRhZWU4Njk3YzMwZmM3ZTdjCi9Vc2Vycy9tYXR0a3VvL0RvY3VtZW50cy9QYW50aGVvbg==
legacy_project_binding: local-0020d4379451d545eb08362962f1def0
repo_identity: github.com/bluemaple18-home/Pantheon
required_base_ref: codex/pantheon-p0c-locale-authority-successor-base
required_base_sha: ce34670911a7c4691cb6a3cea851b7a805ff965e
source_candidate_sha: 488c3ca290cc62811100f5b73a6eb530f86c6634
source_review_evidence_sha: ce34670911a7c4691cb6a3cea851b7a805ff965e
mainline_thread_id: 019fb165-8174-7192-b19f-4ed19ed19426
ownership: successor implementation for the bounded locale-authority validator contract only
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-LOCALE-AUTHORITY-SUCCESSOR-IMPLEMENTATION-20260730/
created_at: 2026-07-30 Asia/Taipei
---

# Pantheon i18n-rewrite Locale Authority Successor Implementation

## Role and lineage

這是前一 strict chain 在 Repair-2 後仍 `REVIEW_NO_GO` 所建立的新 successor
Implementation chain。它不是 Repair-3、replacement 或重複 mainline。

基線 `ce34670911a7c4691cb6a3cea851b7a805ff965e` 包含：

- Repair-2 candidate
  `488c3ca290cc62811100f5b73a6eb530f86c6634`。
- 最終獨立 Review evidence 與
  `targeted_re_review_2_probes.py`。
- 已關閉的 `P0C-REREV-001` 與 `P0C-REV-003..006` 證據。

不得修改既有 Review evidence 或 probes 來讓結果變綠。完成後只交付一個
successor candidate，回主線建立新 chain 的獨立 Review。

## Root question

如何讓 ja／ko locale plan 的每個 semantic item 都具有可驗證的目標語言
authority，同時允許局部 proper noun、ASCII acronym、產品代碼與數字，而不再用
大小寫形狀或有限英文詞表把任意純英文句誤認為 entity？

## Confirmed current state

- `_plan_matches_target_language()` 已逐一驗證：
  - `native_search_intent`
  - 每一個 native query
  - `article_angle`
  - 每一個 H2
  - 每一個 coverage note
- 現存 P1 只在 item 內的 ASCII exception：
  `_ascii_is_name_acronym_or_number()`。
- `READERS EVALUATE SOURCES CAREFULLY` 因每個 word 都是 uppercase，被 ja／ko
  錯誤接受；相同字串放入上述五類欄位，ja／ko 共十個獨立 probe 均失敗。
- 最終 positive probe 已證明合法日文純漢字 H2 `実践方法` 通過；它不是本卡
  blocker，必須保持通過。
- Prompt canonical identity 已關閉，不得重新設計或擾動。

## Required design contract

### LA-SL-01 — Red-capable direct contract

在改 production code 前，先把現有 final Review probe 的十個 failure 重現為 RED，
並在 direct multilingual tests 建立不依賴特定英文單字的 adversarial matrix：

1. ja／ko 的五類 semantic item，各自拒絕任意多詞 ASCII-only 一般句。
2. 變換大小寫、Title Case、未知一般詞與多個大寫詞後仍拒絕。
3. 其他母語欄位不得掩護錯語言 item。
4. 日文純漢字 H2、自然日文與自然韓文保持接受。
5. 目標語言文字內的局部 proper noun、ASCII acronym、產品代碼與數字保持接受。
6. 若允許整個 item 為 ASCII-only，例外必須是封閉、可解釋且具長度／token
   topology 邊界的單一 entity／acronym／model code／number；不得用一般詞表、
   `isupper()` 或 Title Case 多詞形狀推斷任意 entity。

### LA-SL-02 — Minimal closed validator

只在現有 per-item seam 做最小修復：

1. 移除「有限一般英文詞表 + capitalization shape」作為多詞 entity 判定 authority。
2. ja／ko 的句子型 semantic item 必須包含目標語言 authority；局部 ASCII literal
   不能取代整個 item。
3. ASCII-only 例外只接受封閉 token contract，例如數字、短 acronym、model／產品
   code；一般多詞句一律 fail closed。
4. 不新增外部語言套件，不把 provider 或 Reviewer 變成 deterministic gate 的前置
   依賴。
5. 保留 en 的既有目標語言行為與 ja 純漢字 positive。

不要以擴充 `GENERAL_ENGLISH_WORDS`、加入本次 probe 單字或另一個更大的 stop-word
list 修補。

### LA-SL-03 — Regression preservation

下列既有契約不得回歸：

- canonical plan prompt／request identity 與 pending replay idempotency。
- continuation generation／root transaction recovery。
- repeated finding outline rebuild topology。
- source fact coverage、source structure blacklist與article hydration。
- deterministic、Reviewer、SEO、canonical、安全與publication gates。

## Allowlist

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- 本卡專屬 evidence／handoff

若 RED 證據顯示必須變更 schema 或其他 production module，立即停止並回報
`BLOCKED_SCOPE`；不得自行擴張 allowlist。

## Forbidden scope

- 不修改既有 Implementation、Review、Repair 或 targeted re-review
  evidence／probes。
- 不降低或繞過 deterministic、Reviewer、SEO、canonical、安全或 publication
  gate。
- 不修改 Writer／Reviewer prompt authority、Outbox identity、transport retry、
  Publisher runtime manifest 或 ledger ordering。
- 不手改 production candidate、review、queue、approval、apply、publish或ledger。
- 不修改 frontend、registry、sitemap、feed、redirect或生成文章。
- 不呼叫 provider、不讀寫 production `.work`、不push、不deploy、不publish。
- 不建立 Repair、Review、replacement或其他 task；不使用 hidden sub-agent。

## Required workflow

1. 驗證 formal thread、project binding、獨立 clean worktree、exact base SHA 與無
   `index.lock`。
2. 跑 worktree capability preflight；source decision 前使用 CodeGraph，失敗才以
   限域 `rg` 降級並保存原因。
3. 先完成 LA-SL-01 RED，再做 LA-SL-02 最小修復。
4. 執行 LA-SL-03 regressions、完整受影響 suites與 `git diff --check`。
5. 建立單一 candidate commit；不得 merge、push或自行宣稱 Review GO。

## Verification

至少 fresh 執行：

```text
<existing-venv-python> -m pytest \
  artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REVIEW-20260730/targeted_re_review_2_probes.py -q

<existing-venv-python> -m pytest \
  tests/test_agy_multilingual_pipeline.py -q

<existing-venv-python> -m pytest \
  artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REVIEW-20260730/adversarial_review_tests.py \
  artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REVIEW-20260730/targeted_re_review_probes.py \
  artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REVIEW-20260730/targeted_re_review_2_probes.py -q

<existing-venv-python> -m pytest \
  tests/test_agy_multilingual_pipeline.py \
  tests/test_agy_gemini_outbox.py \
  tests/test_agy_seo_copy_pipeline.py \
  tests/test_agy_content_publisher.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_gemini_v4_broker.py \
  tests/test_agy_gemini_reviewer_cutover.py -q

git diff --check
```

另驗證：

- changed files 完全落在 allowlist。
- production Python 可編譯。
- `rg '\\[DBG-'` 無 debug instrumentation。
- candidate direct parent 精確為 required base。
- candidate commit 後 worktree clean。

## Evidence contract

在本卡 evidence path 保存：

- `preflight.md`
- `source-map.md`
- `red-green.md`
- `verification.txt`
- `implementation-evidence.md`
- `handoff.md`

不得寫入 credentials、raw provider payload、production內容或本機絕對路徑。

## Delivery

狀態只能回：

`DELIVERED_SUCCESSOR_CANDIDATE`

並附：

- candidate SHA與direct parent
- LA-SL-01 RED→GREEN證據
- 最終 Review probe disposition
- 已關閉 findings regression結果
- changed files與allowlist
- fresh tests、`git diff --check`與worktree clean證據
- residual risks與所有未執行的外部／production actions

完成後停止，回主線等待獨立 Review；不得自行整合或繼續 production。
