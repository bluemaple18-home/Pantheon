---
id: CARD-PANTHEON-G8-V0391-PUBLISH-ACTIVATION-CANARY-20260825
status: ready
chain_id: PANTHEON-G8-PUBLISH-ACTIVATION-CANARY-20260825
role: implementation
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 規格與正式入口已固定，但涉及 production activation、單篇 publication transaction 與公開驗收，使用 strict/core-bounded 跑道；不需 Sol 處理架構岔。
execution_mode: bounded_production_canary
production_mutation: activation_and_single_article_publish_authorized
remote_mutation: forbidden_without_explicit_push_authorization
---

# Pantheon 單篇發文 activation canary

工作名稱：Pantheon 單篇發文 activation canary

任務目的：沿用已 promotion 的正式 runtime，完成 activation → 單篇 create/run → Publisher exact-run → 公開網址驗收。

可改範圍：本卡專屬 result/evidence、既有正式 runtime 所擁有的單篇 queue/state/publication transaction；禁止修改 source、workflow、共享規則或既有未追蹤檔。

驗證：同一 correlation 下只有一篇、`max-runs=1`、Publisher child 不超過一次、公開 URL 200 且正文 identity 可見；中間 PASS 不算完成。
停損：禁止新卡、重做 promotion、替代腳本、tag、未授權 push；同一 blocker 第三次、identity 漂移、第二 child 或需要 push 時立即停止並保留證據。

## 來源與固定事實

- 接手：`handoff_20260825_pantheon_publish_flow_activation_canary.md`。
- Source commit：建立 thread 時以包含本卡的 main commit 為準。
- Promotion target：`5872284828f9dd6f0a75adf407becaeadb50d61a`。
- Generation：`g36-5872284828-zero-write-20260824`。
- Promotion 已 `COMMITTED`；禁止重做 promotion、capacity exercise 或 readiness 建置。
- 既有未追蹤檔屬主工作區，禁止讀寫、加入或清理。

## 執行契約

1. 第一拍唯讀確認 actor、manifest、private stage、readiness、activation barrier、七服務與正式 action；先查 CodeGraph，無結果才限域 `rg`。
2. 只用既有正式入口 activation；不得建立替代 token、腳本、plist 或第二套流程。
3. 從既有正式內容來源選一篇未發布 `new` 項目，鎖 article identity、run ID、correlation ID 與預期 route；公開內容不得含 canary／測試等內部字樣。
4. 只用既有 coordinator/runner 建立並跑完該 exact run；Writer、Reviewer、deterministic gate 全數通過才可交 Publisher。
5. Publisher 必須使用既有正式 preflight/stage/`--activate-publisher-only`，固定 exact run、`max-runs=1`、one-shot child；terminal 後走既有 reset seam。
6. 若公開部署需要 Git push 或其他本卡未明示 remote write，停止並回報 exact action、target 與原因；不得自行推定授權。
7. 取得正式文章 URL 後，以 HTTP 與 browser 驗證 200、canonical、標題與正文 identity；只有公開文章可讀才回 GO。

## 唯一可寫範圍

- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0391-PUBLISH-ACTIVATION-CANARY-20260825-RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/g8_v0391_publish_activation_canary_20260825/`
- 正式 runtime 既有入口明示擁有的單篇 queue/state/publication transaction。
- task-owned `/private/tmp/pantheon-v0391-*`。

## 禁止範圍

- 禁止修改 repo source、tests、workflow、registry 手工檔、既有 evidence 與未追蹤檔。
- 禁止 promotion、capacity 重跑、手造 readiness/barrier、直接 launchctl 操作、第二篇、第二 child、retry chain。
- 禁止 push、tag、archive thread、清理主工作區或建立後續卡。

## 交付

- `GO`：公開 URL、HTTP/browser 證據、run/transaction/child accounting、reset 終態與未追蹤檔未碰證據。
- `BLOCKED`：單一根因、已嘗試次數、最後安全狀態、是否有 partial mutation、下一個需要的明確授權。
- 只交付 candidate/result 與完整 commit SHA；不得宣稱主線已接受或整合。
