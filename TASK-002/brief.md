# TASK-002 Brief

## Root Question

如何把 MBTI 做成個人問卷形式，並讓結果回流到 Pantheon 的統一 report channel，供 AI 解讀、組合牌與後續追問引用？

## Assumptions

- 「頻道」先解讀為 Pantheon 內部 report / signal channel，而不是 Discord、LINE 或社群發送頻道。
- MBTI 是個人自評問卷，不以醫療、職涯測評或正式心理診斷呈現。
- 結果以四個 dimension 為主，16 型只作 shorthand label。
- 外部 MBTI 專案只作流程與資料結構參考，不直接複製題庫。
- 第一版不接 Machine-Mindset 訓練資料；先把個人資料入口與 report 回流打通。

## Goal

交付一條可驗證的 MVP 路徑：

```text
使用者填 MBTI 問卷
-> API 接收 answers
-> MbtiCalculator 產出 dimension scores
-> UnifiedReport 轉成 mbti signals / combo cards
-> 前端在個人報告與 raw signals 中顯示
-> AI prompt 可引用 MBTI evidence
```

## Non-Goals

- 不直接使用外部 repo 題庫原文。
- 不做正式心理測驗宣稱。
- 不先做多人頻道、社群分享或 webhook 推送。
- 不把 MBTI 結果當成覆蓋八字、紫微、人類圖的主結論。

## Acceptance

- 使用者可在前端完成一份 MBTI 個人問卷。
- API payload 可帶 `personality_answers`，不影響既有生日排盤。
- MBTI calculator 產出 `EI/SN/TF/JP` 四維 score、confidence、type shorthand。
- `build_unified_report` 會把 MBTI 結果轉成可追溯 `Signal`。
- AI prompt 明確要求 MBTI 只能作自評偏好，不作絕對人格定論。
- 測試覆蓋 scoring、low-margin 降級、API 兼容與 report signal 回流。

## Open Question

若「回到頻道」是指外部 channel，例如 Discord、LINE、Slack 或產品內多人房間，需要另開 delivery slice。
