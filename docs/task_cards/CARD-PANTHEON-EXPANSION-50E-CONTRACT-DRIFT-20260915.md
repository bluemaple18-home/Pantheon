# Expansion 50E 新舊內容契約分流

## 目標

消除 expansion-50e 舊 cohort regression 與現行 canonical rewrite policy 的衝突，讓合法 rewrite 不再於完整 release suite 被舊規格誤殺；真正 canonical content failure 仍須在昂貴 suite 前成為 `non_retryable`。

## 已證實根因

- 舊 cohort 測試自 2026-07-19 起固定要求正文 800–1400 字、4 節。
- canonical policy 自 2026-07-27 起要求 `rewrite_existing_body` 為 1300–2000 字、5 節。
- production 的 astrology-0073（1548 字）與 0079（1543 字）通過 canonical precheck，之後被舊 cohort assertion 擋下。
- 這是 cohort-wide contract drift；不是 run ID 特例，也不是 retry taxonomy 錯誤。

## 範圍

- 只調整既有 `tests/test_web.py` 的 expansion-50e cohort contract，直接讀既有 canonical profile。
- 補 Publisher regression：canonical rewrite 可進 suite；超過 canonical 上限或 section profile 不符時，在 suite 前 `non_retryable`。
- 不改 taxonomy、scheduler、fairness、Writer、Reviewer、policy 數值或 production state。
- 不新增 validator、registry、FSM、資料庫或 run-ID 特判。

## 驗收

1. untouched legacy 50e 文章仍須符合 800–1400 字、4 節。
2. `substantive_rewrite` 文章由既有 canonical `rewrite_existing_body` profile 判定；1548 字、5 節通過 full suite。
3. >2000 字或 section profile 不符，既有 canonical path 在 full suite 前產生 terminal policy rejection，命中 run 為 `non_retryable`，同 batch 未命中 run 不受影響。
4. recovery 候選只能由可重現的 failure evidence 證明為 stale 50e assertion；不得按 run ID 或 cohort 身分直接恢復。
5. 受影響測試、Publisher suite、`py_compile`、`git diff --check` 通過；候選交獨立 review。

## Recovery 證據契約

既有 exhausted run 不在本卡直接 mutation。後續每個候選須以保存的 candidate hash、failure timestamp、對應 production log assertion，以及修正前 RED／修正後 GREEN replay 綁定；只有證據完整者才可走既有 dry-run digest → apply recovery。
