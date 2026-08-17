# Publisher Registry Node Recovery

## 工作名稱 → 正在做什麼 → 現在狀態

Publisher Registry Node Recovery → 修正 Publisher 在 prerender 前讀取 article registry 時的無界等待 → 本機修補與測試完成，production 未部署

## Root question

為什麼前三線可完成，Publisher 卻持續停在 transaction，且原先加入的 prerender timeout 沒有生效？

## 已確認根因

- Publisher 在進入 prerender 前會呼叫 `agy_seo_copy_pipeline._registry_inventory()`。
- 該函式用 `subprocess.run(..., capture_output=True)` 啟動 Node，沒有 timeout。
- Node 後代程序若繼承 stdout/stderr，直接 Node 程序退出後，Python 仍可能因 PIPE 未收到 EOF 而無界等待。
- 原修補只包住後段 `prerender_article_shells.py`，因此修錯邊界。

## 可改範圍

- `scripts/agy_seo_copy_pipeline.py`
- `tests/test_agy_seo_copy_pipeline.py`

## 禁止範圍

- 不啟動、部署或修改 production。
- 不修改 queue、registry 內容、文章、sitemap、feed 或 redirects。
- 不清除使用者既有未追蹤檔案。

## 驗收

- registry Node 呼叫有 300 秒 fail-closed timeout。
- stdout/stderr 不使用 PIPE，等待只綁定直接子程序。
- timeout 時終止完整 Node process group。
- 三個 registry Node 入口共用同一執行器。
- `tests/test_agy_seo_copy_pipeline.py`、`tests/test_agy_content_publisher.py`、`git diff --check` 通過。

## 停止條件

本機驗收完成即停；不得在本卡內重新 activation 或 production canary。
