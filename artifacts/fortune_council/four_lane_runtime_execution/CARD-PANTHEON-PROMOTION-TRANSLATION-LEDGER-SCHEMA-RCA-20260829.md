---
id: PANTHEON-PROMOTION-TRANSLATION-LEDGER-SCHEMA-RCA-20260829
status: complete
type: rca
mode: readonly
---

# Promotion translation ledger schema RCA

## Root question

為何 remote `main` `55e2` 的 promotion plan 在讀取 v0.3.374 後 live state 時，以 `publisher ledger identity mismatch` fail closed：是 publisher 寫出錯誤的 singular `article_id`、promotion validator 對正式 lane-specific schema 過度收窄，或跨版本 schema contract 缺口？

## 已知失敗

- Registry envelope 的 `translate_existing` target run 使用 `article_ids: [...]`。
- Durable `translation_published_runs` entry 使用 singular `article_id`。
- Promotion `_publisher_ledger_evidence` 固定以 `_validated_ledger_article_ids(entry.get("article_ids"))` 驗證。
- transaction 未建立；provider／publisher／其他 mutation 均為 0。

## 可寫範圍

- 本卡。
- `pantheon_promotion_translation_ledger_schema_rca_20260829/RESULT.md`。
- 同名 evidence 目錄內 machine-readable receipts 與唯讀 reproduction harness。

## 禁止範圍

- 不改 source、tests、ledger、registry、runtime、plist。
- 不執行 promotion、terminalize、provider、publisher。
- 不 commit、push、tag、deploy。
- 不手改 live ledger，不建立 migration DB／registry，不以 generic accept-both 放寬驗證。

## 連續故障停線四證

1. 找出這個 ledger shape 前最後一次成功 promotion、版本與 live state；驗證是否當時尚無 `translation_published_runs`。
2. 定位哪個 writer／commit／mechanism 形成 singular translation ledger，以及哪個 promotion commit／validator 開始拒絕；裁決 publisher 或 validator 誰是 schema authority。
3. 定義 new／rewrite／translation lane-specific ledger records、registry envelopes、promotion preserved-run identity 的 durable invariant，涵蓋跨版本 migration／compatibility。
4. 實跑 exact RED-capable fixture：使用 real v0.3.374-shaped record，僅 plan-only，provider mutation 0、new transaction 0、輸入 bytes unchanged，穩定命中原 failure。

## 必查

- singular `article_id` 是正式 publisher schema，或 malformed production record。
- 其他 translation／rewrite entries 是否同 shape。
- 最後成功 promotion 是否因當時尚未有 `translation_published_runs` 才通過。

## 裁決與 Repair frontier

- 主裁決只可為：`producer schema bug`、`promotion validator overreach`、`cross-version schema contract gap` 之一；其他因素另列 secondary。
- 最小 Repair 僅允許 exact canonicalization、ambiguity／drift fail closed 與 regression tests。
- 必答 `why_not_less`、`why_not_more`、`do_not_absorb`。

## 驗收

- `RESULT.md` 明確標示 `NO-GO | PARTIAL | BLOCKED | GO`，事實與推論分離。
- machine receipts 可重跑，包含 commit／writer timeline、schema census、RED fixture、mutation counters 與 bytes-before/after digest。
- `git diff --check` 通過；除本卡與同名 evidence dir 外無本任務新增修改。
