---
card_id: CARD-PANTHEON-GEMINI-RATE-LIMIT-THROUGHPUT-REVIEW-001
chain_id: PANTHEON-GEMINI-RATE-LIMIT-THROUGHPUT-20260728
type: independent-review
status: TARGETED_REVIEW_DELIVERED
decision: TARGETED_REVIEW_GO
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
review_cycle: 1
targeted_re_review: true
repair_budget: 0
original_candidate: 7e38274efda6b76eb2e5baf27b62d20bb9614292
repair_candidate: 74db4fbb6e28936376ff4b02e021362b04386af7
required_direct_parent: 7e38274efda6b76eb2e5baf27b62d20bb9614292
original_review_evidence_commit: 3adf0746a6810d3a90e26cd3e966300c6d94ec66
repair_thread: 019fa922-58c6-7fb2-98d9-c2785fbd11b0
review_thread: 019fa913-8132-7280-9b81-430b2898c4b2
---

# Gemini rate-limit throughput targeted re-review

## Scope

這是同一 chain、同一 Reviewer identity 的 finding closure，只重驗：

- `PGR-REV-001`：credential/ordinal/provider ordering。
- `PGR-REV-002`：coordinator 與四 lane 的 installer closed contract。

未新增 goalpost，未重跑 Publisher，未修改 production code、tests 或 Repair
evidence。

## Provisioning receipt

- Reviewer worktree 在 checkout 前 clean：PASS
- detached HEAD 精確等於 Repair candidate：PASS
- direct parent 精確等於 required parent：PASS
- Repair changed files：精確 9 檔，missing=[]、unexpected=[]
- `index.lock`：不存在

## Finding closure

### PGR-REV-001 — RESOLVED

`admission.commit()` 現在先於 selected credential open/read。Fresh injected
commit-failure regression 證明：

- credential open/read：0
- ordinal durable：false
- provider construction/call：0
- closed terminal failure：恰一個
- production attempt：恰一個且 status=`failed`
- raw exception、credential path/value：未持久化

成功路徑的 provider construction 與 transport 均在 allocator admission context
退出後執行；code inspection 與 lock-boundary regression 都通過。

### PGR-REV-002 — RESOLVED

Production pool opt-in 時，coordinator 與四條 lane 的 pool、state、bounded
cooldown 精確一致。Coordinator plist example 與 installer conditional injection
一致；closed validation 先於任何 plist/control mutation。`new_only=0` 的
shared-root runner 取得相同 contract；opt-out 不要求或注入 pool/state。

## Fresh verification

- finding-specific direct regressions：`6 passed`
- allocator/outbox/coordinator full suites：`171 passed`
- installer `bash -n`：PASS
- coordinator/lane plist lint：PASS
- `git diff --check`：PASS
- exact 9-file Repair allowlist：PASS
- secret、absolute-local-path、debug-marker scans：zero matches

Repair diff 未修改 multilingual production/test path，沒有相較 parent 的新
因果證據；既有兩個 `missing_policy_contract` 保持 baseline exception，不升格
為 finding。

## Decision

`TARGETED_REVIEW_GO`

兩個原 P1 均已 resolved，沒有新增 finding。這個 GO 只解除本 targeted Review
的阻塞，不代表已整合、已部署、已啟用 canary、已發布或 production throughput
已改善。

## Historical procedure note

Original Review 曾建立兩個 ephemeral synthetic probe，完成後已刪除；本次
targeted re-review 未建立額外 probe file。最終持久化變更仍只限本 Review card
與原 Review evidence root。
