---
card_id: CARD-CONTENT-GEMINI-REWRITE-AUDIT-001
status: INTEGRATED
thickness: standard
risk: medium
model: gpt-5.5
reasoning: medium
model_reason: 全站逐篇內容品質判讀需要一致語意標準與跨批次比較，不屬於純欄位擷取
ownership: 全站舊文改寫必要性稽核與 Gemini 候選佇列
allowlist:
  - artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_audit_001/**
forbidden_scope:
  - app/**
  - tests/**
  - scripts/**
  - registry、metadata、prerender、sitemap、feed、redirects 與任何正式文章正文
evidence_path: artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_audit_001/
worktree_path: <codex-worktree>/Pantheon
cwd: <codex-worktree>/Pantheon
main_cwd: <repo-root>
worktree_exists: true
source_branch: main
source_sha: 0782567831fbbcaf78daaddc70bf1b417b232a02
source_clean: true
git_metadata_writable: true（Codex 平台已成功建立 worktree）
index_lock: absent
unrelated_dirty_paths: 主工作區既有未追蹤檔；不得帶入新 worktree
thread_id: 019f741c-0628-7322-ae87-9c71c1ca24a7
thread_status: DELIVERED
mainline_commit: b71463c
integration_scope: audit_evidence
---

# CARD-CONTENT-GEMINI-REWRITE-AUDIT-001｜全站舊文 Gemini 改寫必要性稽核

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REWRITE-AUDIT-001`，只做全站舊文盤點與改寫建議。
派工對象｜`gpt-5.5`、`medium`；主線負責覆蓋率、判定一致性與後續是否送 Gemini 的最終驗收。
任務目的｜掃描正式文章 registry 所涵蓋的每一篇文章，逐篇判定 `KEEP / LIGHT_EDIT / GEMINI_REWRITE / BLOCKED`，不得抽樣。
可改範圍｜只可新增 `artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_audit_001/` 下的稽核成果；所有程式、文章、registry 與生成檔唯讀。
驗收證據｜交付逐篇 inventory、判定與理由、問題碼、優先級、來源檔定位、Gemini 批次佇列、覆蓋率／唯一性檢查及執行紀錄。

## 掃描母體與判定契約

- 母體以 runtime `ARTICLE_REGISTRY` 實際可列出的正式文章為準，納入其 import 的所有 expansion records；以文章 `id + product + slug` 去重。
- 每篇都必須讀取實際 body，不得只看 title、meta、日期或 prerender HTML。
- `KEEP`：符合最新版文章發布規範，無明顯模板腔、重複句、空泛段落、過度斷言或搜尋意圖落差。
- `LIGHT_EDIT`：局部可修，預估不需重寫全文；列出精確問題與建議修改區段。
- `GEMINI_REWRITE`：結構、語氣、情境、可信度或重複度問題已達全文改寫更划算；必須列出至少兩項文章專屬證據。
- `BLOCKED`：缺正文、來源無法解析、registry/body 對不上或規範衝突；不可用 `KEEP` 掩蓋。
- 不因文章「舊」就自動改寫，也不因已被前一批處理過就自動保留；以目前內容重新判讀。
- 後續改寫順序採全域流水號尾碼數字升冪；排序鍵為 `priority → serial number → product/category → id`，不先按分類分組。每個 Gemini batch 最多 5 篇。

## 必交付檔案

- `inventory.csv`：每篇一列，至少包含 id、product、slug、title、source_file、body_source、char_count、verdict、priority、issue_codes、reason、gemini_batch。
- `audit.md`：總數、各 verdict 數量、問題分布、優先批次、判定準則與代表案例。
- `gemini_queue.md`：只列 `GEMINI_REWRITE`，按 P0/P1/P2 分批；每篇附不可變更欄位與具體改寫 brief，不直接執行改寫。
- `gemini_queue.md` 的 Batch 1 必須從所有 `GEMINI_REWRITE` 中流水號數字最小者開始；`KEEP` 不得進入改寫批次。
- `verification.txt`：記錄 registry 總數、inventory 唯一列數、缺漏、重複、body 缺失與使用的可重現指令。

## 禁止範圍

- 不修改任何文章正文、title、slug、meta、FAQ、Schema、內鏈、日期或發布狀態。
- 不修改 shared registry、生成器、prerender、sitemap、feed、redirects、測試與部署設定。
- 不呼叫 Gemini 或任何外部寫入服務；本卡只建立候選佇列與改寫 brief。
- 不把主工作區未追蹤 binary、截圖或既有 artifacts 帶入隔離 worktree。

## 驗證與交付

- `inventory.csv` 的唯一文章數必須等於 runtime registry 的唯一文章數。
- `KEEP + LIGHT_EDIT + GEMINI_REWRITE + BLOCKED` 必須等於 inventory 總數。
- 每個 `GEMINI_REWRITE` 至少有兩項文章專屬理由，不得只寫「模板感重」。
- 執行 `git diff --check`，並確認 changed files 全部位於 evidence allowlist。
- 交付時建立 candidate commit，回報完整 SHA；只能宣稱 `DELIVERED_CANDIDATE`，不得宣稱已改寫、已整合或已驗收。
- 同一 blocker 失敗三次立即停止，不做第四次嘗試。

## Thread Receipt

- 正式 thread ID：`019f741c-0628-7322-ae87-9c71c1ca24a7`
- 標題：`CARD-CONTENT-GEMINI-REWRITE-AUDIT-001｜全站舊文改寫稽核`
- 建立環境：Codex 專案獨立 worktree；cwd 與主工作區不同。
- list 查詢：可查，狀態 `active`；首回合 `inProgress`。
- preview：包含本卡 ID、全量掃描、四類 verdict、allowlist、禁止範圍與交付契約。
- 主工作區既有未追蹤檔未以 `working-tree` 帶入。

## Gate 狀態

- Gate 1：卡片與完整派工契約已建立。
- Gate 2：正式 thread 可由 list 查詢、標題與 preview 正確、cwd 為獨立 worktree，任務執行中。
- Gate 3–5：尚未開始，禁止預填通過。
