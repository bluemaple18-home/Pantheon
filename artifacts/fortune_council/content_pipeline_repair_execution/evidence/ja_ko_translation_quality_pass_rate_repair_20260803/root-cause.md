---
id: CARD-PANTHEON-JA-KO-TRANSLATION-QUALITY-PASS-RATE-REPAIR-20260803
status: ROOT_CAUSE_CONFIRMED
type: evidence
---

# Root cause

## 已觀測事實

- `SLICE-JKQ-OBS-001` 以 `updated_at` 由新到舊固定抽取 `ja=20`、`ko=20`、`en=10` 個 terminal run；50 筆皆有唯一 primary stage，unknown／generic 為 0。
- 32 個 `LocalePlanValidationError` 保存 response 均以目前 runtime 做離線 replay；31 個是 safety flag 不一致、來源語言殘留或 rebuild topology 重用。
- 唯一 false-negative 是日文 `coverage_note`：來源含 `Rider–Waite–Smith`，response 正規化為 `Rider-Waite-Smith版の構図について`。日文內容成立，但 source authority 擷取只接受全大寫 acronym，且未正規化 dash。
- fact mapping 反序正例通過；缺漏、重複、錯誤 safety flag 與非法 H2 slot 負例維持拒絕。因此不能移除 canonicalization、唯一性、安全或 H2 gate。
- Reviewer 樣本中 `SOURCE_SYNTAX_TRANSFER=7`、`NON_NATIVE_SEARCH_INTENT=3`；8 個 run 命中至少一個主因 code。訊息集中在來源段落／問答順序鏡像，以及 title、tag、FAQ、H2 未依日韓搜尋問題重組。

## 可證偽假說

1. 若 false-negative 來自 source proper-name dash 正規化缺口，僅把來源中以 dash 連接的 ASCII proper name 正規化成 `-` authority，保存 response 會轉綠，任意英文句、錯誤 safety、fact 缺漏／重複與非法 H2 仍拒絕。
2. 若問題是 coverage note 不該受語言 gate，移除該 gate 會讓樣本中的繁中與英文 coverage note 一併通過；replay 已證明這會降標，因此此假說否決。
3. 若問題是 fact order，反序 control 應失敗；實際 replay 已通過 canonicalization，因此此假說否決。
4. 若日韓 Reviewer 主因來自 writer 未把 locale plan 的 query 轉成文章資訊架構，加入僅對 `ja/ko` 生效的 plan/article repair contract 後，固定 Reviewer-code fixture 應保留 hard reject，且 repair prompt 明確要求 title／answer／H2／FAQ 依當地問題順序重組；英文 prompt digest 必須不變。

## Source decision

- CodeGraph 入口：`_run_locale_generation` → `_hydrate_locale_plan` → `_article_prompt` → `_review_generated_candidate`。
- 原始碼 seam：`_source_ascii_authorities`／`_plan_matches_target_language` 是保存 response 的最小 public-observable validation seam；`_plan_prompt`／`_article_prompt` 是日韓 native repair seam。
- Publisher 只消費 clean review；本卡不修改 Publisher eligibility、ledger 或 release 流程。

## Slice decision

- `SLICE-JKQ-PLAN-002`: applicable；已有 1 個可重現 false-negative。
- `SLICE-JKQ-NATIVE-003`: applicable；兩個主因 code 的 sample denominator 已鎖定。
- 修改策略：先完成 PLAN-002 的單一 RED→GREEN，再建立 NATIVE-003 的固定日韓 fixture；不得同時放寬 validator 與 prompt。
