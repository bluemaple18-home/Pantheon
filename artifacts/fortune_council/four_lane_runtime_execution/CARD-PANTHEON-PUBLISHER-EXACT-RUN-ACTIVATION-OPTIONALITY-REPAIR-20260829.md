# CARD：Pantheon Publisher Exact-Run Activation Optionality Bounded Repair

- 卡號：`CARD-PANTHEON-PUBLISHER-EXACT-RUN-ACTIVATION-OPTIONALITY-REPAIR-20260829`
- 類型：bounded Repair
- 狀態：`RE_REVIEW_REQUESTED`
- accepted base：`bde44589f3785aae738bb7d7b1626270ba5505d0`
- 唯一主因：`CAPACITY_VALIDATOR_OVERREACH`

## Reviewed Authority

- RCA：`pantheon_publisher_exact_run_activation_ordering_rca_20260829/RESULT.md`
- Reviewer：同目錄 `REVIEWER-RESULT.md`
- Reviewer verdict：`GO`，無 P0/P1。

## Locked Contract

只在 `scripts/pantheon_content_capacity_guard.py` 恢復 `publisher-exact-run-id` 的 optional-before-run contract：

1. selector 缺席時，只有 Publisher plist 與 stage receipt 同步缺席才可通過。
2. selector 存在時，沿用 shared Publisher exact contract，嚴格驗證 stage receipt與Publisher plist一致；空值、格式錯誤、單邊缺失或不一致一律 fail closed。
3. 無論 selector 存在或缺席，都必須繼續既有 manifest digest、generation、barrier、model route、six/seven staged tuple、old-live cohort、Rule24、normal/recovery mode 與 stopped topology檢查。
4. Capacity 不讀 run、queue、registry，不驗 completion，不新增 authority。

## Hard Allowlist

- source：`scripts/pantheon_content_capacity_guard.py`
- test：`tests/test_pantheon_content_capacity_guard.py`
- 本卡與同名小寫 evidence 目錄。
- 只有證據證明不可避免時，才可加入一個既有直接相關 capacity/activation test file；必須先在 RESULT 說明 `why_not_less`。預設不使用。

## Required TDD / Verification

1. 保存 exact production-shaped fresh/no-future-run RED。
2. 完整 `coordinator --install → publisher --install → capacity --install-recovery-stage`：selector雙側缺席轉 GREEN。
3. historical valid selector維持 GREEN。
4. stale、missing-one-side、mismatch、empty、malformed selector皆 RED。
5. Rule24、manifest/generation、barrier、model route、stage/live tuple、old-live cohort、stopped topology、normal/recovery drift持續 fail closed。
6. production-shaped candidate雙跑 deterministic、production/live bytes before==after、external calls 0。
7. 跑 targeted、affected broad baseline/candidate parity、py_compile、`git diff --check`、anti-expansion scan。

## Forbidden

- preallocate、placeholder、猜 future run、手改 stage、capacity-first bypass。
- 修改 scheduler、publisher installer、coordinator aggregate、promotion、manifest schema或其他 source。
- 新 FSM／registry／DB／ledger／migration／authority。
- per-lane／per-installer特判。
- production/install/activate/scheduler/provider/reviewer/publisher/publish/tag/push/deploy mutation。
- commit／push。

## Stop Conditions

- 需要 allowlist 外 source/test：立即停在 evidence，不擴 scope。
- 發現第二個獨立缺口：立即回 BLOCKED，不逐症狀修補。
- affected broad candidate與baseline failure node/digest不一致：立即停，不掩蓋。

## Deliverable

- `pantheon_publisher_exact_run_activation_optionality_repair_20260829/RESULT.md`
- RED/GREEN、negative matrix、baseline parity、diff/LOC、anti-expansion與production immutability receipts。
- `why_not_less`、`why_not_more`、`do_not_absorb`。
- 終態：`RE_REVIEW_REQUESTED` 或 `BLOCKED`。
