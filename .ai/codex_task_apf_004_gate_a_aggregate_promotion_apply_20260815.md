---
id: APF-004-GATE-A-AGGREGATE-PROMOTION-APPLY
title: 執行 Gate A aggregate runtime promotion
status: awaiting_user_authorization
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: implementation
cycle: 1
thickness: strict
risk: critical
model: gpt-5.6-sol
reasoning: high
model_reason: production actor/manifest/private-stage transaction 具高回退成本，需 critical execution supervision
parent_candidate: 4b02e2038f1102b0f1601f5471e7bfbac2c6ea60
traces_to:
  - FR-AGG-PROMOTE-APPLY-001
  - SC-AGG-PROMOTE-APPLY-001
  - SC-AGG-PROMOTE-ROLLBACK-001
---

# APF-004｜Gate A aggregate runtime promotion apply

## 啟動閘門

- 本卡建立／提交／推送不等於 apply 授權。
- 只有主線收到使用者對「Gate A production apply；不含 finalize、Gate B、發文」的明確核准後，才可把 `status` 視為 activated 並派工。
- 未核准前：production mutation=0，不得執行本卡任何 production snapshot 以外動作。

## 任務五行卡

- 目標：以已核准 plan digest 執行一次 aggregate `apply`，原子 promotion production actor＋manifest＋private stage，通過 postchecks 後停在 `POSTCHECK_PASSED`，保留 rollback bundle。
- 可寫：public CLI 固定 transaction root；證據只可寫 `artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/gate_a_aggregate_promotion_apply_20260815/**`。
- 禁止：不得 `finalize`；不得第二次 apply；不得手動 copy/manifest/plist/stage/launchctl；不得 Gate B create-run、外部模型、select/publish/transaction/tag/push/schedule/發文；不得改 code/config/tests。
- 驗收：`APPLY_POSTCHECK_PASSED | APPLY_ROLLED_BACK | BLOCKED_BEFORE_MUTATION`；actor/manifest/stage identity exact、queue/state business writes=0、7 ACK、rollback bundle durable、production downstream=0。
- 交付：單一 evidence candidate commit，不 amend、不 push；回 SHA、transaction state、plan digest、receipt path、mutation matrix、後續 finalize 建議。

## 鎖定 payload

- plan evidence：`artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/aggregate_runtime_promotion_plan_replay_raw_capacity_20260815/`。
- expected plan digest：`55771aa1d934d01e65233cc85889b4edc8834d6f3fd9593e0bbcc40a50e25aa6`。
- source SHA：`0bf78f0b0cac6743fef4dae4aa76e21ebbaffe35`。
- current actor SHA：`9d8573e9624d09748d029cab7d0209e1e14730c9`。
- current manifest digest：`effd15bd06b242201d5e297016e58ba5f96b6d82f866a9ee03584cb3b0f2abfc`。
- current stage digest：`3a856a54d8bb5f8c3d2554ce09f68820f9e2e28e1515c4f312bb5d5b16c21c78`。
- target identity：`gate2-actor:0bf78f0b0cac6743fef4dae4aa76e21ebbaffe35:activation-only`。
- target generation：`g2-0bf78f0b0c-20260814T183109Z`。
- correlation：`apf004-aggregate-plan-raw-capacity-0bf78f0b0c-20260814T183109Z`。
- target runtime digest：`4b5b4f0c818f80dd3fcdd8a02d11060e3f7d2a22fc43e532f246fd9b87461efb`。
- authorization digest：`cdbc25281df48b7c057ca0eaac7afe27da51ed245b37d78545418d1ba51949fb`。
- capacity receipt digest：`7fa0036a4ce81a173bc1f16c964829d82822d9fa6a3bb4c92793b222d4954f34`。
- transaction root：`<runtime-root>/backups/apf004-aggregate-promotion-transaction-0bf78f0b0c-20260815-raw-capacity`。

所有其餘 argv 必須逐欄取自 `plan-attempt-1.json.argv`；只允許把 subcommand `plan` 改為 `apply`，並新增 `--expected-plan-digest` 上述值。不得重算 generation/correlation、改 path、改 receipt 或改 target。

## 執行前 fail-closed

1. 先核對 plan evidence/12 JSON/digest manifest/sanitizer仍 PASS，candidate已在 `origin/main`。
2. source worktree、actor、manifest、stage、capacity receipt、Python executable identity、queue/state/run/gsc-copy、worker labels與host capacity須與鎖定 plan一致。
3. transaction root 執行前必須不存在；若存在，停止並回 `BLOCKED_BEFORE_MUTATION`，不得刪除或覆蓋。
4. 任一 expected current digest/identity 漂移，停止；不得重跑 plan或另造 payload。
5. 保存完整 before snapshot、禁止動作計數與 apply exact argv hash。

## 唯一允許 mutation

1. 只執行一次 public CLI `python -m scripts.pantheon_content_runtime_promotion apply ... --expected-plan-digest 55771...`。
2. 允許 state machine：`PREPARED → ACTOR_PROMOTED → MANIFEST_WRITTEN → STAGE_INSTALLED → POSTCHECK_PASSED`。
3. 任一步失敗必須由同一 CLI 自動逆序 rollback：stage → manifest → actor，最終證明 before snapshot 完整恢復；不得手動修。
4. apply 成功後禁止 `finalize`，rollback bundle／receipt／before snapshot必須保留供獨立 Reviewer。

## Apply 後驗收

1. actor clean、HEAD=source SHA、origin exact。
2. manifest digest/actor head/generation/target identity exact。
3. private stage matching generation，readiness ACK=7/7，activation barrier exact。
4. queue空、run/gsc-copy=0、state只允許既有/新 barrier、worker business child I/O=0。
5. capacity receipt仍 PASS；transaction receipt狀態=`POSTCHECK_PASSED`；rollback bundle actor/manifest/stage/barrier完整。
6. external model、select/publish/transaction/tag/push/schedule/發文全部為0。
7. evidence只用 placeholder，sanitizer/JSON/digests/`git diff --check`必須 PASS。

## 下一閘門

- 本卡成功後，先獨立 Reviewer 驗收 production state與 rollback bundle。
- Reviewer核准前不得 finalize；finalize須另卡、另授權。
- Gate B single plan-only與發文仍不在範圍。
