# TASK-002 Status

## Current State

64 分支人格問卷已實作為 48 題六軸 MVP。

Latest update:

- 題目已做第二輪降 AI 感與隱性化。
- 題目避免直接暴露「內向外向、抽象具體、情感邏輯、計畫彈性」等軸向。
- 題面改用生活片段：旅行、群組、聚會、訊息、出包、文件、臨場變動。
- 顯示順序已用固定 `QUESTION_ORDER` 打散，避免連續同軸題目讓使用者猜出測量項目。
- App 已拆成獨立頁：`/` 是命書，`/personality` 是 64 人格。
- 命書頁不再包含人格測驗 DOM 或人格 JS；人格頁使用獨立 `personality.html` / `personality.js`。
- 新增 `/api/v1/personality` personality-only API，64 人格不依賴生日命盤。
- 問卷互動改為每段 8 題，共 6 段；保留進度條、已答題數、返回/繼續。
- 已補 `.mbti-question[hidden] { display: none; }`，避免 CSS 把 hidden 題目重新顯示出來。
- 後端計分軸未變，仍保留 answer metadata 供追溯。

## Mainline

MBTI 個人問卷要先形成 Pantheon 自有 schema，再回流 `UnifiedReport` 的 signal / combo card channel。第一版重點是「資料回流與可追溯」，不是追求題庫完整度。

題數決策：

- 32 題：核心 MBTI，四個維度各 8 題，只能產生 16 型 core。
- 48 題：目前 64 分支人格 MVP，六個維度各 8 題，可產生 `core_type + A/O + H/C`。
- 72 題：若要更接近 MBTI Step II 的 facet 思路，可在 48 題上再加 facet probes。

目前不宣稱是官方最新版 MBTI；定位是 Pantheon 自有 MBTI-like / 64personality-like 自評問卷，採連續分數、confidence 與 low-margin 降級。

## Task Slices

### S1：MBTI Schema Contract

目的：定義 API 可接收的問卷答案與 calculator 可輸出的結果契約。

Likely files:

- `app/api/schemas.py`
- `app/calculators/mbti.py`
- `tests/test_api.py`
- `tests/test_calculators.py`

Acceptance:

- `BirthInput` 可選帶 `personality_answers`。
- 每個 answer 至少包含 `question_id`、`dimension`、`direction`、`value`。
- 不帶 MBTI 答案時，現有 `/predict` 行為不變。

Verification:

- `uv run pytest tests/test_api.py tests/test_calculators.py`

Status: completed.

### S2：Scoring MVP

目的：讓 `MbtiCalculator` 從答案算出四維分數、confidence 與 16 型 shorthand。

Likely files:

- `app/calculators/mbti.py`
- `tests/test_calculators.py`

Acceptance:

- 固定 answers 產出穩定 type。
- 接近中線的維度標 `low_margin`。
- 答案不足時輸出 `insufficient_data`，不假裝完成測驗。

Verification:

- `uv run pytest tests/test_calculators.py`

Status: completed.

### S3：Report Channel 回流

目的：把 MBTI 結果轉成 `UnifiedReport.signals`，讓 AI 與前端可以引用。

Likely files:

- `app/ai/report.py`
- `app/ai/prompts.py`
- `tests/test_api.py`

Acceptance:

- MBTI 四維各自轉成 signal。
- signal `basis` 明確標成「MBTI 自評問卷」。
- low-margin signal 的文字降級。
- prompt 禁止把 MBTI 當心理診斷。

Verification:

- `uv run pytest tests/test_api.py`

Status: completed.

### Checkpoint A

跑完整測試：

```bash
uv run pytest
git diff --check
```

### S4：前端問卷入口

目的：在個人報告輸入區加入 MBTI 問卷 UI，並把 answers 送進 `/predict`。

Likely files:

- `app/web/index.html`
- `app/web/static/app.js`
- `app/web/static/api.js`
- `app/web/static/styles.css`
- `tests/test_web.py`

Acceptance:

- 問卷可填、可送出、可重跑報告。
- 不填問卷也可以照常產生生日報告。
- UI 不把 MBTI 呈現成正式診斷。

Verification:

- `uv run pytest tests/test_web.py`
- 若啟動前端，做 browser smoke。

Status: completed for static UI and payload wiring; browser smoke pending because no in-app Browser tool was available in this turn.

### S5：Dashboard / Signals 顯示

目的：讓 MBTI signals 出現在 dashboard 與 raw signals，不破壞既有五行/紫微視圖。

Likely files:

- `app/web/static/dashboard.js`
- `app/web/static/paper.js`
- `app/web/static/styles.css`

Acceptance:

- MBTI 四維能在 raw signals 顯示。
- 若加入人格摘要，只顯示自評偏好與 confidence。
- 既有元素圖、雷達圖、組合牌仍可正常渲染。

Verification:

- `uv run pytest`
- browser smoke 截圖或文字證據。

Status: completed for MBTI identity strip and raw signal rendering path; browser smoke pending because no in-app Browser tool was available in this turn.

### Checkpoint B

驗收完整個人 MBTI flow：

```bash
uv run pytest
git diff --check
```

若有 browser 驗收，證據放 `TASK-002/evidence/`。

## Waiting Condition

如果要把結果送到外部「頻道」，需要先確認目標是 Discord、LINE、Slack、Telegram，或 Pantheon 內部多人 channel。

## Next Branch Slice

### S6：Branch Personality Layer

目的：在 16 型之外加入 Pantheon 分支人格，避免只輸出四字母。

Status: completed as six-axis MVP.

Implemented design:

- 六軸：`EI/SN/TF/JP/AO/HC`。
- 題數：48 題，每軸 8 題。
- 輸出：`core_type`、`branch_code`、`type`，例如 `INTJ-AH`。
- A/O 與 H/C 只作自評分支，不宣稱官方 MBTI。
- 分支結果進 `signals` 與 `combo_cards`，不覆蓋八字或紫微原始訊號。

Acceptance:

- 分支人格必須能追溯到 branch answers。
- low-confidence branch 不顯示分支名，只顯示「傾向待確認」。
- AI prompt 禁止把分支名寫成固定命運或診斷。
