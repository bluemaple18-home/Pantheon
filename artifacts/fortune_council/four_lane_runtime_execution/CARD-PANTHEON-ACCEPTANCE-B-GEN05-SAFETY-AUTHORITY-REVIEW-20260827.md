# Pantheon Acceptance B：gen05 safety authority Review

status: `DISPATCH_READY`
card_id: `CARD-PANTHEON-ACCEPTANCE-B-GEN05-SAFETY-AUTHORITY-REVIEW-20260827`
chain_id: `PANTHEON-ACCEPTANCE-B-GEN05-SAFETY-COVERAGE`
candidate: `3f54e1c74eec945f192f2e1ad7ff677baf9885cc`
parent: `e3a2bbd188a0d25f15a02cde1b2b6820df5dd583`

## 目的

唯讀審查 gen05 safety authority bounded Repair 是否以最小 seam 關閉 provider safety echo gap，且可 provider=0 恢復 production exact gen05 legacy plan，不造成 fresh-path fail-open。

## 必驗

- Candidate parent／allowlist／diff；禁止擴至 publisher、promotion、replacement、semantic budget 或 gen04 lifecycle。
- Fresh schema/prompt 不再要求 `safety_boundary`；fresh payload 偷帶 safety 必須 strict reject；合法 fresh payload由 local deterministic owner 注入。
- Legacy read 只能在 external plan 已存在、source-ref-map valid、companion writer receipt success、legacy schema digest exact match 時啟用。
- Legacy adapter 只忽略 external safety assertion；missing/duplicate/unknown refs、receipt missing/drift、其他欄位 drift 仍 fail closed。
- Production exact gen05 fixture：provider=0，22 safety 全由 local 注入 false，三個 legacy audit artifacts bytes 不變，不建 gen06、不改 continuation state。
- Targeted tests、完整 `tests/test_agy_multilingual_pipeline.py`、`git diff --check`。

## 禁止範圍

- 唯讀，不改檔、不 commit、不 merge/push、不碰 production、不呼叫 provider、不重跑正式入口。
- 不重審 forged gen07 或已接受的 gen04 Repair；P2/P3 不得阻擋。
- 只有本卡 acceptance 的 P0/P1 可 `NO_GO`；若 NO_GO，列 path:line、觸發條件、風險、最小修法、重現命令。

## 裁決

- `GEN05_SAFETY_AUTHORITY_REVIEW_GO`：無未解 P0/P1，附證據與 residual risks。
- `GEN05_SAFETY_AUTHORITY_REVIEW_NO_GO`：只列 acceptance-scope P0/P1。
