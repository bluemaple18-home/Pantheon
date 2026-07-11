# Mystic Engine

純 Python 的模組化算命後端骨架，使用 FastAPI、Pydantic 與插件 registry。這一版先交付可運行的 MVP：同一筆生日資料會同時產出八字、紫微斗數骨架資料，並組裝成 AI 解盤 prompt。

## 快速開始

```bash
uv venv
uv pip install -e ".[dev]"
uvicorn main:app --host 0.0.0.0 --port 8877 --reload
```

測試：

```bash
uv run pytest
```

## 部署 Workflow

公開頁、文章、SEO、sitemap、redirect、cache 版號與部署驗收流程，統一依照：

- `docs/pantheon_deployment_workflow.md`

## API

`POST /api/v1/predict`

```json
{
  "name": "demo",
  "birth_date": "1990-05-15",
  "birth_time": "15:30:00",
  "gender": "female",
  "timezone": "Asia/Taipei",
  "utc_offset": "+08:00",
  "calendar": "solar",
  "location": "Taipei",
  "latitude": 25.033,
  "longitude": 121.5654,
  "birth_time_confidence": "exact",
  "target_year": 2026
}
```

## 外部參考邊界

- `hhszzzz/taibu`：參考 MCP 工具化與多命理系統設計。其 README 標示 `packages/core`、`packages/mcp`、`packages/mcp-server` 為 MIT，其餘多為 AGPL-3.0-only。
- `china-testing/bazi`：參考八字排盤、刑沖合會、五行分數概念。GitHub 頁面目前未清楚顯示 license，因此本專案暫不直接複製其程式碼。
- `Renhuai123/ziwei-doushu`：參考紫微斗數資料集與排盤知識庫。README 標示程式碼 MIT、51.8 萬樣本資料可商用但需保留 attribution。
- `zhenheco/life-chart-engine`：參考西洋星盤、人類圖、紫微三合一 JSON 契約與外部 golden sample 驗證。其 README 標示 repo 為 AGPL-3.0，且依賴 Swiss Ephemeris，因此本專案暫不直接複製或 import 其程式碼；詳細評估見 `docs/life_chart_engine_intake.md`。
- MBTI / 塔羅 / 人類圖外部專案目前只作為研究樣本、資料契約與驗證靶，不直接搬 code 或題庫；融合策略見 `docs/mbti_tarot_hd_fusion_strategy.md`。

目前 `app/calculators/bazi.py` 與 `app/calculators/ziwei.py` 是可替換的 MVP 算力接口，不宣稱等同完整傳統排盤。後續若要接入外部演算法，請先做 license 檢查與 golden sample 驗證。

## 資料匯入

下載 `ziwei-doushu` Releases 的樣本資料後，可用：

```bash
uv run python scripts/ingest_ziwei_samples.py --source ./data/ziwei_samples --db ./app/database/ziwei_samples.sqlite
```

資料來源標註建議放在產品 About、README 或模型卡：

> 本項目使用了紫微斗數開源樣本資料集 v3.0（518,400 條），來源：https://github.com/Renhuai123/ziwei-doushu，作者：王多魚AI。
