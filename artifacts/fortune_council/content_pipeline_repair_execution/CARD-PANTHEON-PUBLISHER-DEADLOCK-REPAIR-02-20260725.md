---
card_id: CARD-PANTHEON-PUBLISHER-DEADLOCK-REPAIR-02-20260725
status: CARD_DRAFTED
type: repair
project: Pantheon
chain: pantheon-publisher-deadlock-repair-20260724
generation: Repair-2
created_at: 2026-07-25
owner: repair_executor
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 最後一輪修復涉及 concurrent write、跨週期 distributed state 與 queue retry attribution，屬核心發布安全契約與高回退成本。
base_sha: 41522076fccbe0406fb4d270d138368ce5c0395f
parent_candidate: 6ea7a7ffdfd2280555af0400baa4dc0167babdce
original_reviewer_thread: 019f9497-d801-7183-b4a9-9c9388aadd15
---

# Pantheon Publisher Deadlock Repair-2

## Root question

只修原 Reviewer 在 Repair-1 re-review 中仍未解決的 `PPD-R-001`、`PPD-R-002`、
`PPD-R-003`，保留已解決的 `PPD-R-004`，交回同一 Reviewer re-review。這是本 chain
最後允許的 Repair generation；若再次 `REVIEW_NO_GO`，必須回主線
`BLOCKED / REVIEW_REPAIR_LIMIT`。

## Fixed lineage

- Base：`41522076fccbe0406fb4d270d138368ce5c0395f`
- Original candidate：`21dab0283f5a6690d1d4cd1631efe1354955818e`
- Repair-1 parent：`6ea7a7ffdfd2280555af0400baa4dc0167babdce`
- Reviewer：`019f9497-d801-7183-b4a9-9c9388aadd15`
- Re-review verdict：`REVIEW_NO_GO`

## Unresolved findings

### PPD-R-001

`MutationJournal.checkpoint()` 從 mutation 後的 shared worktree 回讀 bytes 當 expected
post-image。publisher write 後、checkpoint 前若有 concurrent write，該 bytes 會被
錯當成 publisher output，recovery 再覆寫回 pre-image。

Required fix：expected post-image 不得由未受保護的 mutation 後 shared worktree回讀
推導。以 publisher 已知 payload／寫入 helper 的 before-and-after capture／private
staging 建立可歸因 write-set；任何無法歸因的 bytes 必須保存 evidence、fail-closed，
禁止覆寫。

### PPD-R-002

`PUSH_OUTCOME_UNKNOWN` 只寫 evidence，下一輪 preflight 不讀 durable unresolved
state。remote main=candidate、tag missing 時，下一輪仍可通過 clean-origin。

Required fix：在 state root 寫 durable unresolved push control record；所有 publish
phase 在 clean-origin／collector／mutation 前都必須檢查並 fail-closed。只有明確
reconciliation 驗證 remote main、tag、ledger/evidence 已收斂後才能清除。

### PPD-R-003

wrapper 以 `_queued_run_ids()` 在真實 collector 前預猜失敗 run，會把 retry metadata
誤歸因到排序較前但已 published 的歷史 run，實際失敗 run 仍 eligible。

Required fix：failure identity 必須來自通過真實 collector 全部 filters 後的實際
selected run IDs；將 selected IDs 寫入 transaction context/journal，再由 recovery
使用。不得用獨立 queue 預掃作為 attribution authority。

## Required RED → GREEN

1. 真實 Git：publisher write 完成、checkpoint 前注入 concurrent owned-path write；
   recovery 不得覆寫 concurrent bytes。
2. Push unknown：remote main=candidate、tag missing 後，下一次完整 publisher call
   必須在 mutation 前被 durable control record 阻擋。
3. 三 queue E2E：第一個 complete run 已 published、第二個 ready run 實際失敗、
   第三個 healthy；retry 必須屬於第二個，第三個下一輪可發布。
4. 原 Repair-1 全部 regression 維持綠燈，`PPD-R-004` 不得退化。

## Allowlist

- `scripts/agy_content_publisher.py`
- `tests/test_agy_content_publisher.py`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-PUBLISHER-DEADLOCK-REPAIR-02-20260725/**`

需要越界先停，不得自行擴張。

## Forbidden

- 不改 Reviewer evidence、finding ID、chain 或 generation。
- 不改文章、registry、sitemap、feed、redirects、launchd、正式 actor、queue payload、
  ledger schema 或 V4 default/shadow 邊界。
- 不刪 candidate、queue、ledger、state 或 evidence。
- 不使用 destructive Git；不 push、merge、deploy。
- 不自審；不得更換 Reviewer。

## Verification

- Required RED → GREEN cases。
- `tests/test_agy_content_publisher.py`
- `tests/test_agy_seo_copy_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- `tests/test_web.py`
- Full pytest。
- `git diff --check`
- `git status --short`
- changed-files allowlist。

測試使用 `<repo-root>/.venv/bin/python -m pytest`；若只因缺
`node_modules/iztro` 出現卡片既知 Ziwei failures，可依既有 lockfile 執行
`pnpm install --frozen-lockfile`，不得改 manifest／lockfile。

## Evidence

寫入：
`artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-PUBLISHER-DEADLOCK-REPAIR-02-20260725/`

至少包含 finding matrix、測試命令／exit code、changed files、完整 candidate SHA。

## Delivery

只可交付 `REPAIR_READY_FOR_REVIEW` 與單一完整 Repair-2 candidate SHA；完成後通知主線，
由主線把同一 Reviewer worktree 指向候選，再回原 Reviewer re-review。

## Stop

同一 blocker 第三次立即停；需要越界、無法保留 concurrent bytes／queue／ledger／
candidate／evidence，或無法建立單一可審 commit 時，回報 `BLOCKED`。不得第四次嘗試。
