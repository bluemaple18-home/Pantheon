# Pantheon Promotion Ledger Schema Contract Repair - 2026-08-29

## 工作名稱

PANTHEON-PROMOTION-LEDGER-SCHEMA-CONTRACT-REPAIR

## 目標

修復 promotion preserved-run ledger 驗證的 cross-version schema contract gap：publisher 自 commit `2b5da2f` 起在 `translation_published_runs` 使用 durable singular `article_id`，但 promotion 自 commit `2c1c6a` 後錯誤要求所有 ledger collections 都使用 `article_ids` list，導致 v0.3.374 translation published history 被誤擋。

## 唯一 RCA 裁決

- 主因：cross-version schema contract gap。
- 次因：promotion validator overreach，把 collection-specific durable schema 扁平化成全域 `article_ids` list。
- 已證偽：publisher producer bug；v0.3.369/v0.3.374 live translation ledger 皆使用 singular `article_id`。
- 已知 blocking mismatch：136 preserved/live census 中只有 v0.3.374 translation shape。

## 可改檔案

- `scripts/pantheon_content_runtime_promotion.py`
- `tests/test_pantheon_content_runtime_promotion.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-PROMOTION-LEDGER-SCHEMA-CONTRACT-REPAIR-20260829.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_promotion_ledger_schema_contract_repair_20260829/`

## 禁止範圍

- 禁止改 publisher、coordinator、registry、shared ledger、live state。
- 禁止 promotion/provider/publisher/commit/push/tag/deploy。
- 禁止逐 lane if/else、generic field union、DB、FSM、migration、live ledger rewrite。

## 實作契約

- 必須 TDD：先用 exact v0.3.374 translation-shaped singular `article_id` ledger record 跑 RED 並保存 failure receipt。
- GREEN 必須用 declarative collection descriptor 定義各 collection identity field/cardinality。
- 必須以 shared exact canonicalizer 產生 canonical `article_ids` tuple。
- `article_id` 與 `article_ids` 必須互斥；unexpected、both、missing、wrong type、duplicate、drift 皆 fail closed。
- new/rewrite 既有 shape 與 preserved matching 不得退化。
- 必須有 bounded compatibility matrix 或等價 fixture，證明只有已知 translation singular shape 轉 GREEN，malformed 仍 RED。
- plan-only 必須 idempotent；transaction root、production bytes、provider call、publisher call 都必須為 0。

## 驗收命令

- RED: exact v0.3.374 translation-shaped test only, expected fail before source edit。
- GREEN: targeted schema tests pass。
- Full: `python -m pytest tests/test_pantheon_content_runtime_promotion.py`
- Compile: `python -m py_compile scripts/pantheon_content_runtime_promotion.py tests/test_pantheon_content_runtime_promotion.py`
- Diff hygiene: `git diff --check`
- Budget: source+test changed LOC <= 200。

## 交付格式

RESULT 必須包含改檔、RED/GREEN、完整測試命令與結果、LOC、allowlist diff、production immutability、artifact 路徑、風險，以及 why_not_less/why_not_more/do_not_absorb 與 anti-expansion receipt。狀態為 `RE_REVIEW_REQUESTED`。
