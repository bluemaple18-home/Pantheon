# Article Expansion 50D｜整合與發布證據

- 文章總數：279（本批新增 50）
- MBTI：16 篇，`personality-0037`～`personality-0052`
- 星盤：17 篇，`astrology-0028`～`astrology-0044`
- 命理：17 篇，`fortune-0027`～`fortune-0043`

## Candidate / Review

- MBTI 最終 candidate：`c0fb263c55d9a37df95bb9b7e4c64dcff43753e7`
  - reviewer thread：`019f6aa5-ca54-70a3-b8bb-c5cb3992d2e4`
  - verdict：GO；reviewed commit 與 candidate 一致。
- 星盤 candidate：`42b957fe209b464e1d3245f766fd50a01f9d1c3d`
  - reviewer thread：`019f6aa5-ca5b-7981-8978-ee40e260a537`
  - verdict：GO；reviewed commit 與 candidate 一致。
- 命理 candidate：`dea03274cfde01a3497c47c7ddc90e7a34173475`
  - reviewer thread：`019f6aa5-ca5d-7071-99ad-50fa8345f419`
  - verdict：GO；reviewed commit 與 candidate 一致。

## 自動驗證

- `.venv/bin/python -m pytest -q`：98 passed。
- JS `node --check`、Python `py_compile`、`git diff --check`：通過。
- registry：279 records。
- 最新文章前四篇：`personality-0052`、`tarot-0080`、`fortune-0043`、`astrology-0044`。
- prerender、sitemap、redirects、feed：已重建。

## Browser Acceptance

- 本機服務：目前工作樹，`127.0.0.1:8878`，驗收後已停止。
- 6 篇 50D 代表文章：4 sections、5 FAQ、更新日期 2026-07-16。
- `/articles`：最新順序符合預期。
- 390px mobile：無橫向溢出。
- traceback / pageerror / requestfailed / 相關 console error / 文章資產 4xx、5xx：0。
- 瀏覽器自動請求 `/favicon.ico` 為既有 404，與本批文章資產無關，原始紀錄保留於 `browser-acceptance.json`。
- verdict：GO。
