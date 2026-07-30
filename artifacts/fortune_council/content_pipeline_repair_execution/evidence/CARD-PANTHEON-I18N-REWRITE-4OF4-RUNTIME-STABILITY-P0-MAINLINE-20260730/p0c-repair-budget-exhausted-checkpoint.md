# P0-C Repair Budget Exhausted Checkpoint

- captured_at: `2026-07-30 Asia/Taipei`
- mainline_thread: `019fb165-8174-7192-b19f-4ed19ed19426`
- chain: `pantheon-i18n-rewrite-4of4-runtime-stability-p0-20260730`
- state: `BLOCKED_PENDING_REPAIR_BUDGET_DECISION`

## Root question

讓既有 `fortune-0039` deferred i18n-rewrite run先建立topic-neutral、
locale-specific plan，再依source fact package原生重寫；repeated findings必須
重建outline，continuation則須保留lineage、bounded、idempotent且fail closed。

## Current state

- P0-A／P0-B已通過獨立Review並在主線完成fresh acceptance：
  `462 passed, 1 warning`。
- P0-C Implementation candidate：
  `f0b70b4bba41a952f9b8bc2c12d3a2bc5c13502e`。
- 原Review evidence commit：
  `cc76cce1eb713ab6e1cf202392b7f4ae35c62071`，verdict `REVIEW_NO_GO`。
- Repair-1 candidate：
  `bcb1ae53215996a9d4504bdb3247e1090afbb3ee`，direct parent
  `cc76cce1eb713ab6e1cf202392b7f4ae35c62071`。
- Targeted re-review evidence commit：
  `5d75d1802e379e022ae5682fd9d6ebe019d804f6`，verdict
  `REVIEW_NO_GO`。
- Repair-1 fresh suites：
  - required suite：`474 passed, 1 warning`
  - original Review probes：`12 passed`
  - `git diff --check`：PASS
- Targeted probes：`2 failed, 1 passed`；兩個failure是尚未關閉的P1
  requirement probes。
- Candidate尚未整合到mainline；未呼叫provider、未讀寫production `.work`、
  未push、deploy或publish。

## Blocker

Review卡的`repair_budget: 1`已用盡，且仍有兩筆P1：

1. `P0C-REREV-001`：後續generation plan-pending replay的`prior_plan`第一次來自
   in-memory dict，重跑來自sorted-key JSON artifact；`_plan_prompt()`未canonical
   serialize structured fragments，導致prompt/request identity漂移。
2. `P0C-REREV-002`：locale gate只做所有semantic fields的aggregate script ratio；
   ko的其他母語欄位可掩護整組英文H2，錯語言outline仍被article phase接受。

## Candidate fork

- Recommended、尚未啟動：在使用者明確增加一次repair budget後，建立唯一
  Repair-2／Retry-1卡，以targeted re-review evidence commit
  `5d75d1802e379e022ae5682fd9d6ebe019d804f6`為base，只修：
  - structured prompt canonical serialization與later-generation plan replay；
  - critical field-group／per-item locale validation。
- Alternative、尚未啟動：停止本candidate，重新設計整個P0-C continuation。
  目前四筆原finding已關閉，兩筆剩餘finding範圍明確，因此不建議此fork。

## Next step

等待使用者決定是否明確增加一次repair budget。若核准：

1. 建立唯一實體Repair-2／Retry-1卡。
2. 建立獨立可見task與clean worktree，base精確為
   `5d75d1802e379e022ae5682fd9d6ebe019d804f6`。
3. 修復後交回同一原Reviewer做targeted re-review。
4. 只有`REVIEW_GO`後才整合mainline與跑fresh acceptance。

## Waiting condition

使用者明確核准「增加一次repair budget並開唯一Repair-2／Retry-1」。

## Limits

- 未核准前不得建立Repair-2／replacement、修改candidate或整合NO_GO candidate。
- 未取得精確外部授權前不得呼叫provider、push、deploy、publish或修改production
  `.work`。
- 不降低deterministic、Reviewer、SEO、canonical、安全或publication gate。
