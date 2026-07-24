---
card_id: CARD-PANTHEON-PUBLISHER-DEADLOCK-REPAIR-03-20260725
status: READY_FOR_REVIEW
type: repair
project: Pantheon
chain: pantheon-publisher-deadlock-repair-20260724
generation: Repair-3
created_at: 2026-07-25
owner: mainline
---

# Pantheon Publisher Deadlock Repair-3

## Authorization

使用者已明確同意突破原 Repair-2 limit 繼續修復。此授權只涵蓋
`PPD-R-001`，不授權 Gemini V4 default promotion。

## Fixed boundary

- Base：`473556cc00e6a620491897ade606c72b90caac47`
- Finding：`PPD-R-001`
- V4：必須維持 shadow。
- 不得操作正式 actor、queue、ledger、launchd、push 或 deploy，直到修復通過驗證。

## Root cause

共用 worktree 的 before/after observation 無法分辨 publisher 與 non-cooperative
concurrent writer 在同一 helper attribution window 內寫入的 bytes。

## Required repair

正式 publisher mutation 必須在隔離 transaction worktree 執行。正式 actor 只可在：

1. 原 HEAD 仍精確等於 transaction base；
2. worktree 仍 clean；
3. transaction 已成功產生 commit；

三項同時成立時，以 compare-and-swap 更新。失敗 transaction 不得 rollback 或覆寫
正式 actor 的 bytes。

## Acceptance

- reviewer 的 capture-window concurrent edit 反例在 production transaction seam 轉綠。
- 正式 actor 在 transaction 期間注入 concurrent edit 時，bytes 保留且 actor sync
  fail-closed。
- 成功 transaction 可同步 actor 並讓後續 create／rewrite／translation phase 繼續。
- publisher focused、SEO／多語／web、full pytest、py_compile、debug marker scan、
  `git diff --check` 全部通過。
- V4 shadow invariant 不變。

## Implementation result

- 正式 CLI 非 dry-run 路徑從最新 `origin/main` 建立單輪隔離 worktree。
- publisher 的 create／rewrite／translation、測試、commit 與 push 全在隔離
  worktree 執行。
- 正式 actor 在整輪中不切 HEAD、不套 patch、不 rollback；actor concurrent bytes
  不會被 transaction cleanup 觸碰。
- transaction worktree 結束後移除；下一輪重新從最新 `origin/main` 建立。
