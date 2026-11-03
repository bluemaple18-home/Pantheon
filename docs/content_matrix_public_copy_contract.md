# Pantheon Content Matrix Public Copy Contract

狀態：`PROVISIONAL EDITORIAL WORDING / NOT MEASURED SEO TRUTH`

## 問題

Content Matrix 的 `scenario` 是內部分類。它不能被機械拼進公開標題與正文。
`V2-TAROT-DEATH-MONEY` 曾把 `scenario=金錢` 直接組成「塔羅死神在金錢中代表什麼」，並讓 Writer 依該字串展開整篇文章；這是 matrix-to-copy contract 缺口，不是單篇文案偶發失誤。

## v1 裁決

- Matrix 的原子組合、ID、family、entity、scenario 與總篇數不變。
- `scenario` 繼續作內部 coverage 分類。
- `primaryKeyword`、`title` 與 `intent` 必須由 `family × scenario` 的公開文案 renderer 產生，不能直接使用 `entity + 在 + scenario + 中` 通用模板。
- 本輪只修已證實不自然的 `MONEY` renderer；不建立禁詞黑名單，也不宣稱已找到各語系最佳 SEO keyword。
- 目前用詞是前期人工審過的自然表達。10K 發布後，仍由各語系 GSC query data 決定 retitle、rewrite、merge 或其他 SEO action。
- `intent` 必須把矩陣分類轉成該 domain 的實際讀者問題；Writer 應依該問題展開全文，而不是反覆重複內部分類詞。

## 回歸案例

```text
internal:
  family = tarot
  entity = 死神
  scenario = 金錢

public:
  primaryKeyword = 塔羅死神財運
  title = 塔羅死神財運怎麼看？從牌義、取捨與風險選擇理解限制
  intent = 問財運時抽到死神，想理解這張牌對取捨、收入變動與風險選擇提供什麼提醒，以及不能據此斷定什麼
```

不得再產生：

```text
塔羅死神在金錢中代表什麼
```

這個例子是結構回歸，不是建立「金錢」黑名單；真正 contract 是內部 scenario 不得直接成為所有 family 的公開句法。
