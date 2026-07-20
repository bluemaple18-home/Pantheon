---
card_id: CARD-CONTENT-GEMINI-CONTRACT-REPAIR-001
chain_id: CONTENT-GEMINI-CONTRACT-REPAIR-001
status: RUNNING
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 共同 Gemini 產文契約同時影響新文與舊文，需修復 strict JSON、publication gate 對齊、逐篇隔離與部分交付 invariant，回退成本高
ownership: Gemini Writer 輸出契約、publication prompt 編譯、單篇隔離產製、逐篇續跑與 canary 驗證
allowlist:
  - scripts/agy_seo_copy_pipeline.py
  - scripts/agy_gemini_outbox.py
  - scripts/agy_gemini_runner.py
  - tests/test_agy_seo_copy_pipeline.py
  - tests/test_agy_gemini_outbox.py
  - docs/pantheon_gemini_outbox_runner.md
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_contract_repair_001/**
forbidden_scope:
  - app/**
  - 正式文章、registry、metadata、prerender、sitemap、feed、redirects
  - 原 BLOCKED run 的任何 attempt、receipt 或 retry identity
  - deploy、publish、push、production、OAuth、token、Gemini CLI 安裝或全域設定
verification:
  - red-capable regression tests
  - prompt/gate contract parity tests
  - single-article request and partial-manifest tests
  - strict JSON fail-closed and resumability tests
  - four-article Gemini canary
  - focused/full pytest、git diff --check、allowlist
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_contract_repair_001/
worktree_path: <codex-worktree>/e2d42265-1097-4341-b030-8eba32c67993/Pantheon
cwd: <codex-worktree>/e2d42265-1097-4341-b030-8eba32c67993/Pantheon
main_cwd: <repo-root>
worktree_exists: true
source_branch: main
source_sha: 569b46e010cf8d2ffccfab55496077d5efbac9d4
source_clean: true
index_lock: absent
thread_id: 019f7fb1-60b5-7183-bd55-99eaeb503107
thread_status: RUNNING
previous_thread_id: 019f7faf-6973-7633-ab36-1a66ff6a9aa3
previous_thread_status: BLOCKED_PROVISIONING_PREFLIGHT
---

# CARD-CONTENT-GEMINI-CONTRACT-REPAIR-001｜Gemini 產文契約與容錯修復

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-CONTRACT-REPAIR-001`，修復舊文與新文共同命中的 Gemini JSON 與 publication contract 根因。
派工對象｜`gpt-5.6-sol`、`high`；只修 pipeline、runner 契約與測試，用 4 篇新 identity 做 Gemini canary，不恢復大量產文。
任務目的｜把多篇長文外部回傳拆成單篇 strict JSON、把 deterministic gate 規格編譯進 Writer／repair prompt，並讓成功文章可逐篇封存而不被其他失敗項污染。
可改範圍｜只可修改三個既有 pipeline／runner 檔、兩份 focused tests、一份 runner 文件及本卡 evidence；所有文章與共享發布檔唯讀。
驗收證據｜失敗重現、假說驗證、prompt/gate parity、單篇 request、strict schema、partial manifest、resume、4/4 canary Writer／Reviewer receipts、測試與完整 candidate commit。

## 固定失敗證據

- 舊文阻塞 evidence commit：`af9e333fcd64714b310abdd327af136a1af34925`。
  - runtime inventory 352。
  - Gemini Reviewer 71/71 batch 成功。
  - Writer 50/55 batch 成功；5 batch 在 initial + retry-01 + retry-02 後仍 `JSONDecodeError`。
  - 250 篇部分候選因全量契約而未進 candidate Reviewer／apply。
- 新文阻塞 evidence commit：`c5b78c706bbe2586b4fbbd0591e0c8f6ccfc93b6`。
  - 30 篇、6 batch、每批 5 篇。
  - attempt 03 findings：`description_boundary=30`、`banned_phrase=6`、`paragraph_length=5`、`description_length=3`、`title_length=3`，以及少量 body／keyword finding。
  - 第 3 次 `JSONDecodeError` 後停止；0/30 達成 `Reviewer APPROVE + deterministic findings=0`。
- 以上 commit 只作唯讀 root-cause evidence；不得 cherry-pick 其內容草稿或延續原 attempt。

## 可證偽假說

1. `H1_RESPONSE_SIZE`：多篇長文共用一個外部 JSON response 造成截斷或非完整 JSON。若改為每個 Writer request 精確 1 篇，4 篇 canary 應為 4/4 strict JSON 可解析。
2. `H2_PROMPT_GATE_DRIFT`：Writer／repair prompt 沒有完整表達 deterministic publication gate。若由同一 contract source 產生 prompt 規則與正反例，canary 的 `description_boundary` 應為 0，其他列明 gate 亦不得靠 Reviewer 才首次發現。
3. `H3_FAILURE_AMPLIFICATION`：batch 級 aggregate 與全有全無 manifest 讓單篇失敗污染已成功文章。若改為逐篇 SHA／receipt／status 再 deterministic aggregate，失敗 fixture 應只標記該 identity，已核准 identity 保持 resumable。

不得假設 JSON error 是 Markdown fence、stderr、網路或認證問題；現有 runner 沒保存 invalid raw response，沒有證據前禁止加入寬鬆 JSON 猜測修復器。

## Frontier 與垂直切片

### Slice A｜Red-capable seam

- 先新增 public-behavior tests，重現：五篇 create brief 產生多篇 response schema、prompt 缺 description boundary 明確正反例、單篇 schema failure 阻塞整個 aggregate。
- 至少執行一次會紅的 focused pytest，保存 red command、失敗 assertion 與 baseline。

### Slice B｜Publication contract parity

- 建立單一 deterministic contract source，至少涵蓋：description 必須自帶限制語、title／description 長度、title／opening keyword、禁詞、段落長度、正文長度與 generic AI phrase。
- Writer 初稿與 repair prompt 都必須引用相同 contract，提供最小繁中正例／反例；不得讓 prompt 規格與 gate 分別硬編碼後再次漂移。
- 測試只驗 public prompt／gate observable parity，不鎖 private implementation。

### Slice C｜Single-article external generation

- 新文 create 與本卡涉及的 rewrite 外部 Writer request 每次只允許一篇；Reviewer 仍可在本地聚合後獨立審核，但每篇 candidate／receipt／SHA 必須可單獨追蹤。
- 若現有 rewrite path 已具單篇隔離，應重用而非另造第二套流程。
- strict JSON schema 不得放寬；不得用 regex、括號補齊、移除任意 prose 等方式猜修模型內容。

### Checkpoint 1

- Slice A red tests 轉綠。
- 單篇 request schema、prompt/gate parity、舊 public interface compatibility 通過。

### Slice D｜Failure isolation and resume

- aggregate manifest 必須逐篇記錄 `APPROVED / BLOCKED / PENDING`、request SHA、candidate SHA、Reviewer SHA 與 finding codes。
- 一篇 parse/schema failure 不得改寫其他文章狀態；resume 只為失敗 identity 建立新 run identity，成功 identity 不重送。
- 仍保留每 identity 最多兩輪 repair、同一 identity 同 blocker 三次即停；不得建立 attempt 04。
- 卡片可以交付 partial candidate manifest，但只有 `APPROVED + findings=0` 的文章可進主線 review；BLOCKED 不得 apply。

### Slice E｜Four-article Gemini canary

- 使用四個產品 cluster 各一篇、全新 canary run identity；每次 Writer request 一篇，Reviewer 為 fresh Pro Low process。
- canary 只保存公開 sanitized brief、SHA receipts、candidate／review verdict 與 deterministic findings；不得寫入 `app/**`。
- 成功標準：4/4 Writer strict JSON、4/4 schema hydrate、`description_boundary=0`、無 attempt 04、每篇狀態獨立；最終 Reviewer 若因文章品質 REJECT 可保留 finding，但不得因已修契約欄位或 JSON 格式失敗。
- 任一 canary `JSONDecodeError` 即停止外部 canary，不做盲目重送；保存 red evidence 並回 `BLOCKED`。

### Checkpoint 2

- focused tests、既有 pipeline tests、outbox tests、必要 web tests、`git diff --check`、allowlist、敏感字串掃描。
- 若 canary 未達契約成功標準，不得宣稱修復完成。

## 必交付

- 修復後 pipeline／runner 與 public-behavior regression tests。
- `root-cause.md`：三個假說的 verified／falsified 結論與 evidence mapping。
- `red-green.txt`：實際執行的 red-capable command、初始 failure 與修復後結果。
- `contract-parity.json`：publication codes、prompt coverage、正反例 coverage 與 gate mapping。
- `canary-manifest.json`：四篇逐篇 request／candidate／review SHA、findings、attempts 與 status。
- `verification.txt`：focused/full tests、allowlist、`git diff --check`、`[DBG-` 清除檢查與 remaining risk。
- 更新 `docs/pantheon_gemini_outbox_runner.md`，說明單篇外部生成、逐篇 resume、partial manifest 與不自動 apply 邊界。

## 禁止範圍

- 不修改 `app/**`、文章、registry、metadata、prerender、sitemap、feed、redirects 或部署設定。
- 不修改或重試原 BLOCKED run；所有 canary 必須是新 identity。
- 不安裝、不登入、不修改 Gemini CLI、OAuth、token store、MCP config 或全域 ai-core。
- 不實作寬鬆 JSON 猜測修復器，不保存 invalid raw response、CLI stderr 或秘密。
- 不 push、不 deploy、不 publish；不啟動舊文 352 篇或新文 30 篇正式 rerun。

## 驗收與交付

- 已跑過可重現本次失敗的 red-capable test，且相同 seam 修復後轉綠。
- publication prompt 與 deterministic gate 同源或有可程式驗證的完整 parity；`description_boundary` 必須有繁中正反例。
- Writer 外部 request 每次精確 1 篇；逐篇 failure isolation／resume／partial manifest 有測試。
- 4 篇 canary 達成卡片 success criteria，且所有外部結果有 SHA-bound receipts；否則終態 `BLOCKED`。
- 執行受影響 focused/full pytest、`git diff --check`、changed-file allowlist 與敏感字串掃描。
- 建立 candidate commit 並回報完整 SHA；只能宣稱 `DELIVERED_CANDIDATE` 或 `BLOCKED`，不得宣稱已整合、已恢復大量產文、已部署或已上線。
- 同一 blocker 失敗三次立即停止，不做第四次嘗試。

## Gate 狀態

- Gate 1：實體卡已建立並提交於來源 commit `569b46e010cf8d2ffccfab55496077d5efbac9d4`。
- Gate 2：正式 thread `019f7fb1-60b5-7183-bd55-99eaeb503107` 可查，標題為「Gemini 產文契約修復｜正確來源」，cwd 為獨立 worktree `<codex-worktree>/e2d42265-1097-4341-b030-8eba32c67993/Pantheon`，HEAD 精確為 `5ee072be12ea430daeb2a9c4ee1e7dcb5214b7a5`、卡片可讀、worktree clean，首回合狀態 `inProgress`。
- Previous provisioning：thread `019f7faf-6973-7633-ab36-1a66ff6a9aa3` 從過舊 `ddcb4ef` 建立且缺卡，已要求停止並標記 `BLOCKED / PROVISIONING_PREFLIGHT`；不得收取其任何成果。
- Gate 3–5：尚未開始，禁止預填通過。
