---
id: APF-001
status: ready
type: implementation
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: implementation
cycle: 1
thickness: standard
risk: medium
model: gpt-5.6-terra
reasoning: medium
model_reason: 邊界固定的跨檔盤點與 deterministic dry-run workset；不碰 production、排程或 Publisher mutation。
traces_to:
  - US-001
  - US-002
  - FR-017
  - SC-001
---

# APF-001｜自動來源與 campaign 契約

## Root Question

如何沿用 Pantheon 唯一 Control Plane，讓題庫新文與全部 eligible 舊文形成可重跑、不重複、具版本與可追溯 identity 的四 lane dry-run 工作集合？

## 任務目的

從乾淨 source commit 盤點現有題庫、rewrite lifecycle、四 lane coordinator、i18n 與 Existing Publisher 的 owner／I/O；補出最小 source-to-publish contract 與 side-effect-free dry-run workset。先證明來源與 campaign 契約，不啟動正式 runtime 或發布。

## 已知基線

- 唯一 Control Plane：既有 Pantheon coordinator／queue／lock／approval／Publisher。
- lanes：`new`、`rewrite`、`i18n-new`、`i18n-rewrite`。
- Existing Publisher 是唯一 publication owner；本卡只能讀其邊界或呼叫 side-effect-free validator。
- Writer vNext contracts 已有 `ArticleBriefV2`、`EditorialManifestV1` 與 legacy compatibility validation。
- `origin/main` baseline：`038cb1fd1cc29ffe234ac213222938b699ab4082`；本卡 source commit 會在其上只加入本卡。
- Auto Publishing First 是唯一 active frontier。V9 parked；Blind Reader、Claims、Humanizer、SEO／AEO／GEO deferred。

## Ownership 與可改範圍

唯一輸出 owner：本 task／worktree。

允許修改：

- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`
- `docs/pantheon_writer_vnext_auto_source_campaign_contract.md`
- `artifacts/fortune_council/content_writer_vnext_execution/apf_001/**`

其餘檔案唯讀。若實作確實需要額外 source/test 檔，先停止並回報 `SCOPE_EXPANSION`；不得自行擴大 allowlist。

## 禁止範圍

- 禁止修改或啟動 Publisher、LaunchAgent、scheduler、production runtime、deploy、tag、push。
- 禁止清空、重送、改寫既有 queue／state／ledger／lock。
- 禁止建立第二套 queue、scheduler、lock、approval、Publisher 或 Control Plane。
- 禁止碰 V9、GEO、SEO/AEO、Blind Reader、Claims、Humanizer、前端、sitemap、feed、redirects。
- 禁止人工逐篇觸發作為最終設計。
- 禁止帶入主工作區 dirty／untracked 內容；只以本 task source commit 與原始碼為準。
- 禁止用單篇成功、測試數、服務啟動或舊 receipt 宣稱全自動鏈完成。

## 執行契約

1. 先跑 worktree／Git preflight；CodeGraph ready 後，用任務語意查詢 source selection、rewrite inventory、lane routing、translation enqueue、Publisher collection seam，再讀原始碼確認。
2. 先產 owner／I/O map：每一來源、lane、state owner、identity、dedupe key、輸入、輸出、下游 seam。
3. 定義 versioned campaign identity。至少包含：`source_kind`、`article_id`、`locale`、`campaign_version`、stable work identity；同一輸入重跑 identity 不變。
4. 建立 side-effect-free dry-run workset：
   - 題庫 new：排除已發布、已 active、已 queued、已成功完成的 identity。
   - rewrite：列出全部 eligible 舊文，不清空或重送現有 queue；既有 active／completed／skipped 狀態須可解釋。
   - i18n lanes：只描述由 source publication candidate 衍生的 identity，不預先建立 production run。
   - 輸出 deterministic ordering 與摘要 counts。
5. 若現有 seam 足夠，優先薄包裝；禁止新 workflow engine。若契約矛盾，fail loud 並保留可重現 fixture。
6. 邏輯變更走 RED→GREEN；測試 public behavior，不綁私有實作名稱。

## Acceptance

- `AC-APF001-01`：相同 fixture 連跑兩次，workset JSON byte-stable 或 canonical-json-stable，且無 duplicate work identity。
- `AC-APF001-02`：每項工作具 `source_kind`、`article_id`、`locale`、`campaign_version`、`work_id`、`lane`、`reason`。
- `AC-APF001-03`：new dedupe 同時排除已發布與現存 active／queued／completed identity。
- `AC-APF001-04`：rewrite dry-run 覆蓋全部 eligible inventory；既有 queue 不被清空、修改或批次重送。
- `AC-APF001-05`：四 lane owner／I/O map 明確；不得新增第二 owner。
- `AC-APF001-06`：dry-run 不寫 queue、state、ledger、article、Git ref 或 production runtime。
- `AC-APF001-07`：campaign version 改變時 work identity 可區分；同 version 重跑不得重複。
- `AC-APF001-08`：trace preflight 無 dangling ID；若 source commit 缺正式產品 spec，須在 evidence 明示，不得偽稱 spec 已提交。

## Verification

- 針對新增行為的 focused pytest。
- 既有 `tests/test_agy_gemini_coordinator.py` 全檔。
- 受影響的 coordinator side-effect-free CLI／fixture dry-run；重跑並比較 canonical output。
- `git diff --check`。
- `git status --short`、`git diff --name-only <source_sha>...HEAD` 必須只落 allowlist。
- 不跑 production Publisher，不啟動任何 LaunchAgent。

## Evidence 與交付

證據根：`artifacts/fortune_council/content_writer_vnext_execution/apf_001/`

至少交付：

- `source_owner_io_map.md`
- `dry_run_workset.json`
- `verification_receipt.md`
- candidate commit 完整 SHA
- changed files、測試命令／結果、已知 gap、下一 frontier 判定

交付狀態只能是 `DELIVERED_CANDIDATE` 或 `BLOCKED`；不得宣稱已整合、已發布或 production ready。禁止 commit 以外的外部 mutation。

## Stop Conditions

- 需要修改 allowlist 外檔案。
- 發現 owner／identity 契約互相衝突，無法以薄轉接解決。
- 需要 production、外部 provider、queue mutation 或新 authority 才能驗證。
- 同一 blocker 第三次失敗。
