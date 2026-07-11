# Pantheon 命理產品 Git Source Intake

日期：2026-07-11
狀態：已讀本地文件與公開 GitHub 頁面；只抽取可用結構，不複製程式碼、資料集、題庫、牌義或文案。

注意：這份不是 SEO/GEO 專用 repo intake。SEO/GEO 專用來源已移到 `artifacts/fortune_council/seo_geo_repo_intake/source_manifest.md`。

## 結論

這份整理的是 Pantheon 命理產品、資料 schema、驗證器與內容題材來源。它們對內容題材有用，但不是 SEO/GEO 工具 repo。用法是轉成三層：

1. 產品題材層：決定我們要補哪些 MBTI、塔羅、命盤、紫微、八字內容。
2. 內容信任層：每篇文章要有可追溯來源、邊界、不可保證式結論。
3. 工具輸出層：競品 SEO 工具的 playbook 要明確寫出「哪些來源可用、哪些不能抄」。

## 已確認來源

| 來源 | 本地出現位置 | 目前用途 | 對 SEO 工具的價值 | 不採用邊界 |
|---|---|---|---|---|
| `hhszzzz/taibu` | `TASK-001/context_manifest.md` | 多命理產品與 MCP/Skills 參考 | 可參考產品線覆蓋、工具化入口、AI 引用來源設計 | 不複製 Web/服務端程式；混合 license，只有 core/MCP 類包可按 MIT 條件評估 |
| `china-testing/bazi` | `TASK-001/context_manifest.md` | 八字排盤概念參考 | 可補八字文章題材與術語方向 | GitHub 頁面未找到清楚 license；不得複製 code 或內容 |
| `Renhuai123/ziwei-doushu` | `TASK-001/context_manifest.md`, `docs/attribution.md` | 紫微排盤、樣本資料、知識庫參考 | 可補紫微十二宮、主星、四化、命盤入門 cluster | 若使用 dataset，必須 attribution；不直接照搬解讀文當公開 SEO 文章 |
| `zhenheco/life-chart-engine` | `TASK-001/context_manifest.md`, `docs/life_chart_engine_intake.md` | 西洋星盤 / 人類圖 / 紫微欄位契約與驗證器 | 可補 Human Design、星盤、出生時間敏感度、JSON 欄位嚴謹度 | 不把外部 CLI 當產品核心依賴；先作 verifier/schema 參考 |
| `breezyreeds/kangxi-strokecount` | `data/nameology/kangxi-strokecount.csv` | 康熙筆畫資料來源 | 可補姓名學/筆畫內容 cluster 的資料來源線索 | CSV 資料需保留來源與授權檢查；不直接當 Click108 SEO 證據 |

## 待補 URL 或待審來源

| 來源名稱 | 出現位置 | 目前判定 |
|---|---|---|
| `rauf-21/mbti-personality-test-app` | `docs/mbti_tarot_hd_fusion_strategy.md` | MBTI 測驗流程研究樣本；題庫原文與 UI code 不可直接搬 |
| `PKU-YuanGroup/Machine-Mindset` | `docs/mbti_tarot_hd_fusion_strategy.md` | MBTI agent / dataset 概念；模型、資料與 ethical guideline 需另審 |
| `Personality-NLP/MbtiBench` | `docs/mbti_tarot_hd_fusion_strategy.md` | MBTI 評估方法；只可當評估方法參考 |
| `ekelen/tarot-api` | `docs/mbti_tarot_hd_fusion_strategy.md` | 78 張牌 schema/API contract 參考；牌義與圖像來源需分別審 |
| Human Design 類專案 | `docs/mbti_tarot_hd_fusion_strategy.md` | 目前只當待審 inventory；未確認 URL/license/golden sample 前不進 implementation |

## 給競品 SEO 工具的接法

- `competitor_seo_tool.py` 的核心仍只抓公開競品網站，不抓 GitHub repo 內容當排名證據。
- GitHub source intake 只進 `playbook.md`，用來約束內容生產：題材可參考、架構可參考、正文與資料不可抄。
- Keyword matrix 的產品題材來源可以從這些 repo 延伸，例如 `紫微斗數是什麼`、`命宮是什麼`、`八字是什麼`、`塔羅牌意思`、`MBTI 是什麼`、`人類圖是什麼`。
- 寫 Click108 對打文章時，優先打「解釋型 + 情境型 + FAQ」：比 Click108 多 schema、來源邊界、內鏈，不用更強的宿命承諾。
- 有 license 不清楚的 repo，只能用作題材提示，不可進資料、程式或公開文章正文。
- 對另一個對話框派工時，先讀這份 manifest，再讀 `docs/competitor_seo_tool.md` 和 `docs/pantheon_article_publication_standard.md`。

## 工具驗收標準

下一次跑 Click108 或其他競品時，`output/competitor_seo/<hostname>/playbook.md` 必須包含「已整合的 Git / 研究來源邊界」段落。若沒有，代表工具沒有讀到這份 source intake。
