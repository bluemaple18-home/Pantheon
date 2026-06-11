# MBTI / Tarot / Human Design 融合策略 v0.1

## 結論

Pantheon 不應把 MBTI、塔羅、人類圖外部專案直接搬進來，而是把它們拆成三種可融合能力：

- MBTI：補「人格語言」與 AI 顧問口吻，不作硬分類定論。
- 塔羅：補「當下議題」與象徵敘事，不和出生資料假裝有因果。
- 人類圖：補「BodyGraph 結構欄位」與出生時間敏感度，不在缺星曆驗證時輸出強結論。

採用原則：

```text
外部專案只當研究樣本、資料契約與驗證靶
Pantheon 自己定義中介 schema、confidence 與 report 語法
AI 只使用可追溯 evidence 產生建議
```

## 產品定位

第一階段目標不是做「三套準確度競賽」，而是做一個可追溯的整合型顧問：

- 出生盤系統回答「長期底色」。
- MBTI 回答「自我敘述與互動偏好」。
- 塔羅回答「當前提問與情境反思」。
- 人類圖回答「出生時間推導的能量結構」，但必須標註計算信心。

每個結論都要能回到 `report.signals` 或 `report.combo_cards`。沒有 evidence 的 AI 文案只能寫成反思問題，不能寫成命盤結論。

## 外部來源分層

| 類別 | 外部來源 | 可吸收內容 | 不直接吸收內容 | 初步風險 |
|---|---|---|---|---|
| MBTI 測驗流程 | `rauf-21/mbti-personality-test-app` | 70 題流程、題目分組、結果頁節奏 | 題庫原文、UI code、yarn/Next 實作 | 題目來源與 license 需再查 |
| MBTI Agent 人格 | `PKU-YuanGroup/Machine-Mindset` | 16 型人格對話一致性、訓練/偏好資料概念 | 模型權重、資料集直接商用、人格強操控 | Apache-2.0 code，但模型/資料需分開審 |
| MBTI 評估 | `Personality-NLP/MbtiBench` | soft label、心理師標註、偏差評估方法 | 小樣本直接當產品分類器 | 倫理 guideline 與資料來源需保留 |
| Tarot 資料/API | `ekelen/tarot-api` | 78 張牌 schema、upright/reversed、API contract | API 依賴作核心服務、直接搬資料不標來源 | Waite 文本與牌圖來源需分別標註 |
| Tarot AI 解讀 | Arcana AI / Emily Tarot / Ollama 類專案 | 多牌陣、解讀 prompt、local model 選項 | 直接套商業化流程與文案 | repo 需逐一定位與 license audit |
| Human Design 引擎 | HDKit / HumanDesign-API / SharpAstrology / human-design-py | BodyGraph 欄位、閘門/通道 schema、golden sample | 未驗證星曆與圖表演算法 | 多數專案需重新確認維護狀態與 license |

## Pantheon 中介 Schema

不要讓各外部專案的欄位直接進 report。先統一成三種中介 payload。

### MBTI payload

```json
{
  "system": "mbti",
  "status": "scored",
  "provider": "pantheon_mbti_questionnaire",
  "type": "INTP",
  "dimensions": {
    "EI": {"score": -0.64, "confidence": "primary"},
    "SN": {"score": 0.28, "confidence": "low_margin"},
    "TF": {"score": -0.42, "confidence": "primary"},
    "JP": {"score": 0.11, "confidence": "low_margin"}
  },
  "evidence": [
    {"question_id": "mbti.q01", "dimension": "EI", "answer": 4}
  ]
}
```

規則：

- `type` 只能當 shorthand，report 強結論應使用四個 dimension。
- 接近中線的維度標 `low_margin`，AI 文案必須降級。
- 若使用者只輸入自認 MBTI，不可當測驗結果。

### Tarot payload

```json
{
  "system": "tarot",
  "status": "drawn",
  "provider": "pantheon_tarot_deck",
  "question": "我現在該怎麼面對職涯選擇？",
  "spread": "three_card",
  "cards": [
    {"position": "past", "name": "The Fool", "reversed": false, "seed_basis": "server_random"}
  ],
  "evidence_policy": "symbolic_reflection"
}
```

規則：

- 塔羅只回答使用者當下問題，不回推人格或命運。
- 隨機抽牌必須記錄 seed policy，但不把 seed 暴露成可操控結果。
- AI prompt 要保留多義性，避免把牌義收斂成單一命令。

### Human Design payload

```json
{
  "system": "human_design",
  "status": "calculated",
  "provider": "pantheon_hd_engine",
  "birth_time_confidence": "exact",
  "type": {"value": "Projector", "confidence": "external_only"},
  "authority": {"value": "Emotional", "confidence": "external_only"},
  "defined_centers": [{"name": "Solar Plexus", "confidence": "external_only"}],
  "gates": [{"id": 37, "line": 3, "planet": "sun", "confidence": "external_only"}],
  "validation": {"golden_sample_match": false}
}
```

規則：

- 人類圖對出生時間敏感；`birth_time_confidence != exact` 時不能輸出強結論。
- 星曆、時區、夏令時間與座標處理要獨立測 golden sample。
- `external_only` 欄位可展示，但 report 只能寫成「外部參考訊號」。

## Fusion 規則

| Fusion Card | Evidence | 可說 | 不可說 |
|---|---|---|---|
| `combo.self_expression` | MBTI EI/TF + 八字火/水 + 紫微命宮星曜 | 使用者表達與互動偏好 | 你天生一定是某種人 |
| `combo.decision_style` | MBTI JP/TF + 八字十神 + 人類圖 authority | 做決策時可能重視的線索 | 重大決策應照人類圖執行 |
| `combo.current_question` | Tarot spread + report existing signals | 當前問題的反思角度 | 抽牌證明事情會發生 |
| `combo.energy_structure` | Human Design centers/gates + birth confidence | 結構性參考與待驗證欄位 | 未驗證就宣稱完整 BodyGraph 正確 |

融合輸出必須包含：

- `evidence_ids`
- `source_systems`
- `confidence`
- `because`
- `therefore`
- `advice`

## 實作切片

### P0：研究與安全邊界

- 建立 external source inventory，逐一記錄 repo URL、license、資料 license、可用欄位、不可用內容。
- 補 `docs/attribution.md` 條目，只標「參考」與「未直接複製」。
- 為 MBTI / Tarot / Human Design 定義 Pydantic schema，不接外部資料。

### P1：MBTI MVP

- 在 `app/calculators/mbti.py` 實作內建題庫 adapter，但題庫先用 Pantheon 自建題目或可授權題庫。
- API 增加可選 `personality_answers`，回傳四維分數與 low-margin 標記。
- report 只用 dimension signal，不用 16 型標籤下強結論。

題數分層：

- `32 題 core`：四個維度各 8 題，適合第一版個人自評與 report 回流。
- `48 題六軸版`：32 題 core + A/O 8 題 + H/C 8 題，可產生 64 分支人格。
- `72 題 facet 版`：在 48 題六軸版上再加 facets，較接近 MBTI Step II 的細分精神，但不宣稱官方授權或等同官方量表。

分支人格規則：

- 分支名只作產品語言，不覆蓋 `EI/SN/TF/JP` 四維分數。
- branch confidence 低時不顯示分支名。
- A/O 與 H/C 只作 64personality-like 產品分支，不宣稱官方 MBTI。

### P2：Tarot MVP

- 把目前單牌 MVP 擴成牌庫 schema、牌陣 schema、抽牌 seed policy。
- 先支援 `single_card`、`three_card`、`celtic_cross` 的資料結構。
- AI 解讀提示詞加上 `symbolic_reflection` guardrail。

### P3：Human Design Adapter

- 先做 provider interface 與 golden sample harness。
- 比較 HDKit / HumanDesign-API / SharpAstrology / human-design-py 的欄位與輸出，不直接 import。
- 只有 golden sample 穩定後，才把 `human_design` 從 `reserved` 升到 `external_only` 或 `primary`。

### P4：Unified Report 升級

- `app/ai/report.py` 增加 MBTI / Tarot / Human Design signal builder。
- 每個新 signal 都要帶 `basis`、`plain_meaning`、`confidence` 或等效欄位。
- prompt 增加「跨系統衝突降級」規則。

## 驗證策略

- MBTI：固定答案 fixture 應產生穩定四維分數；low-margin case 不得輸出強 type。
- Tarot：相同 seed 與 spread 應產生穩定抽牌；不同 seed 應允許不同結果。
- Human Design：golden sample 對 type、authority、centers、gates；出生時間缺失時應降級。
- Report：AI prompt 中每個強結論都必須能追溯到 signal 或 combo card。
- API：`include_reserved_plugins=false` 時保持現有八字/紫微主線不變。

## 來源備註

- `rauf-21/mbti-personality-test-app`：GitHub README 顯示 70 題 MBTI test app，TypeScript / Next / Chakra UI，約 61 stars。
- `PKU-YuanGroup/Machine-Mindset`：GitHub 顯示 Apache-2.0 license，README 說明 16 型人格模型、資料集與多階段訓練。
- `Personality-NLP/MbtiBench`：README 說明心理師標註、soft labels、286 samples，並標示可供 academic/commercial research 但需遵守 ethical guidelines。
- `ekelen/tarot-api`：README 說明 Rider-Waite-Smith deck REST API、78 張牌隨機/查詢 endpoint，並建議牌圖可參考 public-domain Rider Waite 1909 deck。
- Human Design 相關專案目前只列入待審 inventory；在確認 repo URL、license、資料來源與 golden sample 前，不升級為 implementation dependency。
