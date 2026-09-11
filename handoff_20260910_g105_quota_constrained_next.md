# Pantheon 整合換手：Flash 已耗盡；四線未驗收，先離線定位

## 1. 最新 Owner 要求與目標
- 最新要求：「不夠用。你現在也沒辦法拿 flash 來測，因為都打光了。所以再整合一次。換手卡我要拿去新的對話了。」
- 目標仍是保留既有機制，以足夠日常用量的模型恢復四線：中文新文、中文重寫、多語新文、多語重寫。最終須 Writer → Reviewer → publish → 公開 HTTP 200 且正文可見、符合核准稿。
- 不是重做流程、放寬 validator，亦不是不計配額把工作送回 Flash。優先既有參數／接點的最小修正，但不得把實際程式改動說成只有改參數。
- 本轮只整理文件，不呼叫 provider、不改 code/config/prompt/模型/排程、不重試、不部署、不 push、不新派工。舊卡歷史授權不等於新授權。
- 新對話先依本卡接續唯讀／離線診斷；本卡不是修復、API 測試或正式變更授權。Repair2 已用，不得換卡名重置或另開 Repair3。

## 2. 必須修正的決策：Flash 不能當目前測試前提或日常解法
- Owner 明確表示 Flash 額度已打光，每日 20 次不足日常發文；本輪沒有重新查詢 provider 配額。
- 撤回「下一步直接拿 Flash 重跑 en/ja/ko」；目前不可執行，也不得用反覆試打來確認耗盡。
- 「Planning 用 Flash、正文用 Lite」僅是先前候選，現因容量不符需求，不是已選方案。不能把等 Flash 重置當唯一推進方向。
- 本地 admission cap=1200 不會提高供應商配額；Owner 先前表示三把各 500 次，不等於已驗證所有 key／模型額度可相加或彼此獨立。
- Owner 曾提出 5.3 Spark 備援並提供剩餘 100% 截圖：那是當時畫面，不是目前用量或已接通證據。不能直接把 Codex 額度當成 Gemini API 可替換通道。尚未切 Spark，亦未證明既有 runner 支援它。

## 3. 根問題、目前判斷與證據分級
根問題：以前成功的多語 planning，換模後為何違反 fact identity／coverage／語言契約？如何在現有可用配額下最小恢復，而不引入另一套機制？

### 本對話此前已核對的紀錄
- 今天三語取得回應後，於 planning/schema 驗證失敗；不是此前 HTTP 400 階段，也未走到獨立 Reviewer／Publisher。
- en 非法 enum fact ID；ja 重複 fact ID；ko coverage note 混中文。原始回應確實有違約證據，但不能因此單獨證明是哪個改動造成。
- g103 → g105 另改 runner 來源選取／投影；不能把整段期間當成「唯一變因只有模型」。

### Owner 最新帶入的查核結果（本輪未獨立重查原始檔）
- i18n-rewrite 最後成功基線：v0.3.387，2026-09-09 20:28，planner gemini-3.5-flash，PLANNING PASS。
- i18n-new v0.3.389：2026-09-10 09:19，亦為 gemini-3.5-flash。
- bf174cf850 於 09-10 13:44 將 Writer Flash → Flash Lite，並調整 coordinator 的 pending job 改送 Lite 邏輯；沒有修改 agy_multilingual_pipeline.py。
- 其後目前未找到新多語成功發布；19:54～20:00 三語失敗皆使用 gemini-3.5-flash-lite。
- 三語 archived request schema 各有相同的 41 個合法 source_fact_id，全部唯一。
- 更早外部查核提到 19cbd850cb 曾把預設 Writer Lite → Flash；不要把它和 bf174cf850 的反向切換混為一筆。

### 整合判斷（不是已確診）
- 換模後 structured planning 契約遵循下降，升為第一嫌疑；來源接線／轉換仍未排除。不把嫌疑排序冒充根因結論。
- schema 41 IDs 唯一，降低「白名單本身重複」嫌疑；尚不等於 prompt facts、schema 與 hydration/validator expected_facts 三處一致。
- runner source projection 是否真正改變模型輸入，仍須沿呼叫鏈確認，不能只因程式有改就斷言 prompt 已變。
- validator 目前有抓到真實違約；不放寬它。ko 錯誤索引須按 fact ID 追蹤，不能拿原始陣列位置直接對照。
- 即使未來有單次 Flash PASS／Lite FAIL，也只是支持模型差異，不是排除隨機性及所有干擾因素的證明。

## 4. 正式 runtime 基線（歷史快照，不是本輪即時狀態）
- 最後核對：2026-09-10 20:14:48 +08:00；正常排程可能已繼續產出，勿將快照說成現在。
- runtime：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8`；actor=`actor/`、queue=`queue/`、ledger=`state/ledger.json`。
- actor HEAD：`5d1a603b46fed15b8ba8ecaaf673923e0ac8285a`，當時乾淨；parent=`25ab1a40c9f9a3fed35bc5e4cac59d4939159bba`。
- generation=`g105-5d1a603b46-published-source-20260910`；manifest digest=`fea34bd838004b93ce1331907045370bb70ab92e229478039afd4d4aca15dcf0`。
- Writer=gemini-3.5-flash-lite；Reviewer=gemini-3.1-flash-lite；shared daily admission cap=1200。
- coordinator／四 lane／publisher 間隔 60 秒，capacity guard 300 秒；七服務當時 launchctl print rc0，只代表已載入。
- 中文 new ledger 最新 v0.3.401，run=`auto-new-v1-20260910-048-01`，19:25:23。
- 中文 rewrite ledger 最新 v0.3.403，run=`legacy-auto-sweep-v1-astrology-0033-astro-expansion-50d-0033`，20:13:41；尚未完成該筆公開正文驗收。
- translation ledger 12 筆，最後 v0.3.389，ko，run=`auto-i18n-ko-f27547593f9ad93030fb-replacement-01`，09:19:28。
- 兩 i18n 線本輪未通過端到端驗收，不能宣稱四線完成。代理停止操作不代表停掉自動排程。

## 5. 三筆失敗的可追溯入口
共同來源：ASTRO-EXPANSION-50D-0035；lane=i18n-rewrite。

| 語言 | run | job | 拒絕點 |
| --- | --- | --- | --- |
| en | auto-i18n-en-4537d2fa89dc2d1c5bed | bd4f213b95760f031dd7dd4912c6d29b26adc7e1 | SCHEMA_INVALID_PAYLOAD；coverage_mapping[24].source_fact_id enum 不符 |
| ja | auto-i18n-ja-5653a1887f273669a763 | 4c78066b422715ee255f413d871cbf63c998afad | source fact coverage differs；重複 fact-7a89fd04868e716f3631773c |
| ko | auto-i18n-ko-dceee8434dba1346871d | 1b994bd23bece66be64a0688b9b0d658cbd6ef70 | native locale language differs，coverage_note[5] |

- runtime 下：`queue/translation-runs/<run>/brief.json`、`attempts/01/planning-result.json`、`external-plan.json`、`plan-operation.json`；`queue/lanes/i18n-rewrite/{failed,inbox}/<job>.json`。
- en 可能沒有 external-plan；不能因此說它還沒到 schema，已有明確 SCHEMA_MISMATCH 診斷。
- ko 原始 mapping[5] 是韓文，但 raw 15／28–32／36／39 有中文標題或標籤。需重建正式重排後 fact ID 對應，不能因 raw[5] 合格便判 validator 誤擋。

## 6. 已改多少、已驗證什麼
- 25ab → 5d1a：runner +187/-5；tests/test_agy_source_authority_contract.py +327/-0；tests/test_translation_dispatch_authority.py +52/-13；合計三檔 +566/-18，其餘 tracked tree 相同。不含更早換模／cap 改動。
- 此 delta 未改多語 planner、語言 validator、prompt、模型路由、allocator/coordinator；runner 修已發布來源固定、publisher 證據／投影及原生 registered translation 相容性。
- 本地 operation helper 另有候選、generation、交易／備份路徑參數調整；完整歷程見舊卡與 execution receipt。
- 歷史驗證：產品 126 PASS；操作 31 PASS；review GO；promotion/stage/activate/七服務 receipt 通過。這些不等於四線發文完成。
- publisher dry-run 曾透過既有 selector 記錄 quarantine，並非零寫入；publisher 與 25ab 同 blob a397dd98e850049dddba1752c5a3abca84997d85。未清 ledger、failed runs 或 allocator。

## 7. 下一手唯一可直接推進的範圍
1. 優先核對 Owner 新補的成功 run／切換 commit／41 IDs 證據入口；能復用就復用，不重做全庫調查。
2. 取既有 archived request、response 和正式驗證資料，離線比對 prompt facts → response schema → expected_facts 的 ID 集合、順序、來源版本及 digest。
3. 沿原生呼叫鏈確認 runner 投影實際影響什麼，再追 external-plan → hydration → validator；按 fact ID 還原韓文重排。source decision 前依專案要求先 CodeGraph，不可用才限域 rg，不重建索引。
4. 能做的離線驗證：既有回應配舊／新轉換或 validator，定位是否轉換才出錯；不要呼叫 provider，也不要 import／執行會寫 runtime 或觸發佇列的入口。
5. 查既有模型／階段路由是否已有可用接點，僅提出符合實際用量的最小候選。不得預先指定 Flash；Spark 只列待證實的既有通道可能性，不新建 bridge/runner、不把截圖当已接通。
6. 若資料三處一致且原始回應已違約，明確報告「這幾筆生成違約，模型因果對照仍缺」，不要硬找程式 bug，也不要藉此要求整套重構。沒有 Flash 額度不妨礙完成離線診斷，但不能虛構受控模型對照。
- 修改前必須閉合最後成功版本、開始失敗 commit／機制、破壞的 invariant、可抓回歸的最小 RED；不足就列缺口及最小候選給 Owner，不繼續逐症狀打補丁。
- 禁止重設 quota／failed run、手動發布、provider 重試、放寬驗證、改模型、push/deploy、finalize／清理交易或 worktree。新對話不自動承接已用過的 production 授權。

## 8. Git、CC 與保留物
- 主工作區 `/Users/mattkuo/Documents/Pantheon`；本輪讀到 branch=`codex/g105-handoff-20260910`，有既有未追蹤控制文件／artifacts，全部保留。
- 先前已 push 的只有舊換手文件 commit f440c337a1d8f89fdbaadf072b1897e2c429c0b1；25ab／5d1a 沒有隨之推上 GitHub。外部 reviewer 找不到這兩個 ref 是審查材料缺口，不是 runtime 故障；本轮不 push。
- CC 已完成一次 Opus 零工具、只讀卡片文字的諮詢；不是「未送出」，也不是独立 runtime/code review。原文與主線勘誤：`.ai/cc_g105_handoff_advice_20260910.md`。其「先查白名單重複」優先度因 Owner 新證據下降，其他假說仍不是定論。
- 5d1a 候選：`.work/writer-lite-switch-20260910/source-g103-repair2`；備份：`.work/writer-lite-switch-20260910/source-promotion-g103-repair2/live-before`。
- runtime transaction：`transactions/four-lane-published-source-g103-repair2-20260910`，未 finalize；所有舊 worktrees／交易保留。
- 舊錯候選 6df73586c92d78dac6e9692f35552369d5208d6f 曾因錯基底回退控制面，已 rollback，禁止再 promote；舊交易 four-lane-published-source-20260910 已 ROLLED_BACK，不覆寫。
- 歷史完整卡：`handoff_20260910_g105_readonly_rootcause.md`；receipt：`.ai/four_lane_5d1a_execution_receipt_20260910.md`。舊卡或 `.ai/four_lane_current_handoff_20260910.md` 與本卡衝突時，以本卡最新限制為準。
- 本輪依 state-snapshot-handoff 分開保存根問題、配額 blocker、候選方向與證據等級；僅新增本文件，未重查正式 runtime／配額，未建立新任務。Owner 可將本卡交給新對話，本輪停止操作。
