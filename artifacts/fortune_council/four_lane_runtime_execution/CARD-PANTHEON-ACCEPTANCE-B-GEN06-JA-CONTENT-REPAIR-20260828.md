# Gen06 日文內容修正卡

## 目標

在隔離副本修正 Gen06 候選稿的兩項正式 reviewer finding，交付可供同一 reviewer 回審的內容與證據。

## 權威輸入

- production run：`auto-i18n-ja-1414b75a404721e95e74`（Gen06 已 terminal complete）
- source authority：`831c536043d85a6cafe813c08a4f06921f0dd0e2`
- finding：`NON_NATIVE_LANGUAGE_RESIDUE`、`BOUNDARY_MEANING_MISSING`

## 允許輸出

- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_ja_content_repair_20260828/candidate-repaired.json`
- 同目錄的 before/repaired SHA、field diff、validator receipt 與 `RESULT.md`

## 不可變契約

- 保持 run/article/source identity、事實與 source refs、section topology、其餘內容和結構不變。
- 僅修正 meta description、body、FAQ 中的非日文殘留，及對應的日文 boundary meaning。
- boundary meaning 必須是一般性解釋／參考，非個別化、醫療、法律或財務建議；以既有 protected contract 為準。

## 禁止範圍

- 不寫 production root 或原 production candidate。
- 不呼叫 provider、reviewer、coordinator；不建立 Gen07。
- 不改 pipeline code/config；不 publish、tag、push、PR #22、commit。

## 驗證與交付

- 保存 before/repaired SHA、JSON patch／欄位 diff、validator receipts、boundary 逐處檢查、`git diff --check`。
- 最終狀態只能是 `READY_FOR_FORMAL_REVIEW` 或 `BLOCKED`；不得宣稱已核准或可發布。
