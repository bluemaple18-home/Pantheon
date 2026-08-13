---
id: CHECKPOINT-A
title: 驗證 Writer vNext 私有自動 E2E
status: ready
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: implementation
cycle: 1
thickness: standard
risk: medium
model: gpt-5.6-terra
reasoning: medium
model_reason: APF-001 至 APF-003 seam 已固定；本卡只組合既有能力並補私有 E2E 與失敗復原證據
parent_candidate: 439585392cdae0e3ef3f6b53ea157ce18e704d7b
traces_to:
  - US-001
  - US-002
  - US-004
  - FR-012
  - SC-001
---

# CHECKPOINT-A｜Writer vNext 私有自動 E2E

## 任務五行卡

- 目標：把 APF-001 source campaign、APF-002 new／rewrite editorial chain、APF-003 單一 locale translation chain 串成一次全自動私有 E2E。
- 可改：coordinator 最小組合 seam、對應測試、專屬文件與 receipt；優先重用既有函式，不建立第二套 queue／Publisher。
- 禁止：不得正式發布、push、deploy、排程、改 Publisher production code、改內容策略、啟動 V9 或 SEO／GEO。
- 驗收：new 1、rewrite 1、各 ja 1；retry、resume、duplicate suppression、rollback 與容量上限皆有 deterministic 證據。
- 證據：原子 candidate commit、完整 affected suite、零發布／零 ledger mutation、git diff --check、clean worktree。

## 唯一 Frontier

APF-001、APF-002、APF-003 已整合 local `main`。APF-004 被本 checkpoint 阻擋；本卡只證明 private E2E，不提供 production authority。

## 實作契約

1. source decision 前以 CodeGraph 定位並以原始碼確認 APF-001～003 public seams 與 Existing Publisher collectors。
2. 使用 deterministic fixture 自動建立含一個 new 與一個 rewrite 的 campaign；不得人工逐篇呼叫作為驗收路徑。
3. 自動完成兩個原文 Writer／Reviewer／legacy handoff，再各完成一個 `ja` translation Writer／Reviewer／translation collector handoff。
4. Publisher 只允許 side-effect-free collector／dry-run；結果固定 `published=0`，不得變更文章 tree、registry、ledger、tag、commit、push 或 deployment state。
5. 相同輸入重跑必須 byte-stable 或 contract-stable，不新增 run、translation、Writer／Reviewer call 或 queue state。
6. resume 必須從可辨識的中斷狀態續接；已完成 lane 不重做，未完成 lane 可安全完成，identity 與 SHA 不漂移。
7. duplicate work item、duplicate run ID、publication identity 混淆或 source／candidate／review SHA 漂移必須在任何新 queue／handoff 寫入前 fail closed。
8. rollback 驗證使用專屬 tmp sandbox 或 transaction snapshot；注入第二 lane／translation 階段失敗後，不得留下半套可被 Publisher 收集的完成結果。
9. capacity 固定上限為本 fixture：最多 2 個 source work items、2 個 editorial runs、2 個 `ja` translation runs；超量必須在 Writer／Reviewer 與 Publisher collector 前拒絕。
10. 若既有 seam 無法安全滿足 rollback／resume，只能補最小 coordinator adapter；不得修改 `scripts/agy_content_publisher.py`。

## Allowlist

- scripts/agy_gemini_coordinator.py
- tests/test_agy_gemini_coordinator.py
- docs/pantheon_writer_vnext_auto_vertical_chain.md
- artifacts/fortune_council/content_writer_vnext_execution/checkpoint_a/**

若需要修改 Publisher、multilingual production code、scheduler、installer 或其他清單外 production code，停止並回報 scope change。

## 驗證

1. GREEN：單一入口完整產生 `new + rewrite + i18n-new-ja + i18n-rewrite-ja` 四 lane dry-run receipt。
2. retry／resume／duplicate suppression：相同輸入與中斷重跑無 duplicate、無已完成工作重做。
3. rollback：注入第二 lane 或 translation failure，正式 tmp queue／handoff 無半套 complete result，Publisher 收集為空。
4. capacity：第 3 個 source／editorial／translation work 被 preflight 拒絕，零 Writer／Reviewer／Publisher call。
5. 無副作用：repo HEAD、working tree、文章 tree、registry、Publisher state／ledger、tag 均不變。
6. `uv run pytest tests/test_agy_gemini_coordinator.py tests/test_agy_multilingual_pipeline.py tests/test_agy_content_publisher.py -q`。
7. `git diff --check`；worktree clean。

## 交付

- 回報 candidate SHA、changed paths、E2E 單一入口、四 lane receipt、pass 數與 receipt 路徑。
- 明示未 publish、tag、push、deploy、schedule、production activation。
- 只交付 `DELIVERED_CANDIDATE`；主線 review／acceptance 後才能標記 CHECKPOINT-A PASS。
