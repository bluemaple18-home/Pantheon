# TASK-001 Brief

## Root Question

搭建「高擴充性 AI 萬能算命引擎」的純 Python FastAPI 後端骨架。

## Scope

- 建立 `uv + .venv` Python 3.11+ 專案。
- 實作 FastAPI API、calculator base class、插件 registry。
- 建立八字、紫微、MBTI、人類圖、塔羅插件插槽。
- 實作 `/api/v1/predict`，同一筆生日資料可回傳八字與紫微 dict，以及 AI prompt/summary。
- 補紫微樣本資料匯入腳本與 attribution 文件。

## Out Of Scope

- 直接下載 5.5 GB 紫微樣本資料。
- 在未確認授權前直接複製 `china-testing/bazi` 程式碼。
- 宣稱 MVP 算力等同完整傳統排盤。
