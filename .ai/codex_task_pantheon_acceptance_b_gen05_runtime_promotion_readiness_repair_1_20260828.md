---
id: REPAIR-PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION-READINESS-20260828
title: 修復第五代執行環境升版就緒證據
status: ready
chain_id: PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION
role: repair
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 三個 P1 都位於 promotion readiness authority 與可重現 evidence bytes；範圍固定但會影響後續 production promotion 授權
parent_candidate: 2b9343bc5011f82e5a9d2a81cf1d03a61d80c97d
review_commit: 125b1e87c2e32ec683b5636523dbcffc642ccafc
---

# Pantheon Acceptance B：gen05 runtime promotion readiness bounded Repair

## 已接受 Findings

- `P1-001`：候選 exact plan argv 綁定已不存在的 producer worktree 與 raw capacity receipt path，正式 promotion plan無法在獨立 worktree 重現。
- `P1-002`：planner authority 使用 raw capacity digest `6def7497...`，repo committed portable receipt bytes 的 SHA256 是 `28ffddce...`，digest／bytes契約不一致。
- `P1-003`：`evidence-index.json` 索引兩個未提交的 `.git/...lock` paths，committed evidence set 不完整。
- Reviewer result：`artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION-READINESS-REVIEW-20260827.md`。

## 目標

只修復 readiness evidence 的 portability、capacity authority 與 evidence index，使正式 promotion plan 可從任意乾淨 Pantheon worktree，以 committed artifact bytes 和既有正式入口重現同一 `READY_TO_APPLY` 結果。

本 Repair 不重做 gen04/gen05 RCA、topology、Rule 24／25 架構，也不執行 promotion 或 production mutation。

## 可改檔案

- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_runtime_promotion_readiness_20260827/**`
- `artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION-READINESS-20260827.md`
- 唯一 Repair receipt：`artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION-READINESS-REPAIR-1-20260828.md`
- task-owned `/private/tmp` synthetic outputs；不得把本機絕對路徑提交進 repo。

## 禁止範圍

- 不得修改 code、config、tests、queue/state、continuation、runtime manifest、private stage、production artifacts 或 Reviewer result。
- 不得執行 promotion apply/finalize、provider、production gen05、publish、transaction、tag、push、deploy、launchctl 或 service mutation。
- 不得刪除 failed evidence 來掩蓋 finding；需由 supersession／index 明確保留 audit continuity。
- 不得手寫假的 Rule24 receipt、改 digest 欄位硬湊、略過正式 planner validation，或把 producer worktree 複製成 authority。
- 若既有正式工具無法產生 target-bound、committed-bytes-valid 的 capacity receipt，立即停止並回報單一 code seam；不得自行擴成 code Repair。

## Repair 契約

1. 使用既有正式 Rule24 capacity seam 產生 fresh、target-bound 的 capacity receipt；正式 planner 驗證的 exact bytes 必須提交，receipt SHA256、planner digest、readiness decision 與 argv 全部一致。
2. committed replay 不得依賴 producer worktree。source repo、capacity receipt及其他輸入必須由 current checkout 加 repo-relative committed artifacts deterministic resolve；共享 artifact不得含可照抄的本機絕對路徑。
3. 從另一個乾淨獨立 worktree 重跑正式 promotion plan入口，必須得到與 committed plan相同的 target、current actor／manifest／stage、plan digest、target manifest digest、generation 與 `READY_TO_APPLY`。
4. 重建 evidence index；每個 indexed path都必須是可提交 regular file，實際存在於 candidate tree，byte length與 SHA256逐項吻合。不得索引 `.git` metadata 或 lock file。
5. 保留並重驗 Rule24 兩 cycles、host free、RSS、swap、reclamation、stop-loss，以及 Rule25 七段、正向 READY、負向 BLOCKED、`canary_created=false`。
6. 重驗 continuation：`next_generation=5`、gen04 abandoned/non-resumable、gen05 source-ref-map存在、gen06不存在。
7. production protected bytes before==after，promotion/provider/publish/transaction/tag/push/deploy/service mutation counters全部為 0。

## 驗收

- 先作 task-semantic CodeGraph query；無結果或失敗才限域 `rg`。
- `P1-001` regression：候選原 exact argv 必須 RED；修復後 committed portable replay必須 GREEN，且在第二個乾淨 worktree 重跑一致。
- `P1-002` regression：正式 planner實際讀取的 receipt bytes SHA256 必須等於傳入 digest及 committed decision authority。
- `P1-003` regression：evidence index `missing=0`、`digest_mismatch=0`、不得含 `.git/` path。
- 重跑原 candidate列出的 JSON/schema/checksum/official gates與受影響 tests。
- `git diff --check` 通過；changed files必須完全落在 allowlist。
- 建立單一 Repair candidate commit，不 amend、不 push；回傳 full SHA、parent、finding-to-regression mapping、tests與 residual risk。

## 交付與下一步

- 交付後回同一 Reviewer thread，只 re-review `P1-001`、`P1-002`、`P1-003` 及 Repair regression；不得新增 P2/P3 移動球門。
- Reviewer GO 前不得整合、promotion 或 production mutation。
