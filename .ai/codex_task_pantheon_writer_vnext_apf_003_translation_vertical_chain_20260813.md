---
id: APF-003
title: 建立 Writer vNext 自動翻譯垂直鏈
status: ready
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: implementation
cycle: 1
thickness: standard
risk: medium
model: gpt-5.6-terra
reasoning: medium
model_reason: 既有 i18n 與 Publisher seam 已存在；本卡只補 APF-002 handoff 與可驗證的雙 lane 自動鏈
parent_candidate: 6f0513df50698f1456d44d7b4644ee3e76e54862
traces_to:
  - US-001
  - US-004
  - FR-012
---

# APF-003｜自動翻譯垂直鏈

## 任務五行卡

- 目標：把 APF-002 的 new／rewrite 完成輸出自動送入既有 i18n-new／i18n-rewrite，完成翻譯、Reviewer、legacy-compatible Publisher dry-run handoff。
- 可改：coordinator、既有 multilingual adapter、對應測試、專屬文件與 receipt；只做最小垂直鏈。
- 禁止：不得正式發布、push、deploy、排程、修改 Publisher production code、V9、SEO／GEO 或內容策略。
- 驗收：new／rewrite 各一篇、各一個固定 locale；source SHA、translation SHA、locale／review／publication identity 一致；retry／resume 不重複。
- 證據：原子候選 commit、真實 multilingual validator／Reviewer／Publisher collector、負向漂移、完整受影響回歸、git diff --check、clean。

## 唯一 Frontier

APF-001 與 APF-002 已整合。缺口只有：APF-002 的兩個完成輸出尚未自動形成可被 Existing Publisher 接受的 translation runs。

## 實作契約

1. source decision 前以 CodeGraph 定位並以原始碼確認：
   - scripts/agy_multilingual_pipeline.py 的 prepare／enqueue、translation_run_id、brief／candidate validator。
   - scripts/agy_content_publisher.py 的 collect_ready_translation_runs side-effect-free seam。
   - 現有 translation Reviewer 與 review SHA／identity 契約。
2. 不得新增自我通過 validator；測試必須走既有 multilingual validator、pipeline.validate_review 與 Publisher translation collector。
3. 以 APF-002 campaign result 為輸入，new 與 rewrite 各產生一個固定 locale translation run。locale 先用單一低成本 fixture；不得擴大全 locale。
4. 保留並重新核對 source run ID、source article ID、source SHA、translation run ID、locale、translation SHA、review identity。
5. translation publication identity 必須與原文 identity 可追溯但不得混淆；new／rewrite lane 也不得互換。
6. retry／resume 使用 deterministic translation_run_id；相同 source SHA 不重複建立，source SHA 改變必須 fail closed 或形成明確新版本，不得覆蓋舊 run。
7. 所有 lane 全量 preflight 後才寫入；任一 identity／SHA／review／locale 漂移時 queue 與 translation handoff 零寫入。
8. Publisher 僅呼叫 collect_ready_translation_runs 或等價 side-effect-free seam；published 維持 0，ledger／文章／registry／tag／commit／push 不得 mutation。
9. 不得改自動選題、原文 Writer／Reviewer 行為或正式 Publisher authority。

## Allowlist

- scripts/agy_gemini_coordinator.py
- scripts/agy_multilingual_pipeline.py
- tests/test_agy_gemini_coordinator.py
- tests/test_agy_multilingual_pipeline.py
- docs/pantheon_writer_vnext_auto_vertical_chain.md
- artifacts/fortune_council/content_writer_vnext_execution/apf_003/**

若必須修改 scripts/agy_content_publisher.py 或清單外 production code，停止並回報 scope change。

## 驗證

1. GREEN：new／rewrite translation runs 經真實 multilingual validation、clean Reviewer 與 Existing Publisher translation collector 接受。
2. 負向：source SHA、translation SHA、locale、source／translation article identity 或 review identity 漂移，全部 fail closed 且零寫入。
3. retry／resume：相同輸入重跑不新增 duplicate run；兩 lane run ID 唯一且 deterministic。
4. 無副作用：Publisher state、publication ledger、文章 tree、registry、tag、commit、push 均不變；只允許測試 tmp queue／handoff fixture。
5. uv run pytest tests/test_agy_gemini_coordinator.py tests/test_agy_multilingual_pipeline.py tests/test_agy_content_publisher.py -q，或更精確且完整涵蓋 seam 的集合。
6. git diff --check；worktree clean。

## 交付

- 回報 candidate SHA、changed paths、translation／Publisher seam、pass 數、receipt 路徑。
- 明示未 push、deploy、publish、tag、production activation。
- 同一 blocker 第三次失敗即停，不做第四次。
