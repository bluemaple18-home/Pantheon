---
id: APF-002-REPAIR-001
title: 修正 Writer vNext 垂直鏈自動入口與真實相容驗證
status: ready
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: repair
cycle: 1
thickness: standard
risk: medium
model: gpt-5.6-terra
reasoning: medium
model_reason: 兩個固定 P1 的 bounded Repair；無 production mutation 或架構 fork
parent_candidate: 0386576ab87b7c5cd3139ef3713dda5f8cb7ae07
traces_to:
  - US-001
  - US-002
  - US-003
  - FR-001
  - FR-002
  - FR-012
---

# APF-002 Repair-001｜修正自動入口與真實相容驗證

## 任務五行卡

- 目標：只修 `APF002-VERTICAL-001`、`APF002-COMPAT-002`，讓 new／rewrite 兩條 fixture 真正自動跑到 Existing Publisher side-effect-free boundary。
- 可改：APF-002 原候選五個檔案與其直接測試；必要時新增 APF-002 專屬 fixture／receipt。
- 禁止：不新增功能，不碰 i18n、Publisher mutation、排程、production、V9、SEO／GEO、Blind Reader。
- 驗收：workset 批次入口無人工逐項觸發；new 與 rewrite 成功 fixture 均使用真實 validator；retry 不保存未驗證 stage。
- 證據：原子 repair commit、固定 P1 regression tests、受影響測試、`git diff --check`、clean worktree。

## 固定 Findings

### APF002-VERTICAL-001｜沒有自動 orchestration 入口（P1）

- 證據：`scripts/agy_gemini_coordinator.py:1948` 只新增單項 callable；repo 內呼叫者只有測試。
- 風險：APF-001 workset 無法在一次 deterministic action 中自動推進 new／rewrite，仍需人工逐篇組裝 `work_item`、`run_dir` 與 callbacks，違反 APF-002「不需人工逐篇觸發」。
- 修正：提供 bounded、deterministic、side-effect-free 的 workset execution seam，從 APF-001 workset 選取 new／rewrite 並自動執行；明示輸入／輸出、上限、identity 與 fail-closed。不得建立第二套 queue／scheduler。

### APF002-COMPAT-002｜相容驗證被 mock，rewrite 沒有成功證據（P1）

- 證據：`tests/test_agy_gemini_coordinator.py:41-83` mock `validate_candidate`、`validate_review`、`validate_manifest`；成功案例只有 `new`，`rewrite` 只驗 REJECT。
- 風險：現有測試無法證明真實 candidate／review／manifest contract 可通過，也未重放 Existing Publisher 的 side-effect-free acceptance boundary。
- 修正：建立有效的 `new` 與 `rewrite` 成功 fixture；核心成功測試不得 mock candidate／review／manifest validator，並須實際重放現行 Publisher side-effect-free validation seam。保留 reviewer blocking 負向測試。

## Repair regression

1. 一次 batch/workset 呼叫自動處理一個 new 與一個 rewrite；callbacks 可注入固定模型回應，但不得由測試逐項呼叫單項 helper。
2. new／rewrite 均產生 valid ArticleBriefV2、candidate、clean APPROVE review、EditorialManifestV1。
3. 真實 `pipeline.validate_candidate`、`pipeline.validate_review`、`editorial_contracts.validate_manifest` 全數執行。
4. Existing Publisher 的 dry-run／side-effect-free acceptance boundary 接受兩個完成 run；不得 monkeypatch 掉其核心判斷。
5. Writer 或 Reviewer 產生無效 artifact 時，先驗證再持久化；重跑仍可重新執行失敗 stage，不需人工刪檔。
6. 已驗證成功 stage 重跑不重送，identity／SHA 穩定。
7. 既有 `250` 個受影響測試與新增 regression 全部通過；`git diff --check` 通過。

## Allowlist

- `scripts/agy_gemini_coordinator.py`
- `scripts/agy_editorial_contracts.py`
- `tests/test_agy_gemini_coordinator.py`
- `docs/pantheon_writer_vnext_auto_vertical_chain.md`
- `artifacts/fortune_council/content_writer_vnext_execution/apf_002/**`

若真正 side-effect-free fixture 必須修改清單外的測試 helper，先停止回報；不得修改 `scripts/agy_content_publisher.py` production code。

## 交付

- 回報 repair commit SHA、changed files、finding→test 對照、pass 數、receipt 路徑。
- 明示未 push、未 deploy、未 publish、未啟動 production。
- 同一 blocker 第三次失敗即停，不做第四次。
