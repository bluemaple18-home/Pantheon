---
id: APF-004-AGGREGATE-RUNTIME-PROMOTION-ENTRYPOINT
title: 新增可回滾的 aggregate runtime promotion CLI
status: ready
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: implementation
cycle: 1
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
model_reason: preflight 已固定 actor/manifest/stage transaction 與 rollback 契約，屬核心 bounded state-machine 實作
parent_candidate: 925abf4094
traces_to:
  - FR-AGG-PROMOTE-001
  - SC-AGG-PROMOTE-001
  - SC-AGG-PROMOTE-002
  - SC-AGG-PROMOTE-003
---

# APF-004-AGGREGATE-RUNTIME-PROMOTION-ENTRYPOINT｜新增可回滾 promotion CLI

## 需求追溯

- `FR-AGG-PROMOTE-001`：提供唯一 public CLI，把 actor、production manifest、private stage 納入同一 promotion transaction。
- `SC-AGG-PROMOTE-001`：plan-only deterministic、零寫入，完整列出 identity、write set、backup/rollback 與 postchecks。
- `SC-AGG-PROMOTE-002`：apply 任一階段失敗時，以同一 correlation 恢復 stage→manifest→actor；rollback bundle 在 finalize 前持久存在。
- `SC-AGG-PROMOTE-003`：success postchecks 通過後才可 finalize 清理 backup；重跑／中斷可依 receipt fail-closed resume 或 rollback。
- blocking evidence：`artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/single_create_runtime_promotion_preflight_20260815/`。

## 任務五行卡

- 目標：實作 aggregate runtime promotion public CLI 與 deterministic tests，關閉 actor recovery 成功後過早刪 backup、manifest/stage 分離無 cross-state rollback 的 blocker。
- 可改：新增 `scripts/pantheon_content_runtime_promotion.py`、新增對應 test；必要時限域修改 `scripts/pantheon_content_actor_recovery.py` 與其直接 tests、runtime manifest helper 與三個 installer 的 test seam；證據可寫 `.work/APF-004-AGGREGATE-RUNTIME-PROMOTION-ENTRYPOINT/**`。
- 禁止：不得實際 deploy/install/copy production actor、不得改 live manifest/plist/stage/launchctl、不得 create-run plan/apply、外部模型/publish/tag/push/schedule；不得修改與 promotion transaction 無關的 runtime code。
- 驗收：RED→GREEN；public CLI 支援 `plan/apply/rollback/finalize/status`；persistent transaction receipt＋rollback bundle；完整 failure matrix；existing actor recovery/manifest/installers regression；`git diff --check`。
- 證據：candidate SHA、state-machine schema、RED/GREEN、failure injection matrix、allowlist、sanitizer、production mutation=0。

## 固定 public contract

1. CLI 為 `python -m scripts.pantheon_content_runtime_promotion <plan|apply|rollback|finalize|status>`；不得把多步驟 shell 範例冒充 aggregate entrypoint。
2. 輸入必須鎖定：source repo/target SHA、expected current actor SHA、origin、runtime root、manifest path、private stage root、expected current manifest/stage digests、new generation、correlation ID、authorization digest、capacity receipt digest。
3. `plan` 純計算，禁止 mkdir/write/subprocess mutation；輸出 deterministic plan digest、ordered stages、exact write set、backup set、rollback order、postchecks。
4. transaction state forward-only：`PREPARED → ACTOR_PROMOTED → MANIFEST_WRITTEN → STAGE_INSTALLED → POSTCHECK_PASSED → COMMITTED`。
5. `apply` 每一階段先核對 expected identity；任何 drift 或 failure 進 rollback。rollback 反向順序固定：private stage、manifest、actor。
6. actor backup、manifest bytes/metadata、stage tree/metadata 與 transaction receipt 必須保留到 `POSTCHECK_PASSED`；只有獨立 `finalize` 且 authorization/plan/correlation 完全相符才可清理。
7. crash/retry：已有 receipt 時不得另建 transaction；`status` 回可重算狀態；`apply` 只能安全 resume 或要求 rollback，不能覆蓋未知 partial state。
8. actor replace 復用既有 verified primitives；manifest/stage 復用既有 public helper/seam。不得用 ad-hoc `cp`、手改 plist/JSON 或第二套 installer。
9. postchecks 至少驗 actor clean/HEAD/origin、manifest digest/actor head/generation、stage matching manifest/generation/7 ACK、queue=0、state 只有既有 barrier、run/gsc-copy=0、worker labels inert、capacity stop-loss PASS。
10. apply/rollback/finalize 均需 explicit authorization digest；tests 使用 temp roots、fake subprocess/seams，不得觸碰 production paths。

## TDD 與 failure matrix

先針對 public CLI 寫 RED：

- plan zero-write/deterministic；invalid identity/overlap/path escape fail closed。
- actor promotion failure、manifest write failure、每個 stage installer failure、postcheck failure都恢復完整 before snapshot。
- crash after each durable state 可 status/recover；duplicate apply/finalize authorization drift 拒絕。
- success 保留 rollback bundle直到 finalize；finalize 後 receipt 保留 audit、backup 清理。
- existing `pantheon_content_actor_recovery` positive/negative 不退化。

驗證至少包含新 test module、受影響 recovery/manifest/installer tests、`python -m ... --help`、`git diff --check`。不得跑 live command。

## 停損與交付

- 若需改 allowlist 外 code/config，回 `BLOCKED_SCOPE_CHANGE`。
- 若既有 primitive 無法在不複製 writer 的前提下提供 deferred finalize，回 `BLOCKED_ARCHITECTURE_FORK`，附 source seam 證據。
- 建立單一 candidate commit，不 amend、不 push；回 SHA、changed files、RED/GREEN/failure matrix、production mutation=0。
