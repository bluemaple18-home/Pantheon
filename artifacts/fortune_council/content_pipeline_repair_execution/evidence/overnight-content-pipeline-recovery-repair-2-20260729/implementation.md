---
id: PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-REPAIR-2-IMPLEMENTATION
status: PASS
type: evidence
---

# Implementation

## P1：分離 structural hydration 與 full policy gate

`hydrate_candidate()` 與 `hydrate_create_repair()` 新增預設為 `True` 的
`enforce_policy` 內部控制：

- 既有直接呼叫維持 full validation。
- `run_writer_reviewer()` 只有 create initial/intermediate hydration 使用
  `False`；`validate_candidate(..., enforce_policy=False)` 仍驗證 candidate
  schema、article required/unknown fields、非空 scalar/list、FAQ/body shape
  與 `publicationPolicy` shape。
- create immutable target identity 比對仍在 hydration 後、deterministic
  gate 前 fail closed。
- `quality_findings()` 產生 machine-owned findings；未映射 deterministic
  finding 仍由 `_create_repair_contract()` fail closed。
- deterministic findings 歸零後、Reviewer 呼叫前執行完整
  `validate_candidate()`。
- loop 結束、最終 candidate 寫出前再次執行完整 `validate_candidate()`。

因此 content-policy finding 不再被誤算為 Writer schema repair；external
payload shape／未授權欄位等真正 schema failure 仍使用原 schema budget。
沒有增加 content 或 schema repair budget。

## P2：共用 detector 與逐欄定位

- 抽出 `_has_false_social_origin()`，保留原 regex 語意。
- `quality_findings()` 與 `_create_repair_fields()` 共用此 predicate。
- Repair locator 分別掃描 `title`、`description`、`answer`、
  `bodySections`，只回傳實際命中欄位聯集。
- finding 存在但任何單欄都無 predicate 命中時，既有 deterministic
  `unmapped ...` 分支明確 fail closed；不 fallback 到正文或全部欄位。

## Regression guards

- 真正 `run_writer_reviewer()` short-answer E2E：
  `writer → writer → reviewer`、第二次 schema 只有 `slot+answer`、
  `schema_repairs_used=0`、`content_repairs_used=1`、attempts `2`、Reviewer
  前 deterministic findings 為空、其他欄位 compact JSON bytes 不變。
- `false_social_origin` 四個單欄、title+answer 聯集、跨欄不可定位
  fail-closed。
- title-only bounded schema 僅 `slot+title`；多帶 `answer` 被拒；修復後
  finding 歸零且未授權欄位 bytes 不變。

## 保持不變

- `standalone_answer -> answer`。
- deterministic 未映射 fail-closed 與 Reviewer 自訂 code fallback。
- publication policy、quality detector、Reviewer schema、repair budgets。
- publisher、coordinator、installer、plist、docs 與既有 evidence。
