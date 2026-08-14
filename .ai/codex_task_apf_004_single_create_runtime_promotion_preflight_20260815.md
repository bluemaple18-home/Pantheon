---
id: APF-004-SINGLE-CREATE-RUNTIME-PROMOTION-PREFLIGHT
title: 準備單筆 create-only runtime promotion
status: ready
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: implementation
cycle: 1
thickness: strict
risk: critical
model: gpt-5.6-sol
reasoning: high
model_reason: production runtime promotion 涉及 canonical actor/manifest/stage authority、rollback 與高回退成本，仍有 source-to-runtime identity fork 待收斂
parent_candidate: fbecc03aba
traces_to:
  - FR-RUNTIME-PROMOTE-001
  - SC-RUNTIME-PROMOTE-001
  - SC-RUNTIME-PROMOTE-002
---

# APF-004-SINGLE-CREATE-RUNTIME-PROMOTION-PREFLIGHT｜準備 runtime promotion

## 需求追溯

- `FR-RUNTIME-PROMOTE-001`：把已核准的新 single-source entrypoint 轉為一次性、可回滾、fail-closed 的正式 runtime promotion payload。
- `SC-RUNTIME-PROMOTE-001`：鎖定唯一 source SHA、actor target、manifest/generation、allowlist、backup、rollback 與 promotion 後 zero-write verification。
- `SC-RUNTIME-PROMOTE-002`：preflight 全程 mutation=0；不得以 copy、dirty checkout、手改 manifest 或 launchctl 操作冒充 promotion readiness。
- blocking edges：`2ad9af5b44` feature 已進 origin/main；`fbecc03aba` blocker evidence 已進 origin/main。正式 actor `9d8573e962` 尚缺入口。

## 任務五行卡

- 目標：唯讀收斂 source→production actor→runtime manifest→private stage→zero-write gate 的 exact promotion payload。
- 可寫：`artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/single_create_runtime_promotion_preflight_20260815/**`。
- 禁止：不得 deploy/install/copy/rebase/reset actor、不得寫 manifest/plist/stage、不得 launchctl bootstrap/kickstart/bootout、不得 plan/apply create-run、不得外部模型/publish/tag/push/schedule；不得改 code/config/tests。
- 驗收：輸出 `PROMOTION_PAYLOAD_READY | BLOCKED`；READY 必須唯一化 target SHA、正式 promotion 入口、I/O、identity/correlation、backup/rollback、capacity stop-loss 與 post-promotion zero-write checks。
- 證據：source/runtime/manifest/actor digests、content-equivalence、capacity、clean/ancestry、正式工具 `--help` 或 source contract、exact payload schema、sanitizer/diff-check。

## 固定檢查

1. 以 `origin/main` 當前 SHA 為唯一 source authority；確認它包含 `2ad9af5b44` 且 source 定義 `create_single_source_run_adapter`。
2. 唯讀核對 production runtime root、actor HEAD/clean/origin、runtime manifest、queue/state/run roots、stage identity、activation barrier、host free、project bytes/files、RSS/swap 可觀測性。
3. 查明 repo 既有正式 runtime promotion/install/reload 工具；只能使用 public CLI/source contract，不得提出 ad-hoc `cp` 或手改 manifest。
4. payload 必須分兩個 confirmation gates：A) promotion only；B) promotion 後 single plan-only。不得把 create-run apply 混入。
5. promotion payload 必須包含 backup path/schema、expected actor/manifest/source digests、new generation/correlation、allowlist、pre/post gates、rollback、stop-loss、重入語意與失敗停止點。
6. 缺正式 promotion 入口、actor dirty、容量不安全、manifest authority 不唯一或 rollback 不可驗證，回 `BLOCKED`；不得自行修 code 或執行 mutation。
7. 所有共享 artifacts 使用 `<repo-root>`／`<repo-parent>`；本機路徑只存在 raw command context，不得落盤。

## 交付

建立單一 evidence candidate commit，不 amend、不 push。回 candidate SHA、verdict、唯一 target identity、promotion 工具、mutation summary=0 與後續所需核准。
