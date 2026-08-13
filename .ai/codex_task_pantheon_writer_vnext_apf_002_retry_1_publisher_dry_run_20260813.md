---
id: APF-002-RETRY-1
title: 補齊 Existing Publisher 真實 dry-run 相容證據
status: ready
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: implementation
cycle: 2
thickness: standard
risk: medium
model: gpt-5.6-terra
reasoning: medium
model_reason: 單一固定 Publisher side-effect-free acceptance 缺口；無 production mutation 或架構 fork
supersedes: APF-002-REPAIR-001
parent_candidate: da1ee675cd3d996906cbce00c740c3c09eefd074
traces_to:
  - US-004
  - FR-012
  - SC-006
---

# APF-002 Retry-1｜Existing Publisher 真實 dry-run

## 任務五行卡

- 目標：讓 APF-002 的 new／rewrite 完成輸出實際重放 Existing Publisher side-effect-free acceptance seam。
- 可改：APF-002 coordinator／測試／專屬文件與 receipt；只做相容 handoff 最小必要變更。
- 禁止：不得修改 Publisher production code、不得發布、push、deploy、排程、i18n、V9、SEO／GEO。
- 驗收：new／rewrite 皆被現行 Publisher validator／collector 接受；identity／candidate SHA／review SHA 一致；dry-run 無 publication mutation。
- 證據：原子候選 commit、真實 seam 測試、受影響回歸、`git diff --check`、clean worktree。

## 唯一 Frontier

`APF002-COMPAT-002` 尚未關閉。候選 `da1ee675cd3d996906cbce00c740c3c09eefd074` 已有：

- APF-001 workset → bounded new／rewrite 自動入口。
- 真實 `validate_candidate`、`validate_review`、`validate_manifest`。
- invalid candidate 驗證前不落盤；成功 stage 可 resume。

缺口：尚未把兩條完成輸出轉成 Existing Publisher 現行 queue/run contract，並實際呼叫其 side-effect-free acceptance seam。

## 實作契約

1. 先以 CodeGraph 找 `agy_content_publisher.py` 的 `collect_ready_runs`、rewrite collector、`publish_ready_runs(..., dry_run=True)` 或等價公開 side-effect-free seam；以原始碼確認最小正式入口。
2. 不得新增自我通過 validator。測試必須呼叫現行 Publisher code。
3. 若需要 handoff adapter，只能把已驗證的 APF-002 candidate／review 映射成現行 run／queue contract；不得擴大 Publisher schema 或 authority。
4. new 與 rewrite 各有一個成功 fixture；兩者均保留 campaign work ID、run ID、article identity、candidate SHA、review SHA。
5. Publisher acceptance 必須重新核對 candidate／review 與 clean approval；任何 identity／SHA／review drift fail closed。
6. dry-run 前後比對 repo、queue、publisher state 的 publication-sensitive 檔案；不得新增 ledger publication、approval、文章、registry、tag、commit 或 push。
7. 不得 mock `pipeline.validate_candidate`、`pipeline.validate_review`、`editorial_contracts.validate_manifest`，也不得 mock Publisher 的核心 acceptance／collector 判斷。可注入固定 git HEAD 查詢以避免外部 mutation，但需明示。
8. 不得再改 APF-002 自動選取策略、Writer／Reviewer 行為或新增 editorial stage。

## Allowlist

- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`
- `docs/pantheon_writer_vnext_auto_vertical_chain.md`
- `artifacts/fortune_council/content_writer_vnext_execution/apf_002/**`

若必須修改 `scripts/agy_content_publisher.py` 或清單外 production code，停止並回報 scope change。

## 驗證

1. RED：現有 APF-002 完成輸出尚無法被 Publisher collector／dry-run seam 接受。
2. GREEN：new 與 rewrite 真實 fixture 均被接受，回傳可識別 run ID；published count 維持 0。
3. 負向：candidate SHA、review SHA 或 identity 任一漂移 → Publisher seam 拒絕。
4. 無副作用：dry-run 前後 publication-sensitive tree／queue／state digest 不變，允許純測試 tmp fixture 建立。
5. `uv run pytest tests/test_agy_gemini_coordinator.py tests/test_agy_editorial_contracts.py tests/test_agy_content_publisher.py -q`，或更精確且完整涵蓋 seam 的受影響集合。
6. `git diff --check`；worktree clean。

## 交付

- 回報完整候選 SHA、changed files、Publisher seam 名稱、pass 數、receipt 路徑。
- 明示未 push、未 deploy、未 publish、未啟動 production。
- 同一 blocker 第三次失敗即停，不做第四次。
