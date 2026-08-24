---
id: CARD-PANTHEON-G8-V0386-STAGE-READINESS-CAPACITY-REPAIR-PLAN-20260824-RESULT
status: completed
verdict: BLOCKED
production_mutation: false
remote_access: false
canary_created: false
---

# V0386 結果

## Evidence-first 裁決

`BLOCKED`。

V0385 的 target readiness blocker 是過早 gate：promotion `apply` 在 `STAGE_INSTALLED` 階段才由正式 `_install_private_stage` 建立 `readiness/<target_generation>/*.json` 與 activation barrier；postcheck 之後才讀取驗證。因此不得把缺少 target generation readiness 當成 apply 前 drift，也不得手造 production artifact。正確修正是調整 preflight/replan 契約，讓 readiness 成為 apply output、postcheck input。

Rule24 的正式 two-cycle harness 與 exact-byte bundle 已找到，包含 bounded policy、host reserve、project bytes/files、RSS/swap、reclaim、retention projection 與 fail-closed stop-loss。但 fresh producer 入口是 Python API；現有 DSSE CLI 只能對既有 fresh measurements 做 `produce`，無法由單一正式 argv 產生完整 fresh bundle。本卡沒有執行 fresh harness、沒有建立 production receipt，也沒有進行 production apply。

## 交付物

- [source-contract-receipt.md](g8_v0386_stage_readiness_capacity_repair_plan_20260824/source-contract-receipt.md)：source lines、順序、V0385 finding review。
- [rule24-plan.json](g8_v0386_stage_readiness_capacity_repair_plan_20260824/rule24-plan.json)：inputs/outputs、capacity bounds、sampling、stop-loss、allowlist/forbidden。
- [exact-next-step-argv.json](g8_v0386_stage_readiness_capacity_repair_plan_20260824/exact-next-step-argv.json)：分離 Rule24 與後續 apply 的非執行 argv；placeholder 存在即不構成授權。
- [authorization-payload.json](g8_v0386_stage_readiness_capacity_repair_plan_20260824/authorization-payload.json)：未授權 payload、V0383 僅分析基線、allowlist 與 terminal stops。
- [finding-review-receipt.json](g8_v0386_stage_readiness_capacity_repair_plan_20260824/finding-review-receipt.json)：V0385 過早 gate 分類。
- [protected-tripwire.json](g8_v0386_stage_readiness_capacity_repair_plan_20260824/protected-tripwire.json)：本次 local actions 的 protected changed set。
- [verification-receipt.md](g8_v0386_stage_readiness_capacity_repair_plan_20260824/verification-receipt.md)：JSON/py_compile/diff 結果與 pytest 環境限制。

## 建議的安全下一步

1. 由具正式入口的 operator 在 task-owned `/private/tmp` 建立 fresh two-cycle Rule24 bundle，保留兩個 cycle、capacity receipt、reclaim 與 stop-loss evidence。
2. 以正式 DSSE producer/verify 綁定 fresh bytes、policy、correlation、challenge；任何 drift 或缺欄即 `BLOCKED`。
3. 重新 plan，移除「target generation readiness 必須在 apply 前存在」的錯誤 preflight；保留 current stage digest/no-drift 檢查。
4. 重新產生 exact argv、plan digest、authorization digest、machine bindings 與 rollback packet；經人工核准後才另行考慮 apply。

## 驗證與限制

- JSON parse：待執行唯讀驗證。
- 受影響 tests：待執行唯讀測試。
- `git diff --check`：待執行。
- 本卡未改 source、workflow、tests 或既有 artifact；只新增本卡 ownership。
- 最終 verdict 只能是 `BLOCKED`，因 fresh Rule24 artifact/producer identity/新 plan digest/authorization 尚未存在。
