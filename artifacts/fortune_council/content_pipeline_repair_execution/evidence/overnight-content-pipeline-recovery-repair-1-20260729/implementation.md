---
id: PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-REPAIR-1-IMPLEMENTATION
status: PASS
type: evidence
---

# Implementation

## 最小修補

`scripts/agy_seo_copy_pipeline.py`：

1. `_create_repair_fields()` 明確加入
   `standalone_answer -> {'answer'}`。
2. 補齊可由 create deterministic content gate 修復的固定 codes：
   answer、title、description、tags、bodySections 各自只授權對應欄位。
3. 對需要依內容定位的 codes
   (`article_level_evidence`、banned/generic phrase、outcome guarantee、
   professional substitution) 只授權實際命中的 content fields。
4. `_create_repair_fields()` 與 `_create_repair_contract()` 新增
   `deterministic_findings` 內部旗標。deterministic 未映射 finding 明確拋出
   `CandidateValidationError("unmapped deterministic create finding: ...")`。
5. `run_writer_reviewer()` 只在本機 deterministic review 來源設定該旗標；
   獨立 Reviewer finding 保留原本未知 code 到 `bodySections` 的 bounded
   fallback。

沒有修改 schema、validator、publication policy、quality gate、repair
budget、Reviewer payload schema、publisher deployment preflight 或
`NEW_ONLY` coordinator。

## Deterministic code inventory

明確欄位 mapping：

- `answer`：`answer_length`、`standalone_answer`
- `description`：`description_boundary`、
  `description_context_and_limit`、`description_length`、`missing_boundary`
- `title`：`title_keyword`、`title_length`、`title_primary_intent`
- `tags`：`required_tags`
- `bodySections`：body/paragraph/section length 與 shape、opening intent/keyword、
  cross-corpus/repeated sentence、Pantheon context、false social origin、
  explicit limit
- 內容定位：`article_level_evidence`、`banned_phrase`、
  `generic_ai_phrase`、`no_outcome_guarantee`、
  `no_professional_advice_substitution`

本機／immutable policy-contract 類 finding 與未來未知 deterministic code
沒有交給 Writer 的安全欄位，因此明確 fail closed。Reviewer 自訂 code 不受
此 deterministic 限制。

## Regression guards

`tests/test_agy_seo_copy_pipeline.py` 新增：

- `standalone_answer` contract/schema 只含 `{slot, answer}`。
- 全部 repairable deterministic create codes 的 code-to-field contract。
- dynamic finding 的實際欄位定位。
- deterministic 未映射 fail closed，Reviewer 自訂 code fallback 保留。
- partial answer merge 後其他欄位 compact JSON bytes 不變。
- repair response 帶未授權 `bodySections` 時拒絕。
- 短 answer 修復後 deterministic findings 歸零。
