---
id: APF-002
title: Writer vNext 新文／重寫垂直鏈
status: ready
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: implementation
cycle: 1
traces_to:
  - US-001
  - US-002
  - US-003
  - FR-001
  - FR-002
  - FR-012
depends_on:
  - APF-001@aa2ae63fda9ab9dd79d5cac62d9402cfada94238
thickness: standard
risk: medium
model: gpt-5.6-terra
reasoning: medium
model_reason: 邊界固定的跨檔垂直鏈實作；不含 production mutation 或未解架構 fork
---

# APF-002｜Writer vNext 新文／重寫垂直鏈

## 任務五行卡

- 目標：讓 APF-001 workset 中一個 `new` 與一個 `rewrite` fixture，自動完成 `brief → draft → review → legacy-compatible candidate`。
- 可改：既有 coordinator／editorial contracts／writer-reviewer pipeline 與對應測試；新增 APF-002 專屬文件及證據。
- 禁止：不得建立第二套 queue、scheduler、lock、approval 或 Publisher；不得碰 i18n、production、deploy、push、V9、SEO／GEO、Blind Reader 擴建。
- 驗收：無人工逐篇觸發；Reader Question／Thesis／identity 可追溯；Existing Publisher 的 side-effect-free validation 接受；legacy path 不回歸。
- 證據：原子 commit、測試輸出、dry-run fixture receipt、`git diff --check`；worktree 保持乾淨。

## 已知基線

- source commit 必須包含 APF-001 integrated main：`aa2ae63fda9ab9dd79d5cac62d9402cfada94238`。
- APF-001 已提供 versioned campaign workset、來源 identity、locale 與 campaign version；不得重新建立來源 owner。
- Writer vNext 正式規格：`docs/pantheon_writer_vnext_spec.md`。
- APF-001 contract：`docs/pantheon_writer_vnext_auto_source_campaign_contract.md`。
- Existing Publisher 保持唯一 publication owner；本卡只到 side-effect-free compatibility boundary。
- production runtime、Publisher mutation、外部發文與排程均未授權。

## 實作契約

1. 以 deterministic orchestration 消費 APF-001 work item；測試 fixture 可注入固定 Writer／Reviewer response，不得靠人工逐篇下命令完成狀態搬運。
2. `new` 與 `rewrite` 各完成一條垂直路徑，保留 `work_id`、article identity、source kind、locale、campaign version 與 run identity。
3. 撰稿前產生並驗證 versioned `ArticleBrief`；至少保留 reader question、target reader、search intent、thesis、reader outcome、scope、anti-goals、evidence policy 與 risk class。
4. Content Plan 僅在 manifest 選用時存在；不得加入固定節數、固定段數、固定字數、強制 introduction／FAQ／conclusion。
5. Writer 與 Reviewer 的完成狀態必須可 retry／resume；已成功 stage 不得因重跑重送或重建不同 identity。
6. 最終輸出透過既有 compatibility contract 形成 legacy candidate／review，並實際呼叫現行 side-effect-free validator；不得複製一份只在 vNext 內自我通過的 schema。
7. 新 editorial artifacts 旁掛於 run；不得修改 Publisher authority、publication transaction 或 production queue。
8. schema、identity、SHA、非法 transition 或 reviewer blocking finding 失敗時 fail closed，保留可判讀錯誤。

## 可改範圍

- `scripts/agy_gemini_coordinator.py`
- `scripts/agy_editorial_contracts.py`
- `scripts/agy_seo_copy_pipeline.py`（僅既有 writer／reviewer seam 的最小必要改動）
- 上述檔案的直接測試
- `docs/pantheon_writer_vnext_auto_vertical_chain.md`
- `artifacts/fortune_council/content_writer_vnext_execution/apf_002/**`

若需修改清單外的 production/runtime 檔案，立即停止並回報 scope change，不得自行擴張。

## 明確禁區

- `scripts/agy_content_publisher.py` 的 mutation／transaction／git／deploy 邏輯
- `scripts/agy_multilingual_pipeline.py` 與任何 i18n lane
- queue 清空、批次重送、排程、LaunchAgent、production activation
- V9 barrier／installer、Blind Reader、Claims 深度驗證、Humanizer、SEO／AEO／GEO
- 修改 registry、sitemap、feed、redirects 或正式文章內容
- push、deploy、tag、release、外部服務 mutation

## TDD 與驗收

先寫 public-behavior 回歸測試，再做最小實作。至少證明：

1. `new` fixture：workset item → valid brief → writer candidate → reviewer acceptance → legacy-compatible candidate／review。
2. `rewrite` fixture：同一路徑且保留 rewrite campaign version 與原 article identity。
3. retry／resume：已完成 stage 不重送；重跑輸出 identity 與 SHA 穩定。
4. fail-closed：缺 brief 欄位、identity 漂移、SHA 不符或 reviewer blocking finding 不得產生 compatible result。
5. Content Plan 未選用時不因缺 artifact 失敗；選用時允許任意 sections 長度。
6. 現行 Publisher side-effect-free validator 接受兩個 fixture；沒有 publication side effect。
7. 既有 coordinator、editorial contracts、SEO copy pipeline 相關測試全部通過。
8. `git diff --check` 通過，worktree clean。

## 交付格式

- 回報候選 commit SHA 與變更檔清單。
- 回報驗證指令、pass 數與 APF-002 receipt 路徑。
- 明示未 push、未 deploy、未發布、未啟動 production。
- 若同一 blocker 連續三次失敗，停止，不做第四次。
