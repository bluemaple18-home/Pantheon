---
id: PANTHEON-PROMOTION-LEDGER-SCHEMA-CONTRACT-REPAIR-20260829
status: dispatched
type: bounded_repair
owner: repair_worker
root_cause: cross-version schema contract gap
---

# Pantheon promotion ledger schema contract Repair

## 目標

在 promotion 的共用 preserved-run identity seam，正規化各 durable ledger collection 的正式 article identity cardinality，使既有 v0.3.374 translation `article_id` record 可被精確驗證，同時維持 malformed record fail closed。

## 唯一可改範圍

- `scripts/pantheon_content_runtime_promotion.py`
- `tests/test_pantheon_content_runtime_promotion.py`
- 本卡與同名 evidence 目錄

Source/test changed LOC 上限 200。

## 禁止範圍

- 不改 publisher、coordinator、registry、ledger production bytes、runtime state。
- 不逐 lane 寫 if/else，不做 generic field union。
- 不新增 database、registry、FSM、migration 或 live ledger rewrite。
- 不執行 promotion、production、provider、publisher、commit、push、tag、deploy。

## 驗收

1. Exact v0.3.374 translation record 先 RED 後 GREEN。
2. 以 declarative collection descriptor 定義正式 identity field/cardinality，使用單一 exact canonicalizer。
3. missing、both、unexpected、wrong type、duplicate、identity drift 全部 fail closed。
4. new/rewrite 既有 shape 與 preserved-run matching 不退化。
5. plan-only 兩跑 idempotent，transaction root、production bytes、provider/publisher mutation 全為 0。
6. Promotion full suite、`py_compile`、`git diff --check`、source budget 通過。
7. RESULT 明列 `why_not_less`、`why_not_more`、`do_not_absorb` 與 anti-expansion receipt，交付 `RE_REVIEW_REQUESTED`，不得 commit。
