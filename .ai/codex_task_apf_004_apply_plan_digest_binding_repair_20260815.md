# APF-004-APPLY-PLAN-DIGEST-BINDING-REPAIR

## 工作名稱

修復 aggregate runtime promotion `apply` 的 plan digest 綁定。

## 目的與 blocker

- `Gate A` 已於 candidate `92201049dece9291e21e8ea90ebbc7f27d2440a6` fail-closed，Reviewer `APPROVED`。
- blocker：public `apply` subparser 不接受 `--expected-plan-digest`，因此核准的 exact argv 無法合法執行。
- 修復後只交 code candidate；不得執行 production apply，也不得沿用先前 Gate A 授權。

## 固定基線

- base／`origin/main`：`79ae1c33d8991ce1c51405572289003710bdf81b`
- blocker evidence：`artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/gate_a_aggregate_promotion_apply_20260815/`
- chain：既有 aggregate runtime promotion Implementation → Reviewer。

## 可改範圍

- `scripts/pantheon_content_runtime_promotion.py`
- `tests/test_pantheon_content_runtime_promotion.py`
- 唯一 evidence root：
  `artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/apply_plan_digest_binding_repair_20260815/`

## 禁止範圍

- 禁止讀寫 production runtime、actor、manifest、private stage、queue、state、launchd。
- 禁止呼叫 public `plan/apply/rollback/finalize/status` 對 production 路徑。
- 禁止 Gate A 重試、Gate B、downstream、發文、deploy、push。
- 禁止修改其他 source、共用 registry、metadata 或既有 evidence。
- 所有測試只准 `tmp_path`／fake repos／fake runtime。

## 必要行為

1. public `apply` 必須要求 `--expected-plan-digest`；缺少時 argparse fail-closed。
2. `apply_promotion` 必須要求呼叫者提供 expected digest。
3. `apply_promotion` 先計算當下 plan；digest 不符立即 `PromotionError("plan digest mismatch")`。
4. mismatch 判定必須早於 `transaction_root.mkdir(...)`、receipt、rollback bundle及任何 actor／manifest／stage mutation。
5. digest 相符時維持既有狀態機、rollback、crash recovery、finalize 行為。
6. CLI `main()` 必須把 `args.expected_plan_digest` 傳入 `apply_promotion`。

## TDD／驗收

- 先補 RED：
  - `apply --help`／parser 契約顯示 required expected digest。
  - wrong digest → `plan digest mismatch`，transaction root 不存在，runtime snapshot 不變。
  - correct digest →既有 success path 通過。
- 更新既有 direct `apply_promotion` 測試，全部顯式傳入由 `plan_promotion(request)["plan_digest"]` 取得的 digest；不得用硬編碼繞過。
- 跑：
  - `uv run --python .venv/bin/python pytest -q tests/test_pantheon_content_runtime_promotion.py`
  - 受影響 runtime promotion 測試（若另有檔案，以 `rg` 限域找出）。
  - `git diff --check`
- evidence 至少含：RED/GREEN、測試摘要、production mutation=0、sanitizer、artifact digests。

## 交付

- 單一 candidate commit；不 amend、不 push。
- 回：candidate SHA、變更檔、RED/GREEN、測試數、production mutation=0、剩餘風險。
- 完成後停止，等待原 Reviewer 唯讀審查。
