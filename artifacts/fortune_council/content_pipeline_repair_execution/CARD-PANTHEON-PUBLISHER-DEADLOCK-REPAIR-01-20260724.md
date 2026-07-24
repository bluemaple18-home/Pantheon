---
card_id: CARD-PANTHEON-PUBLISHER-DEADLOCK-REPAIR-01-20260724
status: RUNNING
type: repair
project: Pantheon
chain_id: pantheon-publisher-deadlock-repair-20260724
generation: 1
parent_candidate_sha: 21dab0283f5a6690d1d4cd1631efe1354955818e
base_sha: 41522076fccbe0406fb4d270d138368ce5c0395f
review_thread_id: 019f9497-d801-7183-b4a9-9c9388aadd15
review_verdict: REVIEW_NO_GO
owner: repair
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 三項 P1 涉及 concurrent write data loss、distributed push acknowledgement 與 queue starvation。
created_at: 2026-07-24 23:02 CST
---

# Pantheon Publisher Deadlock Repair-1

## Root question

在不降低 gate、不刪除 queue/ledger/candidate 的前提下，修復 Reviewer 指出的三項 P1 與一項 P2，形成新的單一 repair candidate，交回原 Reviewer re-review。

## Current blocker

原 implementation candidate：
`21dab0283f5a6690d1d4cd1631efe1354955818e`

原 Reviewer verdict：`REVIEW_NO_GO`

原 Reviewer thread：
`019f9497-d801-7183-b4a9-9c9388aadd15`

## Findings to repair

### PPD-R-001 — P1 concurrent owned-path data loss

- `scripts/agy_content_publisher.py` 的 wrapper 在取得 publisher 內部 lock 前先做 clean check 與 base snapshot。
- recovery 只用 publisher-owned path allowlist，沒有 transaction write-set/pre-image identity。
- 重現：`concurrent_owned_edit_preserved=False`、`concurrent_repo_clean=True`。
- 必修：
  - initial snapshot 前取得 repo-scoped transaction lock，持有至 recovery/commit 結束；
  - 只有明確進入 publisher mutation phase後才允許 recovery；
  - 保存 pre-image/write-set，restore 前驗證 expected post-image；
  - concurrent bytes 不一致時保存證據並 fail-closed，禁止覆寫。

### PPD-R-002 — P1 ambiguous atomic push deadlock

- atomic push 可能已被 remote 接受，但 client 收到 error。
- 原 candidate 一律 rollback local HEAD/tag，未 fetch/reconcile remote refs。
- 重現：
  - `ambiguous_local_restored_to_base=True`
  - `ambiguous_remote_contains_candidate=True`
  - `ambiguous_retry_blocked=PublishBlocked`
- 必修：
  - push exception 後 fetch remote main/tag；
  - main/tag 都精確指向本輪 candidate：視為已提交，完成 ledger/evidence；
  - main/tag 都未移動：才可 rollback；
  - 其他組合：進入 `PUSH_OUTCOME_UNKNOWN`，保存 refs/evidence、fail-closed，禁止錯誤 rollback。

### PPD-R-003 — P1 failed candidate queue starvation

- `failed_recovered` 沒有寫 run-scoped retry/defer/attempt/eligibility。
- 預設 `max_runs=1` 時，同一壞 candidate 可反覆占住唯一 slot。
- 原測試 monkeypatch collector，沒有驗證真實 queue selection。
- 必修：
  - repo 外寫 run-scoped retry/defer record；
  - 至少包含 attempt、error class、evidence path、next eligibility；
  - collector 跳過已達 retry policy或未到 eligibility 的 run，繼續掃後方 candidates；
  - candidate/queue payload 必須保留。

### PPD-R-004 — P2 cleanup failure evidence gap

- 原 recovery 先 cleanup，最後才寫 `failure.json`。
- fault injection：`cleanup_failure_patch_count=1`、`cleanup_failure_json_count=0`。
- 必修：
  - cleanup 前原子寫 immutable `failure-attempt.json`；
  - 至少含 base/head/run IDs、original error、pre-recovery status；
  - 每個 cleanup step完成後寫 `recovery-result.json`；
  - cleanup 失敗也必須留下可判讀 metadata。

## Allowed files

- `scripts/agy_content_publisher.py`
- `tests/test_agy_content_publisher.py`
- 如 findings 確實需要：
  - `scripts/agy_gemini_coordinator.py`
  - `tests/test_agy_gemini_coordinator.py`
- Repair evidence：
  `artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-PUBLISHER-DEADLOCK-REPAIR-01-20260724/**`

若要修改其他檔案，先停下回報，不得自行擴張。

## Forbidden scope

- 不修改 Reviewer evidence。
- 不重新命名 finding、重置 generation 或另開新 chain。
- 不新增/修改文章正文。
- V4 必須維持 shadow，禁止 default promotion。
- 不刪除、重建、截短 queue、ledger、run states。
- 不使用 `git reset --hard`、`git checkout --`。
- 不降低 deterministic/review/release gate。
- 不 push、merge、deploy，不操作正式 actor或 launchd。

## Required RED → GREEN

1. 真實 Git 測試：clean check 與 mutation 間出現 publisher-owned concurrent change，bytes 必須保留。
2. 真實 Git 測試：publisher mutation 後同路徑被 concurrent writer 修改，禁止覆寫。
3. Push matrix：
   - remote 未接受；
   - remote 已原子接受但 client raises；
   - remote main/tag 不一致。
4. 真實雙 queue entries：
   - 第一個 candidate-specific failure；
   - 第二個 pass；
   - 壞 run 保留，健康 run可發布。
5. Recovery fault injection：
   - archive copy
   - `update-ref`
   - restore
   - unlink
   - tag delete
   - final evidence write
   每次都要有 pre-cleanup metadata。

## Verification

- findings 對應的 RED → GREEN tests。
- `.venv/bin/python -m pytest tests/test_agy_content_publisher.py tests/test_agy_multilingual_pipeline.py tests/test_agy_gemini_coordinator.py -q`
- `.venv/bin/python -m pytest tests/test_web.py -q`
- `.venv/bin/python -m pytest -q`
- `git diff --check`
- `git status --short`

已知 baseline：若 full pytest 因乾淨 worktree 缺少 `node_modules/iztro` 出現兩項 ziwei provider failure，可依 lockfile 安裝既有依賴後重跑；禁止修改 manifest/lockfile。

## Evidence and delivery

Evidence：
`artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-PUBLISHER-DEADLOCK-REPAIR-01-20260724/`

交付：

- 四項 finding 的 RED → GREEN 對照
- changed files
- focused/full test結果與 exit code
- 完整 repair candidate SHA
- `REPAIR_READY_FOR_REVIEW`

Repair 不得自稱 REVIEW_GO、已整合、已上線或正式 actor 已恢復。

## Next step

Repair candidate 完成後，必須回原 Reviewer thread
`019f9497-d801-7183-b4a9-9c9388aadd15`
re-review；禁止換 Reviewer。

## Stop conditions

- 同一 blocker 第三次失敗立即停，不做第四次。
- 無法保留 concurrent bytes、queue/ledger/candidate 或 failure evidence 時停止。
- 需要 allowlist 外共享生成檔、外部控制面或 destructive cleanup 時停止。

## Dispatch receipt

- mainline dispatcher thread：`019f935b-5af7-7902-b429-e11a5613d4bb`
- parent implementation thread：`019f9420-3ece-7cf2-84ee-66ebb64e0820`
- original Reviewer thread：`019f9497-d801-7183-b4a9-9c9388aadd15`
- Repair-1 thread：`019f94a8-6021-7480-8dda-48f83fc4349b`
- Repair-1 title：`Pantheon｜Repair-1 修復 Publisher Deadlock Findings｜CARD-PANTHEON-PUBLISHER-DEADLOCK-REPAIR-01-20260724`
- source kind：candidate commit
- source SHA：`21dab0283f5a6690d1d4cd1631efe1354955818e`
- source ref：`codex/publisher-deadlock-candidate-20260724`
- source clean：PASS
- unrelated dirty paths：`[]`
- worktree cwd：`<codex-home>/worktrees/0b8c798b-15f1-4b69-b823-d58dd45c2177/Pantheon`
- worktree exists：PASS
- worktree HEAD：`21dab0283f5a6690d1d4cd1631efe1354955818e`
- worktree clean：PASS
- worktree 與 implementation/Reviewer/mainline 均不同：PASS
- `index.lock`：不存在
- runtime model override：依 `create_thread` 契約，使用者未指定模型，未強制覆寫；卡片保留 strict/high 建議與理由
- Gate 1 card contract：PASS
- Gate 2 visible thread：PASS
- Gate 3 Repair candidate delivery：PENDING
- Gate 4 original Reviewer re-review：PENDING
- Gate 5 mainline acceptance：PENDING
- workflow：`RUNNING`
