---
id: CARD-AI-CORE-RULE21-CREATED-UNBOUND-TITLE-MISMATCH-RECOVERY-20260828
status: backlog
owner: ai-core
source_project: Pantheon
type: measured_gap
risk: control_plane
recommended_model: gpt-5.5
recommended_reasoning: high
---

# AI Core Rule 21：created-unbound 標題改寫 recovery 缺口

## 目的

讓正式 thread 已建立、但 runtime title 被平台改寫而無法 activation 的 Reviewer／Repair，可以在外部明確授權封存、worktree 已安全移除後，合法終結舊 reservation 並釋放唯一 role slot。

本卡只記錄 ai-core backlog 缺口，不在 Pantheon 實作、不啟動 Repair，也不授權繞過 Rule 21。

## 實測事故

- Repo：Pantheon。
- Chain：`PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION`。
- Role：唯一 Reviewer。
- Card：`REVIEW-PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION-READINESS-20260827-RETRY-1`。
- Dispatch key：`v1:b2f94d1a40ff344dd440f5c7ec9b5d819bef45154295774837af0e9ca6b8393a`。
- Formal thread：`01a043de-92b2-7e73-8780-8cbb3fa78cbe`。
- Source SHA：`d0b2bbe05950291e04490b915bc35e1557ac3196`。
- Canonical create-time title：`↳ 審查｜驗證第五代執行環境升版就緒度`。
- Runtime 現象：正式 thread 的 title 被整段 `<codex_delegation>…</codex_delegation>` prompt 取代；不是 canonical title，也不是單純空值。
- Rule 21 activation 正確要求 exact title preservation，因此主線未 activation、未手動改名、未送 activation token。
- Owner 已明確授權封存與 recovery；formal thread 已封存且不可見，對應 worktree 已不存在且未註冊，分支仍保留候選 commit。
- Durable reservation 仍為 `CREATING`、`activation_status=NOT_ATTEMPTED`、`next_action=ACTIVATE_SAME_THREAD`，唯一 Reviewer role slot 未釋放。

## 根因邊界

平台 title 改寫是形成事件；Rule 21 fail-closed 拒絕 activation 是正確行為。

已量測的 ai-core 缺口位於 created-unbound recovery：現行 `recover-created-unbound` 有 `FORMAL_THREAD_TITLE_MISSING_ARCHIVED` 分支，但沒有等價且受限的「runtime title mismatch／rewrite 已封存」分支。當 reservation 尚在 `CREATING` 且 project/source 正確時，既有 recovery evidence validator 無合法 reason code 可接受，因此無法 terminalize 舊 reservation 或建立唯一 `RETRY-N` replacement。

這不是 Pantheon runtime、gen05 lifecycle、promotion、publisher 或 production content 缺口。

## 最小 sufficient slice

### 必須支援

- 只接受 Reviewer／Repair 的 exact owner、exact dispatch、exact formal thread 與下一代 `RETRY-N` identity。
- 只接受 create-time canonical title 與已保存 runtime title 明確不一致的 measured evidence。
- 必須證明 formal thread 已由外部明確授權封存且不可見。
- 必須證明 worktree 不存在、未註冊、無 dirty／unique work，候選成果仍有可追溯 ref。
- project、source、identity、thread、create request digest 任一漂移即拒絕。
- 成功後原子寫入 `ABORTED_PRECREATE`、terminal tombstone、evidence digest、`role_slot_released=true` 與唯一 replacement eligibility。
- 同 owner／同 evidence 重跑必須 idempotent；不同 evidence 或第二個 replacement 必須拒絕。
- replacement 仍須重新走 `prepare-create → create → activate`，不得 direct bind。

### why_not_less

只允許人工改名、直接改 SQLite、重送 create 或略過 title gate，會破壞 create-time title authority、唯一 role slot與 audit continuity，不能解決 durable recovery。

### why_not_more

不需要重寫 visible-thread dispatch、建立新 registry／FSM、改變 title preservation gate，或放寬所有 `CREATING` reservation。只補一條有外部封存授權與 exact evidence 的 bounded recovery 分支。

### do_not_absorb

- 不處理一般 title 美化或自動 rename。
- 不允許 active／visible／未封存 thread recovery。
- 不允許 implementation role 或任意 reservation cleanup。
- 不改 project/source mismatch、source advance 或 binding-receipt-lost 既有語意。
- 不把平台異常合理化為可忽略的 title drift。

## RED-capable 驗收

至少新增 deterministic tests 證明：

1. `CREATING` Reviewer + canonical/runtime title mismatch + archived/invisible + absent/unregistered clean worktree，可 recovery 成 `ABORTED_PRECREATE`。
2. receipt 保存 canonical title、observed runtime title、create request digest、formal thread、外部封存 authority 與 evidence digest。
3. 原 role slot 只釋放一次，且只允許 exact 下一代 `RETRY-N`。
4. 同 evidence 重跑回同一 receipt，不重複 terminalization。
5. thread 仍 visible、未封存、worktree 存在、dirty／unique work、project/source/identity/thread/title evidence 漂移時全部零寫入拒絕。
6. `FORMAL_THREAD_TITLE_MISSING_ARCHIVED`、source advance、binding-receipt-lost 與既有 activation title tests 不回歸。
7. 受影響測試、完整相關測試與 `git diff --check` 通過。

## Pantheon 續接條件

本卡被 ai-core 接受並部署後，Pantheon 主線只需：

1. 對既有 RETRY-1 reservation 執行 bounded created-unbound recovery。
2. 建立唯一 Reviewer `RETRY-2`。
3. 驗收既有 readiness candidate `2b9343bc5011f82e5a9d2a81cf1d03a61d80c97d`。

不得藉此重跑 readiness implementation、建立第二條 Reviewer chain，或執行 promotion／production mutation。
