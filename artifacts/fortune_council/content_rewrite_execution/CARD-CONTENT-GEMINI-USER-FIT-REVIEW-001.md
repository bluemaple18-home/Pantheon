---
card_id: CARD-CONTENT-GEMINI-USER-FIT-REVIEW-001
status: CARD_DRAFTED
thickness: standard
risk: medium
model: gpt-5.5
reasoning: medium
model_reason: 全站舊文需結合既有稽核、實際正文與使用者情境做一致語意判讀，並協調 Gemini Writer／Reviewer 與可重現品質閘門
ownership: 舊文口語化、搜尋情境與使用者需求回顧，以及核准後的 Gemini 正文候選
allowlist:
  - artifacts/fortune_council/content_rewrite_execution/evidence/gemini_user_fit_review_001/**
  - app/web/static/article-meta.js
  - app/web/static/article-expansion-*.js
forbidden_scope:
  - 新文章與新文章 registry records
  - registry identity、title、slug、URL、description、answer、FAQ、tags、published、updated
  - sitemap、feed、redirects、部署與外部正式環境
  - Gemini／Google 憑證、token、CLI 設定與全域 dotdir
verification:
  - 逐篇 inventory 覆蓋與唯一性
  - Gemini request／response SHA 綁定
  - deterministic quality、uniqueness 與 metadata invariants
  - 受影響 pytest、git diff --check、代表頁瀏覽器驗收
evidence_path: artifacts/fortune_council/content_rewrite_execution/evidence/gemini_user_fit_review_001/
worktree_path: pending_platform_provisioning
cwd: pending_platform_provisioning
main_cwd: <repo-root>
worktree_exists: false
source_branch: main
source_sha: ddcb4efb7da1f91714bbbdfa0875672af37b209e
source_clean: true
index_lock: absent
thread_id: pending
thread_status: CARD_DRAFTED
---

# CARD-CONTENT-GEMINI-USER-FIT-REVIEW-001｜舊文口語化與使用者需求回顧

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-USER-FIT-REVIEW-001`，回顧正式舊文是否自然、貼近搜尋情境，並只對有證據的文章建立 Gemini 改寫候選。
派工對象｜`gpt-5.5`、`medium`；Gemini CLI Writer 與 Reviewer 必須是獨立 headless process，主線保留整合與最終驗收。
任務目的｜以現行 runtime registry 為母體，重新檢查既有 111 篇 `LIGHT_EDIT`、前次未完成的 rewrite 對象與已改寫文章的實際使用者適配度，不因文章舊就自動重寫。
可改範圍｜只可新增本卡 evidence；只有通過 triage 且 Reviewer 核准者，才可修改既有文章正文欄位，metadata identity 全部不可變。
驗收證據｜逐篇 inventory、使用者情境、verdict、問題證據、Gemini receipts、前後 SHA、deterministic gate、跨文重複度、測試與代表頁瀏覽器證據。

## 已知基線

- 前次全站稽核母體為 287 篇：`KEEP=125`、`LIGHT_EDIT=111`、`GEMINI_REWRITE=51`、`BLOCKED=0`。
- 既有 release 顯示 50 篇正文候選已套用；本卡必須先以現行 registry 與正文重新核對，不可把舊數字當成現況完成證據。
- 必讀：
  - `docs/pantheon_article_publication_standard.md`
  - `docs/pantheon_gemini_outbox_runner.md`
  - `artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_audit_001/audit.md`
  - `artifacts/fortune_council/content_rewrite_execution/CARD-CONTENT-GEMINI-REWRITE-RELEASE-001.md`

## 執行契約

1. 從 runtime registry 建立現況 inventory，以 `id + product + slug` 唯一化並讀取實際正文，不得只看 metadata。
2. 每篇先寫明使用者角色、搜尋當下情境、真正想得到的答案、文章目前是否快速回答，以及讀完可採取的下一步。
3. Gemini CLI Reviewer 必須逐篇輸出 `KEEP / HUMAN_LIGHT_EDIT / GEMINI_REWRITE / BLOCKED`，並至少提供兩項文章專屬證據；不得只寫「模板感重」或「不夠口語」。
4. 判定必須檢查：搜尋意圖延遲、真人口吻、模板句、空泛段落、過度抽象、重複骨架、可行下一步、危險或過度斷言。
5. 只有 `GEMINI_REWRITE` 才能送 Gemini CLI Writer；Writer 使用 Flash Low，獨立 Reviewer 使用 Pro Low，每個模型 run 最多 5 篇、最多兩輪 repair／re-review。
6. Gemini 必須走既有 sanitized outbox runner；不得把本機絕對路徑、私密資料、token、`.work/` 內部狀態或未公開 metadata 放進 prompt。
7. Gemini 輸出只可成為候選。只有 request／response SHA、schema、deterministic gate、Reviewer APPROVE 與 metadata invariants 同時成立，才可套用正文。
8. 不得以「更口語」為由加入俗套、裝熟、保證式命理、醫療／法律／投資建議或無來源事實。

## 必交付

- `inventory.csv`：逐篇現況、來源、字數、舊 verdict、新 verdict、使用者情境、問題碼、理由與 batch。
- `audit.md`：覆蓋率、verdict 分布、代表案例、是否值得 Gemini 改寫的決策依據。
- `gemini_queue.md`：只列 `GEMINI_REWRITE`，每篇附公開 brief、不可變欄位與具體使用者需求。
- `receipts/`：每次 Gemini Writer／Reviewer 的 request SHA、response SHA、model role、status 與 schema 結果，不保存秘密。
- `apply-verification.json`：逐篇原文 SHA、候選 SHA、正式正文 SHA 與 metadata 零漂移結果。
- `verification.txt`：可重現指令、測試、uniqueness findings、changed-file allowlist 與 `git diff --check`。
- `browser/`：至少 5 個不同產品／情境代表頁的桌面與行動版驗收摘要。

## 禁止範圍

- 不建立新文章、不加入 registry record、不改 title、slug、URL、description、answer、FAQ、tags、published、updated。
- 不修改 sitemap、feed、redirects、部署設定或正式環境。
- 不安裝、不登入、不修改 Gemini CLI、OAuth、token store、MCP config 或全域 ai-core。
- 不攜帶主工作區未提交 binary、截圖或無關 artifacts。

## 驗收與交付

- inventory 唯一文章數必須等於現行 runtime registry 唯一文章數，四種 verdict 總數必須相等。
- 每個 `GEMINI_REWRITE` 至少兩項文章專屬證據；每個套用正文都必須有獨立 Reviewer APPROVE。
- deterministic findings 與跨文章 uniqueness findings 必須為 0；metadata identity 必須零漂移。
- 執行受影響 pytest、內容 gate、`git diff --check` 與代表頁瀏覽器驗收。
- 交付時建立 candidate commit 並回報完整 SHA；只能宣稱 `DELIVERED_CANDIDATE`，不得宣稱已整合、已部署或已上線。
- 同一 blocker 失敗三次立即停止，不做第四次嘗試。

## Gate 狀態

- Gate 1：實體卡已建立，等待正式 thread 與獨立 worktree receipt。
- Gate 2–5：尚未開始，禁止預填通過。
