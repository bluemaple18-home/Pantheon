---
id: APF-004-RUNTIME-PROMOTION-TO-MANIFEST-AUTHORITY-REPAIR-20260815
title: 將正式 runtime promotion 到 Publisher authority 修復版
status: authorized_plan
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: implementation
cycle: 1
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
model_reason: 既有 public promotion path 的固定規格 production transaction
parent_candidate: 13b4f53354
---

# APF-004｜Runtime promotion to manifest-authority repair

## 使用者授權

- 使用者已明確授權：單次 governed runtime promotion 到 `a6c4b798a6aeab61fc3e977d326731c1aec9a181`，其後只 reload Publisher 並跑一次 fresh capacity。
- 不授權發文、create run、select、business transaction、tag、push、排程擴量或自動重試。
- promotion 必須使用既有 public deterministic `plan → apply → independent review → finalize` 路徑；不得手動複製、cherry-pick production actor、直接改 manifest 或 stage。

## 已核准基線

- Current formal actor：`28b8b84b6dfa319d8151aac3bc1a6a819ae82aa1`。
- Current formal manifest digest：`c57a95aa72d8e01c676e50a9a54156da04ef1f9c3b4c86fa788819200df586a2`。
- Target source：`a6c4b798a6aeab61fc3e977d326731c1aec9a181`。
- Target 已包含 Reviewer APPROVED 的 manifest-authorized publisher installer/public preflight 修復。
- Blocker evidence：`artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/publisher_launchagent_identity_repair_after_manifest_authority_20260815/`。
- Reviewer verdict：governed runtime promotion 是最小安全 frontier。

## Phase 1：deterministic plan（本次先執行）

1. clean detached checkout exact `origin/main`，確認 target source 可讀、clean、remote identity exact。
2. 重驗 storage capacity、resource runtime、queue/state、actor/manifest/private-stage、transaction roots與 stop-loss；任一不確定即 `BLOCKED_BEFORE_MUTATION`。
3. 只用既有 public `scripts.pantheon_content_runtime_promotion plan` 產生 target=`a6c4...` 的 deterministic plan；不得 apply。
4. 鎖定 generation、correlation、plan digest、exact apply argv digest、current/target identity、transaction root與 rollback contract。
5. 新 evidence root：
   `artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/runtime_promotion_to_manifest_authority_repair_plan_20260815/`
6. JSON、digests、sanitizer、`git diff --check`；candidate commit，不 amend、不 push。
7. 回 `PLAN_READY` 或 `BLOCKED_BEFORE_MUTATION`，附 candidate SHA、plan digest、exact argv digest、production mutation `0`、clean。

## Phase 2：apply（Reviewer 核准 plan 後）

- 同一 Executor thread、同一 immutable tuple、同一使用者授權。
- 使用 plan 鎖定的 exact public apply argv，apply 恰好一次；呼叫前 durable state 記錄 attempt consumed。
- 非零或不確定結果不得重試；只接受 public CLI 自身原子 rollback。
- 成功停在 `POSTCHECK_PASSED`，不直接 finalize。
- 唯一新 evidence root：
  `artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/runtime_promotion_to_manifest_authority_repair_apply_20260815/`

## Phase 3：review／finalize

- Apply candidate 必須由既有 canonical Reviewer 唯讀核准。
- 核准後同一 Executor 只執行 public finalize 一次，移除 transaction/rollback bundle並保存 finalize evidence。
- 唯一新 evidence root：
  `artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/runtime_promotion_to_manifest_authority_repair_finalize_20260815/`
- Finalize 後再由 Reviewer 核對；未核准前不得進 Publisher reload。

## 全程禁止

- 不得手動改 production actor、manifest、stage、barrier或 transaction root。
- 不得第二次 plan/apply/finalize 重播同 root，不得 kickstart或擴其他 LaunchAgent。
- publication/create/run/select/business transaction/tag/push/schedule 全為 `0`。
- 不碰使用者舊 dirty workspace。

## 後續

- Runtime finalize Reviewer APPROVED 且 evidence 整合後，回原 Repair thread執行已授權的 Publisher-only reload＋fresh capacity。
- Capacity PASS 後才回原 Gate B Executor；本卡本身不授權發文。
