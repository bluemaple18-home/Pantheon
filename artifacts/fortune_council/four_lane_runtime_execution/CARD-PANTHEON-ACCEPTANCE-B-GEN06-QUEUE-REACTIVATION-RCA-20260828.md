---
status: COMPLETE
owner: codex
task: pantheon_acceptance_b_gen06_queue_reactivation_rca_20260828
created_at: 2026-08-28T18:25:49+08:00
scope: read_only_rca
---

# Pantheon Acceptance B gen06 queue reactivation RCA

## 目標

只讀閉合 gen06 terminal Reviewer REJECT 後，`authorize-next-generation-after-reviewer-reject` 已讓 run-local continuation 進入 `active,next_generation=6`，但正式 coordinator exact cycle 回 `runner.idle`、四 lane `active=0` 的根因。

## 邊界

- 不改 source。
- 不改 production runtime、queue registry、run state、publisher、tag、content。
- 不 retry provider、不建立 gen06、不建立 gen07。
- 可建立本卡與本輪 RCA result artifact。

## 驗收

- 回答最後成功先例或明確無先例。
- 回答 first failing commit 或機制。
- 回答 authoritative owner 與 durable invariant。
- 提供 provider=0、temp copy 可重跑 RED harness。
- 判定 DATA_ONLY 與唯一 bounded Repair frontier。
