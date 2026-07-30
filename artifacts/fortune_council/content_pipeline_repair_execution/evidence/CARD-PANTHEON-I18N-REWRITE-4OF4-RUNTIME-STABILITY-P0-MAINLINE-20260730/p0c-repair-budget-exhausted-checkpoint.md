# P0-C Repair Budget Exhausted Checkpoint

- captured_at: `2026-07-30 Asia/Taipei`
- mainline_thread: `019fb165-8174-7192-b19f-4ed19ed19426`
- chain: `pantheon-i18n-rewrite-4of4-runtime-stability-p0-20260730`
- state: `BLOCKED_STRICT_REPAIR_LIMIT_EXHAUSTED`

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
- 使用者已核准第二代、最後一代Repair。
- Repair-2 card commit：
  `04ce6b662651d213477125c8e3a3977dcb9a4523`。
- Repair-2 candidate：
  `488c3ca290cc62811100f5b73a6eb530f86c6634`，direct parent
  `5d75d1802e379e022ae5682fd9d6ebe019d804f6`。
- Final targeted re-review evidence commit：
  `ce34670911a7c4691cb6a3cea851b7a805ff965e`，verdict
  `REVIEW_NO_GO`。
- Repair-2／final review fresh evidence：
  - direct multilingual：`64 passed`
  - original Review probes：`15 passed`
  - required suite：`492 passed, 1 warning`
  - candidate `git diff --check`：PASS
  - final independent probes：`3 passed, 10 failed`
- Candidate尚未整合到mainline；未呼叫provider、未讀寫production `.work`、
  未push、deploy或publish。

## Blocker

Strict chain允許的兩代Repair均已用盡，且仍有一筆P1：

1. `P0C-REREV-002`：per-item gate會把
   `READERS EVALUATE SOURCES CAREFULLY`這類全大寫一般英文誤認為acronym／產品名，
   因而在ja／ko的intent、query、angle、H2與coverage note放行。
2. 同一判定也會把合法日文純漢字H2如`実践方法`誤判為繁中殘留；這是同一
   locale authority P1的false-positive側。

已關閉：

- `P0C-REREV-001`：prompt bytes、SHA、request identity、job ID與單一enqueue
  均穩定。
- `P0C-REV-003..006`：無回歸。

## Candidate fork

- Current mainline：停止本candidate；不得用Repair-3、改名或replacement繞過
  strict兩代Repair上限。
- Pending independent fork：若使用者仍要繼續，必須由主線重新立一條新chain／
  新spec，先重新設計locale authority validator，再重新建立完整Implementation →
  Review鏈；不能把它冒充本chain的下一代Repair。
- Production fork：仍pending，且被本P1與`REVIEW_NO_GO`阻擋。

## Next step

本chain無合法下一個Repair step。若使用者要求繼續，主線先重新做
root question／scope／validator design arbitration，形成新chain；不得直接繼承
本chain的GO狀態，且新candidate仍需獨立Review。

## Waiting condition

使用者明確選擇是否：

1. 停止P0-C並保留目前P0-A／P0-B成果；或
2. 另立新chain重新設計locale authority validator。

## Limits

- 不得建立Repair-3、用新finding名稱重置repair generation，或整合NO_GO
  candidate。
- 未取得精確外部授權前不得呼叫provider、push、deploy、publish或修改production
  `.work`。
- 不降低deterministic、Reviewer、SEO、canonical、安全或publication gate。
