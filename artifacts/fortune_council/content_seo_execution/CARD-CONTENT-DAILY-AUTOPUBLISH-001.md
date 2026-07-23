---
card_id: CARD-CONTENT-DAILY-AUTOPUBLISH-001
status: READY_FOR_HIGH_FREQUENCY
thickness: strict
risk: high
ownership: repo harness 持續產文、每批最多五篇、批次發布與失敗停損
allowlist:
  - artifacts/fortune_council/content_seo_execution/CARD-CONTENT-DAILY-AUTOPUBLISH-001.md
  - artifacts/fortune_council/content_seo_execution/evidence/scale_clusters/cluster_plan.md
  - artifacts/fortune_council/content_seo_execution/evidence/content_matrix_v2/content-matrix-v2.json
  - artifacts/fortune_council/content_seo_execution/evidence/content_matrix_v2/README.md
  - scripts/generate_content_matrix_v2.py
  - scripts/agy_seo_copy_pipeline.py
  - tests/test_agy_seo_copy_pipeline.py
  - docs/pantheon_content_transport_decoupling.md
  - Codex automation Pantheon 每日單篇發文
forbidden_scope:
  - scripts/agy_gemini_v4_broker.py
  - AGY_GEMINI_V4_BROKER=1
  - Reviewer REJECT 或 deterministic finding 的 override
  - 每次超過五篇
  - 多批同時修改 main、版本、registry 或 release tag
  - dirty worktree、非 main、HEAD 與 origin/main 不一致時發布
verification:
  - daily backlog 非空且與現有 registry 去重
  - 每輪最多取五篇，維持 backlog 固定順序
  - 每個 brief 都有 Gemini CLI Writer 與 fresh independent Reviewer receipts
  - 全批 deterministic findings 為空且每篇 Reviewer APPROVE
  - release version、CHANGELOG、annotated tag 與 release gate
  - full pytest、git diff --check、本機與正式頁驗收
---

# Pantheon 高頻內容 Harness

## 目標

每日目標至少 100 篇。由 repo 內 `agy_gemini_coordinator` 持續消化 Queue，
不依賴 Codex App automation。每批最多五篇，但每篇使用獨立 Writer run。
內容線使用既有 Gemini CLI，不等待 V4；V4 維持獨立技術改善。

## 每輪控制流

1. 確認 `main`、worktree clean、`HEAD == origin/main`，否則停止。
2. 先從 cluster plan 的未上線 backlog 依序取最多五篇；舊 Queue 用完後接續 content matrix v2。
3. 每篇建立獨立公開 brief，依序使用既有 CLI Writer 與各自的 fresh Reviewer。
4. 全批 deterministic findings 必須為空，每篇 Reviewer 都必須 `APPROVE`，不得 override。
5. 全批通過後才建立 policy approval，一次 apply 至文章 registry 與正文模組。
6. 更新版本、CHANGELOG、prerender、sitemap 與 feed，執行完整測試。
7. 全批只建立一個 release commit 與一個 annotated tag，同次 push `main` 與 tag。
8. 驗收全批正式文章 URL；保存 commit、tag、URL、HTTP、canonical 與文章標題。

## Harness、吞吐與併發

- Coordinator 每 60 秒取得至多一個外部 job；用 checkpoint 持續推進，不建立 App 排程。
- 每批最多五篇，但 Writer／Reviewer 都是一篇一個隔離 run，避免多篇 JSON 與內容互相污染。
- 每篇允許初稿加最多兩次 findings-bound repair；第三次同 blocker 仍失敗就停，不做第 4 次。
- 前一批尚未結束時，下一批不得平行發布；只有單一 actor 可修改 main。
- backlog 少於五篇時只處理剩餘篇數，不補造題目。
- 任一篇失敗即停止整批，不 apply 部分成功文章，也不跳過失敗題目。

## 停損

- 任一 Gemini、schema、內容 Gate、測試、release gate、push 或正式頁驗收失敗即停止整批。
- 不自動 retry 外部 generation 或 push。
- 不使用 V4 fallback。
- 兩份矩陣 backlog 都為空時回報 `IDLE_NO_BACKLOG`，不得自行發明題目。

## 初始 Queue

初始七篇均為現有 registry 未出現的星盤使用者情境題，寫在
`evidence/scale_clusters/cluster_plan.md` 的「每日單篇自動發文 Queue」。

## 第二期 Queue

初始 Queue 跑完後，接續
`evidence/content_matrix_v2/content-matrix-v2.json`。第二期共有 1,720 個候選題，
每一列只對應「一個單體或一組配對 × 一個生活情境」，不得把五個情境合成一篇。

- 單體情境：星座 60、MBTI 80、塔羅 390、紫微主星 70、八字十神 50。
- 配對情境：MBTI 配對 680、星座配對 390。
- 配對採無方向 canonical 組合，`A × B` 與 `B × A` 不重複。
- registry 已有同 ID 或語意等價主題仍須略過，不得為了湊數重複發布。
