# Flash Lite production retry concurrency closure（2026-09-11）

## 最終主線收尾

**狀態：CLOSED。正式產品修補已在 `main`，retry8 promotion 已 `COMMITTED`，七服務已恢復正常載入。**

- 正式產品 actor baseline：`579ddfe0c5b4fd5d8fbf5df96d887ef73b5ba867`（PR #32 merge；PR #28–#32 均已進 `main`）。
- Retry8 generation：`g115-579ddfe0c5-flash-lite-publisher-canary-retry8-20260911`。
- Correlation：`flash-lite-convergence-activation-retry8-20260911`。
- Plan digest：`ebc7234d0210a5a44673cc78e5e71fc6c3abc17c7ee005f1c31f573e2b627d3e`。
- Promotion status：`COMMITTED`；finalize receipt 為 `COMMITTED`。
- Rule25 readiness：`READY`（execution line `exec-ra-slice-004`）。
- Runtime topology：七個 launchd service 目前 7/7 `LOADED`。
- 收尾時 remote `main`：`5ca2f84ddadcaf87514deca7673407c081dc612a`。

## 已驗收 publish

1. `legacy-auto-sweep-v1-astrology-0045-asc-aries` → `PUBLISHED_REWRITE`，commit `6a05dd942d7d7abd9617fab4d744f8e328d340f5`，version `0.3.410`；發布時已驗證公開網址 HTTP 200、正文可見、canonical 正確。
2. 後續既有 publish-ready `ASC-GEMINI` → commit `662a33bba3f8d9c89a5e019d9b667edb9f88430b`，version `0.3.411`；發布時已驗證 HTTP 200、正文可見。
3. `main` 後續另有內容發布至 `0.3.412`（`5ca2f84d...`）。`579ddfe0c5..5ca2f84d` 的三個後續 commit 只有內容／CHANGELOG／generated web output，沒有再修改本次 Flash Lite deployment/control code。

## 正式修補已進主線

- PR #28：Flash Lite convergence / all-stopped recovery。
- PR #29：publisher-canary all-stopped restage。
- PR #30：capacity admission sensor。
- PR #31：publisher gate route expectations。
- PR #32：activation-only replacement stage seam。

上述正式產品修補均已在 `main`。本次收尾不再把 retry8 現場 controller 複製進產品碼。

## Retry8 operation controller 的收尾裁決

`.work/writer-lite-switch-20260910/` 下的 retry8 controller、transaction script 與一次性 recovery evidence 屬 production orchestration，不是新的產品 runtime。它們刻意不整包提交到主線，避免形成第二套 deployment controller。

最後一次現場修補處理的 invariant 是：

- promotion `COMMITTED` 後 rollback／recover 必須持續 fail-closed；
- 同一 exact target 若需恢復 normal steady，只能在 target SHA、generation、manifest、barrier、transaction authority 全部匹配時執行 stage／steady activation；
- 允許 steady 恢復不得重新取得 rollback authority，也不得讓其他 canary／recovery mutation route 因 `COMMITTED` 被廣泛放行。

正式 `scripts/pantheon_content_runtime_promotion.py` 已有 `COMMITTED` rollback fail-closed。`COMMITTED → activate-steady` 的特殊放行只留在 retry8 transaction-specific operation controller；目前沒有 measured need 支持新增另一套正式 deployment runtime，因此不產品化。

## 最終驗證證據

- retry8 `status`：`PASS / COMMITTED`。
- `promotion-finalize.json`：`COMMITTED`。
- Rule25：`READY`。
- 七個 production launchd label：7/7 `LOADED`。
- remote compare `579ddfe0c5..5ca2f84d`：只有發文內容相關檔案，無 deployment/control source drift。
- Root working tree 原有其他 `.ai` / handoff 未追蹤工作保持不動；本次收尾沒有覆寫其他開發。

## 歷史故障摘要

本輪曾依序遇到 activation mode mismatch、all-ABSENT preactivation topology、publisher-only canary 後 mixed-mode restage，以及 finalize 時 active mutation / Rule25 receipt 辨識問題。這些故障都先 fail-closed，未在未通過 gate 時呼叫 Gemini 或發布文章；對應的正式 reusable 修補已由 PR #28–#32 收斂進主線。

最終完成條件以 Writer → Reviewer → publish → GitHub push → 公開網址 HTTP 200 且正文可見為準；本輪 exact canary 已達成。