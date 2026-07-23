---
card_id: CARD-CONTENT-DAILY-AUTOPUBLISH-001
status: IMPLEMENTING
thickness: strict
risk: high
ownership: 每日單篇受監督自動產文、發布與失敗停損
allowlist:
  - artifacts/fortune_council/content_seo_execution/CARD-CONTENT-DAILY-AUTOPUBLISH-001.md
  - artifacts/fortune_council/content_seo_execution/evidence/scale_clusters/cluster_plan.md
  - docs/pantheon_content_transport_decoupling.md
  - Codex automation Pantheon 每日單篇發文
forbidden_scope:
  - scripts/agy_gemini_v4_broker.py
  - AGY_GEMINI_V4_BROKER=1
  - Reviewer REJECT 或 deterministic finding 的 override
  - 每次超過一篇
  - dirty worktree、非 main、HEAD 與 origin/main 不一致時發布
verification:
  - daily backlog 非空且與現有 registry 去重
  - 每輪只建立一篇 brief
  - Gemini CLI Writer 與獨立 Reviewer receipts
  - deterministic findings 為空且 Reviewer APPROVE
  - release version、CHANGELOG、annotated tag 與 release gate
  - full pytest、git diff --check、本機與正式頁驗收
---

# Pantheon 每日單篇自動發文

## 目標

恢復每天一篇公開文章。內容線使用既有 Gemini CLI，不等待 V4；V4 維持獨立技術改善。

## 每輪控制流

1. 確認 `main`、worktree clean、`HEAD == origin/main`，否則停止。
2. 從 cluster plan 的未上線 backlog 取第一篇，最多一篇。
3. 建立公開 brief，使用既有 CLI Writer 與 fresh Reviewer。
4. deterministic findings 必須為空，Reviewer 必須 `APPROVE`，不得 override。
5. 建立 policy approval、apply 至文章 registry 與正文模組。
6. 更新版本、CHANGELOG、prerender、sitemap 與 feed，執行完整測試。
7. 建立 release commit 與 annotated tag，同次 push `main` 與 tag。
8. 驗收正式文章 URL；保存 commit、tag、URL、HTTP、canonical 與文章標題。

## 停損

- 任一 Gemini、schema、內容 Gate、測試、release gate、push 或正式頁驗收失敗即停止。
- 不自動 retry 外部 generation 或 push。
- 不使用 V4 fallback。
- backlog 為空時回報 `IDLE_NO_BACKLOG`，不得自行發明題目。

## 初始 Queue

初始七篇均為現有 registry 未出現的星盤使用者情境題，寫在
`evidence/scale_clusters/cluster_plan.md` 的「每日單篇自動發文 Queue」。
