---
card_id: CARD-PANTHEON-I18N-REWRITE-4OF4-LOCALE-AUTHORITY-SUCCESSOR-REPAIR-1-20260730
chain_id: pantheon-i18n-rewrite-4of4-locale-authority-successor-p0-20260730
parent_card_id: CARD-PANTHEON-I18N-REWRITE-4OF4-LOCALE-AUTHORITY-SUCCESSOR-REVIEW-20260730
role: repair
cycle: 1
status: READY_TO_DISPATCH
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 兩個 P1 均位於 provider 前的 deterministic publication boundary，且前一 chain 已因 heuristic 漏放耗盡兩代 Repair；本次雖為單檔 bounded repair，仍需以封閉 grammar 取代形狀推斷，避免再造第三套 bypass。
project_id: c2xpbmdzaG90OmVudl9lXzZhMTdiMzc4MTg1ODgzMmRhZWU4Njk3YzMwZmM3ZTdjCi9Vc2Vycy9tYXR0a3VvL0RvY3VtZW50cy9QYW50aGVvbg==
legacy_project_binding: local-0020d4379451d545eb08362962f1def0
repo_identity: github.com/bluemaple18-home/Pantheon
required_base_ref: codex/pantheon-p0c-locale-authority-successor-repair-1-base
required_base_sha: a5adb559e2f60ae5f8bd93183ec4aceaca7b78b7
reviewed_candidate_sha: 1f9b9359754d4f3959ee86afcb9d5c257605f9dd
review_evidence_commit: a5adb559e2f60ae5f8bd93183ec4aceaca7b78b7
review_thread_id: 019fb36b-25b3-7990-a4d7-fdb858fab6c6
implementation_thread_id: 019fb358-d09e-71e3-9ed0-f2bba14d6a16
mainline_thread_id: 019fb165-8174-7192-b19f-4ed19ed19426
ownership: repair only LAS-REV-001 and LAS-REV-002
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-LOCALE-AUTHORITY-SUCCESSOR-REPAIR-1-20260730/
created_at: 2026-07-30 Asia/Taipei
---

# Pantheon Locale Authority Successor Repair-1

## Role

你是本 successor chain 唯一 Repair owner。獨立 Review 已對 candidate
`1f9b9359754d4f3959ee86afcb9d5c257605f9dd` 判定 `REVIEW_NO_GO`，Review
evidence commit 為 `a5adb559e2f60ae5f8bd93183ec4aceaca7b78b7`。

只修：

- `LAS-REV-001`：ASCII tokenizer 未驗證 whole value。
- `LAS-REV-002`：單一 Title Case／短全大寫普通字只靠 capitalization shape
  取得 ja／ko authority。

不得重開需求、修改 Review finding、建立其他 Review／Repair／replacement，或
擴張成 locale validation 重構。

## Root question

如何以一個明確、封閉、whole-value 的 ASCII literal grammar，讓 ja／ko 每個
semantic item 拒絕未消費 punctuation／separator／junk 與普通英文 standalone
word，同時保留既有明列 positives、自然日韓內容、日文純漢字與 en 行為？

## Fresh root-cause evidence

Mainline 已在 reviewed candidate fresh 重跑 blocking groups：

```text
74 failed, 98 deselected
```

失敗完全落在：

- full-consumption：ja／ko × 五類 semantic item，加四個 helper probes；
- standalone word：ja／ko × 五類 semantic item ×
  `Strategy`／`SOURCE`／`Zorple`。

這些是 red-capable assertions 的預期失敗，不是 import、fixture 或環境錯誤。

## Root causes

### `LAS-REV-001`

`_ascii_is_name_acronym_or_number()` 使用 `re.findall(...)` 抽取可接受 token，
卻未證明 token spans 與允許 separator 完整覆蓋原始 ASCII-only value。
`@@OpenAI@@`、`OpenAI???`、slash／comma／semicolon junk 因此被忽略。

### `LAS-REV-002`

`is_single_name()` 與一般 acronym shape 只從大小寫／長度推斷 authority。
因此 `Strategy`、`Zorple`、`SOURCE` 可作為完整 ja／ko semantic item 通過。

## Required repair contract

### R1 — Whole-value grammar

- 對規範化後的完整 ASCII-only value 做 anchored／full-consumption validation。
- 任何未明列 punctuation、separator、leading／trailing junk 或未消費字元都
  fail closed。
- 不得用「先抽合法 token、忽略其餘字元」的方式判定。
- number grammar 可保留 decimal／percent 的既有 bounded 行為，但 grammar 與
  separator 必須明確。

### R2 — Verifiable standalone authority

- standalone alphabetic value 不得只靠 Title Case、UPPERCASE、長度或其他
  capitalization shape 取得 authority。
- 既有明列 positive `OpenAI`、`API` 必須通過；可使用最小、顯式、封閉的
  literal authority set。
- `GPT-5` 等含字母＋數字的 bounded model code與 `2026` 等 number可依封閉
  grammar 通過。
- multi-token pure ASCII 只允許已明列 token 類別與 topology；既有 positive
  `OpenAI GPT-5 2026` 必須通過。
- 一般 proper noun 若未在封閉 authority set，不得以 standalone ASCII semantic
  item 通過；它仍可出現在具有足夠目標語言 authority的日／韓內容中。
- 不得引入外部 entity registry、provider call 或一般英文詞庫。

### R3 — Preserve closed invariants

必須維持：

- ja `実践方法` 與自然日文通過；
- 自然韓文通過；
- 日／韓內容內的 `OpenAI`、`API`、`GPT-5`、`2026` 通過；
- standalone `OpenAI`、`API`、`GPT-5`、`2026` 與
  `OpenAI GPT-5 2026` 通過；
- en既有判定不回歸；
- `P0C-REREV-001`、`P0C-REV-003..006` 保持 CLOSED；
- provider 前所有 semantic fields 使用同一 authority boundary。

## Required red → green order

一次只關一個 finding：

1. Fresh 跑 Review probe 的 full-consumption group，確認 `LAS-REV-001` 為 RED。
2. 做最小 whole-value修復，重跑同 group 至 GREEN。
3. Fresh 跑 standalone word group，確認 `LAS-REV-002` 為 RED。
4. 做最小 standalone authority修復，重跑同 group 至 GREEN。
5. 跑完整 independent Review probes與 regression suites。

不得先改 code 再補回歸測試；不得修改 Review 專屬 probe 來取得綠燈。

## Allowlist

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- 本 Repair 實體卡；只能從 mainline committed card 精確 materialize
- 本 Repair 專屬 evidence／handoff

## Forbidden scope

- 不修改 successor Review card、Review evidence或
  `independent_review_probes.py`。
- 不修改 successor Implementation card／evidence。
- 不修改其他 production scripts、frontend、content artifacts或 shared registry。
- 不降低 deterministic、Reviewer、SEO、canonical、安全或publication gate。
- 不呼叫 provider、不讀寫 production `.work`。
- 不merge、push、deploy、publish。
- 不建立 re-review；完成後由 mainline送回原 Review thread。
- 不使用 hidden sub-agent。

## Verification

至少 fresh 執行並保存：

```text
<existing-venv-python> -m pytest \
  artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-LOCALE-AUTHORITY-SUCCESSOR-REVIEW-20260730/independent_review_probes.py \
  -q -k "full_ascii_value_consumption or rejects_unconsumed_characters"

<existing-venv-python> -m pytest \
  artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-LOCALE-AUTHORITY-SUCCESSOR-REVIEW-20260730/independent_review_probes.py \
  -q -k "rejects_single_ordinary_ascii_word"

<existing-venv-python> -m pytest \
  artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-LOCALE-AUTHORITY-SUCCESSOR-REVIEW-20260730/independent_review_probes.py -q

<existing-venv-python> -m pytest tests/test_agy_multilingual_pipeline.py -q

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
```

另執行：

- production compile；
- changed production／direct-test debug scan；
- `git diff --check a5adb559e2f60ae5f8bd93183ec4aceaca7b78b7 HEAD`；
- changed-files allowlist audit；
- evidence local-path／secret／raw-payload scan。

## Evidence contract

保存於本 Repair evidence path：

- `preflight.md`
- `repair-plan.md`
- `red-green.md`
- `verification.txt`
- `repair-evidence.md`
- `handoff.md`

證據不得包含本機絕對路徑、secret、raw provider payload或 production內容。

## Delivery

建立單一 Repair commit，direct parent 必須是
`a5adb559e2f60ae5f8bd93183ec4aceaca7b78b7`。回報：

- Repair commit與direct parent；
- `LAS-REV-001`／`LAS-REV-002` 的 root-cause-to-fix mapping；
- red → green結果；
-完整 independent probes與fresh suites；
- changed files；
- residual risks；
- 未執行的外部／production actions。

完成後停止在 `READY_FOR_RE_REVIEW`；不得自行宣稱 findings CLOSED、不得整合或
進production。
