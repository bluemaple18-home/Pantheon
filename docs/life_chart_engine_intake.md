# life-chart-engine Intake

日期：2026-06-08
狀態：研究參考，不直接導入程式碼；2026-07-11 重新核對 GitHub 頁面後，license 判定由舊 AGPL 記錄改為目前 README 顯示的 MIT，但產品化前仍需重新審依賴授權。

## 結論

`zhenheco/life-chart-engine` 對 Pantheon 有幫助，但適合當「外部驗證器 / 欄位參考 / golden sample 來源」，不適合直接成為主程式依賴。

主要原因：

- 它能從同一筆出生資料輸出西洋星盤、人類圖、紫微斗數 JSON，剛好補 Pantheon 目前 `ziwei` 與 `human_design` 算力偏薄的問題。
- 它依賴 `pyswisseph` 與 `py-iztro`，並要求 CPython 3.12；Pantheon 目前是 Python `>=3.11` 的純 FastAPI 插件架構。
- repo 目前 README 顯示 MIT，但仍依賴天文/曆法與第三方套件；若 Pantheon 要走 closed-source SaaS，產品化前仍需重審 dependency license 與商用邊界。

## 外部 repo 現況

根據 GitHub README，`life-chart-engine` 是離線 CLI，輸入出生日期、時間、時區與座標後，產出 Markdown 或 JSON，給程式與 AI agent 使用。

它計算三套系統：

| 系統 | repo 輸出 | 對 Pantheon 價值 |
|---|---|---|
| Western natal | Ascendant、Midheaven、planets、houses、aspects | 可新增 `western_astrology` calculator 或作為未來圖表/報告模組 |
| Human Design | type、authority、profile、definition、incarnation_cross、centers、channels、gates | 可補目前 `HumanDesignCalculator` 只有 reserved 狀態的缺口 |
| Zi Wei Dou Shu | five_elements_class、soul、body、hour_index、palaces、horoscope | 可校準目前 `ZiweiCalculator` 的 MVP scaffold |

## Pantheon 對照

Pantheon 目前重點是「模組化算命後端骨架」：

- `app/calculators/base.py` 定義共同 calculator 介面。
- `app/core/registry.py` 透過 registry 掛載 `bazi`、`ziwei`、`human_design`、`mbti`、`tarot`。
- `app/calculators/ziwei.py` 明確標示 `algorithm_level = "mvp_scaffold"`。
- `app/calculators/hd.py` 目前只回傳 reserved 狀態。

所以最佳接法不是複製外部實作，而是把它的 JSON 當作外部事實來源，轉成 Pantheon 的中介語法。

紫微整合策略見 `docs/ziwei_fusion_strategy.md`。Pantheon 會以自有/`ziwei-doushu` 路線作 primary provider，`life-chart-engine` 僅作 secondary validator 與補缺材料。

## 欄位映射草案

| life-chart-engine 欄位 | Pantheon 目標欄位 | 處理方式 |
|---|---|---|
| `input.name` | `BirthInput.name` | 直接映射 |
| `input.gender` | `BirthInput.gender` | `男/女` 需轉成 `male/female`；`other` 無法完整支援紫微 |
| `input.date` | `BirthInput.birth_date` | 直接映射 |
| `input.time` | `BirthInput.birth_time` | 直接映射 |
| `input.tz_offset` | `BirthInput.timezone` / 新欄位 | Pantheon 目前收 IANA timezone，不收 offset；需新增 normalization 層 |
| `input.lat` / `input.lon` | `BirthInput.location` / 新欄位 | 現有 `location` 是字串，不足以供西洋星盤與人類圖使用 |
| `western.ascendant` | `charts.western_astrology.ascendant` | 新 calculator 候選欄位 |
| `western.midheaven` | `charts.western_astrology.midheaven` | 新 calculator 候選欄位 |
| `western.planets[]` | `charts.western_astrology.planets[]` | 可轉成 evidence signal |
| `western.houses[]` | `charts.western_astrology.houses[]` | 需要完整座標與準確出生時間 |
| `western.aspects[]` | `notable_patterns[]` | 轉成關係型 pattern，例如 `western.aspect.sun.moon.trine` |
| `human_design.type` | `charts.human_design.type` | 補目前 reserved 插槽 |
| `human_design.authority` | `charts.human_design.authority` | 補目前 reserved 插槽 |
| `human_design.profile` | `charts.human_design.profile` | 補目前 reserved 插槽 |
| `human_design.defined_centers[]` | `charts.human_design.centers.defined[]` | 命名需 normalize |
| `human_design.open_centers[]` | `charts.human_design.centers.open[]` | 命名需 normalize |
| `human_design.channels[]` | `charts.human_design.channels[]` | 可轉成格局卡 |
| `human_design.gates[]` | `charts.human_design.gates[]` | 可轉成 evidence signal |
| `ziwei.five_elements_class` | `charts.ziwei.five_elements_class` | 可直接新增 |
| `ziwei.soul` / `ziwei.body` | `charts.ziwei.soul_star` / `body_star` | 命名 normalize |
| `ziwei.hour_index` | `charts.ziwei.hour_index` | 可直接新增 |
| `ziwei.palaces[]` | `charts.ziwei.palaces[]` | 可用來取代現有假資料 palaces |
| `ziwei.horoscope` | `charts.ziwei.horoscope` | 標記 best-effort；不可當核心證據 |
| `meta.engine` / `meta.version` | `metadata.external_engines[]` | 來源追蹤與報告 attribution |

## Golden samples

先用三組固定樣本建立驗證，不要一次擴太大。

| 樣本 | 目的 | 輸入 |
|---|---|---|
| Taipei baseline | 對齊 repo README 範例，驗證 JSON parser 與欄位映射 | `1990-06-15 08:30`, UTC+8, `25.033`, `121.5654`, female |
| Midnight boundary | 測時辰、宮位、Human Design line 對邊界時間敏感度 | `1990-06-15 23:50`, UTC+8, Taipei |
| DST city | 驗證 caller 必須處理 DST-aware offset，不可只用 IANA timezone 名稱假裝完成 | `1990-06-15 08:30`, New York, 當日正確 UTC offset |

驗證條件：

- JSON 必須有 `ok = true`。
- `western.planets[]`、`western.houses[]`、`human_design.gates[]`、`ziwei.palaces[]` 不可為空。
- Pantheon adapter 不可在外部工具失敗時 fabricated chart values。
- 若缺 `lat/lon/tz_offset`，adapter 必須回傳 validation error，不得 fallback 到 Taipei 101 之類預設值。

## 採用策略

### Phase 1：只做外部驗證器

建立一個非產品路徑的驗證腳本，例如：

```text
scripts/compare_life_chart_engine.py
```

它只負責：

- 呼叫本機已安裝的 `life-chart --json`。
- 讀 stdout JSON。
- 將外部 JSON 轉成 Pantheon 中介 schema。
- 與 golden samples snapshot 比對。

目前已實作 `scripts/compare_life_chart_engine.py`：

- 預設執行 `life-chart --json`，也可用 `--input-json` 讀既有輸出。
- 只使用 subprocess 呼叫外部 CLI，不 import 或 vendoring 外部程式碼。
- 驗證 `ok=true`，且 `western.planets[]`、`western.houses[]`、`human_design.gates[]`、`ziwei.palaces[]` 必須為非空陣列。
- 輸出 Pantheon normalized JSON，含 `western_astrology`、`human_design`、`ziwei` 三個 chart payload 與 `metadata.external_engine`。
- 可用 `--expect-json` 對照 normalized snapshot。

範例：

```bash
uv run python scripts/compare_life_chart_engine.py --sample taipei_baseline
uv run python scripts/compare_life_chart_engine.py --input-json /path/to/life-chart-output.json
```

### Phase 2：補 Pantheon schema

優先新增：

- `BirthInput.latitude`
- `BirthInput.longitude`
- `BirthInput.utc_offset`
- `BirthInput.birth_time_confidence`

`timezone` 可以保留，但不能取代出生當地當日的 UTC offset。這是西洋星盤、人類圖、紫微時辰共同的精準度來源。

### Phase 3：產品化前再決定算力來源

可選路線：

| 路線 | 優點 | 風險 |
|---|---|---|
| 外部 local subprocess | 最快、最少衍生作品風險 | 仍需 dependency license 重審與安裝 UX |
| 商業 Swiss Ephemeris license | 可保留高品質星曆 | 需法務與授權費 |
| 替換 permissive ephemeris | closed-source 風險最低 | 要重寫西洋星盤與 HD 基礎計算 |
| 只借欄位契約，不借 code | 最安全 | 需要自己補算力 |

## 不採用邊界

目前不做：

- 不把 `life-chart-engine` 加進 `pyproject.toml`。
- 不複製它的 `scripts/chart_engine.py`。
- 不把外部 repo code 混進 `app/calculators/`。
- 不宣稱 Pantheon 的現有紫微輸出已等同完整排盤。

## 來源

- GitHub repo: https://github.com/zhenheco/life-chart-engine
- README 說明它是三合一離線 CLI，輸出 Markdown/JSON 給程式與 AI agent。
- README 標示直接依賴 `pyswisseph==2.10.3.2` 與 `py-iztro==0.1.5`，並要求 CPython 3.12。
- 2026-07-11 核對 GitHub README 與 repo badge，頁面顯示 repo license 為 MIT；本文件舊版 AGPL 記錄已降級為歷史註記。
- 產品化前仍需重新審 `pyswisseph`、`py-iztro`、星曆資料與任何外部計算依賴的商用條件。
