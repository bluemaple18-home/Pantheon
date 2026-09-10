# Pantheon 換手：g105已套用，多語未跑通；下一手只做唯讀根因比對

## 0. 最新Owner要求與停止邊界（優先於舊卡）
- Owner目標：保留既有機制，換模型後恢復四線 Writer→Reviewer→publish→公開HTTP200且正文可見；不是重做架構。
- Owner質疑「以前會過、現在不會過」，不接受未證實就歸咎模型或流程脆弱，也擔心AI先前修改／接線造成回歸。
- 主線已承諾：先唯讀比較最後成功版本與目前版本、成功／失敗任務輸入及實際設定；提出證據後才談最小修正。在此之前不改程式、不換模型、不改prompt、不放寬驗證器、不動排程、不重試或重置任務。
- 最新請求為「還是你先換手」。本輪只整理此卡及唯讀狀態，停止操作。沒有建立新task、沒有移交Mainline給其他代理；新對話讀本卡接續唯讀診斷即可。
- 舊5d1a部署授權已執行，不是新修復／再部署的通行證。Repair2已用；不能靠改卡名重置代數或再開第三代Repair。

## 1. root question／目前未解
為何以前成功的多語鏈現在失敗？需要區分模型輸出差異、prompt/schema/參數差異、驗證或規劃轉換差異，以及前次AI修改造成的回歸。
**根因尚未證實。**「Flash Lite太差」「流程太脆」是主線已撤回的過度推論，不得當換手結論。現有失敗輸出只能證明被哪些契約拒絕，不能單獨證明因果。

## 2. 正式狀態：20:14:48 +08:00唯讀核對
- runtime（本機）：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8`；actor為其`actor/`，queue為`queue/`，publisher ledger為`state/ledger.json`。
- 正式HEAD：`5d1a603b46fed15b8ba8ecaaf673923e0ac8285a`，actor工作樹乾淨。
- generation：`g105-5d1a603b46-published-source-20260910`。
- manifest digest：`fea34bd838004b93ce1331907045370bb70ab92e229478039afd4d4aca15dcf0`。
- 七服務launchctl print皆rc0；coordinator／四lane／publisher間隔60秒，capacity guard300秒。這是載入狀態，不代替端到端驗收。
- Writer=`gemini-3.5-flash-lite`；Reviewer=`gemini-3.1-flash-lite`；共享daily admission cap=`1200`。未切Spark，未改排程間隔。
- 最新中文new ledger：v0.3.401，run=`auto-new-v1-20260910-048-01`，commit=`e33569e3b5e1e77556ab4a65485cfed9d8fa0c85`，19:25:23。
- 最新中文rewrite ledger：v0.3.403，run=`legacy-auto-sweep-v1-astrology-0033-astro-expansion-50d-0033`，commit=`8f4649ce00dfc7c8d16f659ee51ca1fb9a7f3d5d`，20:13:41。這是正常排程自行產出；本輪只查ledger，尚未公開正文驗收。
- translation ledger仍12筆，最後一筆v0.3.389、ko、`auto-i18n-ko-f27547593f9ad93030fb-replacement-01`，commit=`2905a3ffa2322221a46ca98b1e9b02f1fdba3c08`，09:19:28。此為歷史成功調查候選，不代表已證明和現在同一輸入／prompt／模型／規劃代際。
- 自動排程保持原狀；沒有停用全部服務。20:13後可能有新seed／新結果，以上有明確觀測時點，不可假設runtime凍結。

## 3. 這次實際改了多少
相對前一正式actor `25ab1a40c9f9a3fed35bc5e4cac59d4939159bba`（g103）：
- `scripts/agy_gemini_runner.py`：+187/-5，固定已發布Git ref、publisher證據與來源投影；保留原生registered translation入口，仍驗證source digest及auto/replacement lineage。
- `tests/test_agy_source_authority_contract.py`：+327/-0。
- `tests/test_translation_dispatch_authority.py`：+52/-13，真Git/ledger fixture及原生入口回歸；原assertions保留。
- 合計三檔+566/-18；5d1a直接parent是25ab，其餘tracked tree相同。**不是只有改參數，但沒有整套重寫。**此數不含更早g103裡的換模型／1200額度修改。
- 本地另改`.work/writer-lite-switch-20260910/source_control.py`、`source_promotion.py`候選／generation／備份／交易／授權參數及`test_source_control.py`；另有控制卡、receipt與handoff文件。
- 這次沒有改多語規劃器、語言驗證器、Writer/Reviewer prompt或模型路由。Owner要求唯讀根因比較後，沒有再改產品程式。

## 4. 已驗證與不能混淆的結論
- 產品指定五檔126PASS，原Reviewer GO；操作31PASS，兩原Reviewer各獨立GO；主線另跑通過。
- native apply POSTCHECK_PASSED；三installer stage PASS；staged完整publisher wrapper/env/working directory + --dry-run rc0/statusok；normal activate rc0；主線獨立七receipt live aggregate PASS、capacity preflight PASS。
- actor套用後曾fetch origin/main到9943c65520eea315405b4ca8d7e31860e6561588（v402）；new/rewrite最新來源與brief source digest吻合。這不等於多語文稿合格或已發布。
- dry-run不是完全零寫入：既有create selector記錄quarantine（rewrite非create分類／new未核准）。publisher與25ab同blob `a397dd98e850049dddba1752c5a3abca84997d85`；rewrite selector明確排除「publisher only supports create mode」原因。未擦ledger，未重置failedrun或allocator。
- **兩i18n線本輪公開驗收未完成，不可宣稱四線GO。**

## 5. 三筆真實失敗證據（20:00前；未再人工重試）
來源article=`ASTRO-EXPANSION-50D-0035`，lane=`i18n-rewrite`。
1. en run=`auto-i18n-en-4537d2fa89dc2d1c5bed`；job=`bd4f213b95760f031dd7dd4912c6d29b26adc7e1`。broker outcomeSUCCESS，但SCHEMA_INVALID_PAYLOAD，coverage_mapping[24].source_fact_id enum不符，最後LocalePlanValidationError。
2. ja run=`auto-i18n-ja-5653a1887f273669a763`；job=`4c78066b422715ee255f413d871cbf63c998afad`。API/inbox成功，planning-result為`external locale plan source fact coverage differs for article-01`；external-plan中有重複fact ID。
3. ko run=`auto-i18n-ko-dceee8434dba1346871d`；job=`1b994bd23bece66be64a0688b9b0d658cbd6ef70`。API/inbox成功，planning-result為`locale plan native locale language differs for article-01.coverage_note[5]`。
- 證據入口：runtime的`queue/translation-runs/<run>/brief.json`、`attempts/01/planning-result.json`、`external-plan.json`、`plan-operation.json`；`queue/lanes/i18n-rewrite/{failed,inbox}/<job>.json`。en失敗可能無external-plan，不可虛構。
- 韓語陷阱：主線曾用raw mapping[5]的純韓文誤猜validator誤擋；逐條跑原predicate後raw索引15/28–32/36/39實際混入中文標題／標籤。錯誤索引和raw位置不能直接等同；須核對正式plan轉換及順序，尚未完成該因果比對。
- 三筆皆未到Reviewer/publish。API有回應不代表所有欄位正確；退件也不足以斷定模型不適用。保留所有失敗與計數。

## 6. 下一手唯一scope：唯讀比較，先給原因證據
1. 從歷史translation ledger選一筆可追溯成功run，核實它實際使用的actor、模型、prompt、schema、參數與planning入口；不要用「g103中文會發文」冒充「同多語規劃以前會過」。
2. 與上述失敗run比較實際送出的request／source fact package／response／plan轉換／validator版本。沿CodeGraph先查（此前不可用，若仍不可用用限域rg）；不要重掃全庫或重建索引。
3. 先排除AI引入的回歸與接線錯誤；可做不呼叫provider、不寫runtime的離線replay／原validator比對。尚未做成功失敗同輸入受控對照，不能聲稱完成。
4. 回報最後成功證據、開始失敗的commit或機制、破壞的invariant、能重現的最小RED。沒有证據不改程式，不換模型，不放寬gate，不重置run，不部署。
- 目前沒有核准新修法。拿到根因與最小修改範圍後再交Owner裁決；不得因新對話而跳過Repair ceiling與停止邊界。

## 7. 保留與回退資料（不得自動執行）
- 本地候選worktree：`.work/writer-lite-switch-20260910/source-g103-repair2`（5d1a）；其他worktrees全保留。
- 專用output/備份：`.work/writer-lite-switch-20260910/source-promotion-g103-repair2/live-before`；exact backup十roots含manifest/barrier/七plist/fullstage，不還原queue/allocator。初始舊snapshot缺已消費outbox而失敗，其partial資料保留；原exact backup已補全與核對。
- 正式transaction：runtime的`transactions/four-lane-published-source-g103-repair2-20260910`；plan digest=`a0e3c0ed45318dca40954c354d8a159ef228342c33f5a9e83c58f02f344a0fc2`。未finalize，不能隨意刪除或直接復用。
- 舊錯候選6df73586c92d78dac6e9692f35552369d5208d6f錯基於cba120，曾回退g103模型／coordinator等，已rollback，禁止再promote。其舊transaction `four-lane-published-source-20260910` 已ROLLED_BACK，保留不可覆寫。
- 本卡最後寫入前無主線未完成的shell session；原Worker/Reviewer最後均已回覆，未新派工。不要自行重啟代理或另建task。

## 8. 證據索引與歷史注意
- `.ai/four_lane_5d1a_execution_receipt_20260910.md`
- `.ai/four_lane_5d1a_promotion_authorization_20260910.md`（已執行的舊授權，不蓋過本卡唯讀邊界）
- `.ai/codex_task_source_g103_repair2_20260910.md`及同名review卡。
- `.ai/codex_task_5d1a_operation_mapping_20260910.md`
- `.ai/four_lane_current_handoff_20260910.md`含多代歷史與已過時段落；**衝突以本卡最新觀測／Owner邊界為準**，不可照舊段落再部署。
