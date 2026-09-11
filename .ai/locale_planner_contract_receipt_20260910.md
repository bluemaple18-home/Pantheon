# Lite planning 固定 coverage：主線 receipt

## 授權與狀態

- Owner：本對話明確「授權」。範圍見 [授權卡](locale_planner_contract_authorization_20260910.md)。
- 基線：`5d1a603b46fed15b8ba8ecaaf673923e0ac8285a`。
- 交付工作區：`.work/locale-planner-contract-20260910`，乾淨 sparse worktree 起始；與主工作區、原 source-g103-repair2、正式 actor 分離。
- 目前狀態：本地候選已交付，原多篇 P1 已修正並經原 Reviewer 複審 GO；Owner 補充明確資料/目的地授權後，Gemini Lite 三語 planning 實測 3/3 PASS，授權的三次 HTTP 已用完。尚未整合、部署或完成四線發文驗收。
- CodeGraph 回傳主工作區的其他分支警告，因此只作入口線索；本候選以固定基線與 worktree source/diff 為準，未重建索引。

## 已確認的根因層級

- 三語原始 prompt facts、archived schema、brief 重算均為同一組 41 個唯一 ID；來源投影符合既有 policy 適用範圍，digest 一致。
- `GeminiClient.generate_json` 呼叫 `_response_schema_for_model`。Flash 與 Lite 都移除超過 8 選項的 enum；原 41-ID schema 到 API 時只剩 string。此共同機制不是 bf174cf850 才新增，不把它當成已證明的換模因果。
- 本地 schema 本來也不保證 mapping 中每個 ID 恰好一次；另由 canonicalization 檢查。語言驗證在 hydration 後另做。
- 原英文違約只保留 enum path 診斷，未留可重播原文。日文重複/漏項與語言違約、韓文混語則有原始 external-plan。
- 以完整 5d1a module 的 `_hydrate_locale_plan` 本地重播：JA 拒絕 source fact coverage；KO 拒絕 article-01.coverage_note[5]；20:16 英文成功樣本 41 facts PASS。沒有呼叫 provider。
- Lite 已有後續英文成功，ledger 記錄 v0.3.404；公開頁面未驗收。本輪不宣稱四線恢復。

## 審查與設計裁決

- 唯一 Worker：Rawls；唯一獨立 Reviewer：Goodall；均 native clean context，未建立新側邊欄 task。
- Probe P1：不合法憑證例外文字可能帶出秘密。已加 ASCII/安全字元格式檢查與固定錯誤；transport ValueError 不保留原文；PASS 要求恰好一次 HTTP。原 Reviewer 以虛構 key 複審 GO，零真 key／零網路。核准 probe SHA-256：`e1a20a09a7537ea4dca76f3d88dca426fae8ba609ff3322d0bf9384056a569c3`。
- 產品首次全檔 422 PASS，但 Reviewer 重現多篇 anyOf 不受 broker 支援的 P1。主線退回同一 Worker，只修這個 finding；不重設 Repair 世代。
- 最小範圍改為單篇固定 coverage object；多篇保留 legacy 格式。不增加 broker 功能。
- 舊 pending migration 不在範圍。不符 request digest 時須明確拒絕，不能宣稱可無縫部署。

## 探測契約

- 只用原三筆 ASTRO-EXPANSION-50D-0035 brief，en/ja/ko 各最多 1 次 Gemini 3.5 Flash Lite planning，LOW。所有失敗也計次；不呼叫 Flash，不重試。
- 工具：`.work/locale-planner-probe-20260910/probe.py`。使用原生 `_run_locale_generation`，正文 provider 呼叫前停止；成功後再跑原 `validate_locale_plan`。
- prepare 保存實際 client 生成的 provider payload，execute 比對完整 payload、三個 source code digest、brief digest。attempt 在 HTTP 前以獨占檔案建立。
- 憑證只讀既有 pool 第一 slot，在記憶體使用；不寫 key，不輪替試打，不更新正式 allocator/queue。
- 已讀本地 admission snapshot：2026-09-10，450/1200，無 quota block/cooldown；不等於供應商剩餘配額。每次 execute 前仍重查。
- 三份首次 prepare 為零 API，因產品 review 修正需重建，完整保留於 `.work/locale-planner-probe-20260910/prepare-before-review-correction/`。

## 最終驗證

- 原 Reviewer 複審：原 anyOf P1 已解除，未發現新增 P0/P1；430 tests PASS（7.14s）。多篇 mixed locale 與 JA continuation 的 prompt/schema 與 5d1a 完全相同；實際 broker 與 Lite schema 投影接受合法多篇，原生 stage 拒絕跨篇錯配；9 個 authority 函式 AST 不變。
- 主線六個受影響 test files：321 PASS，唯一失敗是 sparse checkout 尚未補入 launchd 範本；補入基線範本後只重跑該 node，1 PASS。共 322 個相異外層案例通過。日誌：`evidence/affected-bounded-regression.txt`、`evidence/outbox-template-recheck.txt`。
- 更廣的 coordinator/deployment 測試曾中止於 89 failed / 626 passed，不能說全庫通過。主要已見缺 sparse 歷史輸入與 legacy fixture 拒絕；主線在未改 5d1a 完整 worktree 重現 `test_same_generation_locale_plan_retry_plan_is_zero_write` 相同 `legacy translation brief lane is invalid`。未逐一歸因所有廣測失敗，不據此放行部署。原日誌保留於 `evidence/affected-regression.txt`。
- `git diff --check` PASS；匯出 patch 對未改 5d1a `git apply --check` PASS，未實際套入舊 worktree。
- Patch：`.work/locale-planner-probe-20260910/evidence/candidate.patch`，SHA-256 `d75d55cf7715aa77adfce81f5601374de01fd39adadbf03c38149a3e3a25bf63`。
- 凍結 product SHA-256：`edef09933ec8d45e86515e8d4f55ad5c46a014a1a82f1100ec0aa6816c9e415b`；test SHA-256：`2c82089a740bafb4815078aaf9fcbd204684e9a175643fa2e14551cb5c28f421`。
- 重建後三份 `evidence/{en,ja,ko}/prepared.json` 均通過：41 個固定必填欄位、禁止額外欄位、code/brief/payload 綁定，HTTP=0。機器摘要：`evidence/verification-summary.json`。

## API 授權歷程與實測驗收

- 第一次執行英文 execute 在啟動前被自動核准審查拒絕：它認為既有「Lite planning 授權」尚未明確涵蓋資料傳送目的地。
- 主線補證 `evidence/egress-scope-check.json`：原文/policy/41 facts 與此前同來源同模型 archived request 完全相同；僅新增固定 ref/語言指令，payload 不含本機路徑或憑證欄位，endpoint 固定 `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`。以原命令重新送審仍被拒絕，理由明確要求 Owner 對上述來源文章/41 facts 與此目的地逐項授權。
- 上述兩次都沒有啟動 process，沒有 attempt marker，沒有讀真 key 或消耗 provider 呼叫。Owner 對明列文章、41 facts、編輯規則/schema 與 Google Gemini API 目的地的問題再次回覆「授權」後，才以原凍結 probe 與原命令執行；未改工具或路徑繞過拒絕。

| 語言 | 原生 planning / validator | 完整 fact ID | HTTP 次數 | 完成時間（臺北） |
| --- | --- | --- | --- | --- |
| en | PASS | 41/41 唯一、順序一致 | 1 | 2026-09-10 22:15:46 |
| ja | PASS | 41/41 唯一、順序一致 | 1 | 2026-09-10 22:17:02 |
| ko | PASS | 41/41 唯一、順序一致 | 1 | 2026-09-10 22:17:44 |

- 三次均為 `gemini-3.5-flash-lite`、LOW、固定第一 credential slot、單次 transport；沒有 retry、Flash、正文、Reviewer 或 Publisher 呼叫。實際使用 provider 額度三次，正式 allocator/admission 狀態沒有修改。
- 主線終驗：每筆 raw-response 與原生 external-plan 完全一致；完整 request schema 診斷通過；原 `validate_locale_plan` 通過；hydrated ID 序列等於原 brief 重新計算的 41 個唯一 facts；沒有 candidate/review artifact；三份 prepared code hashes 仍與凍結版本一致。沒有修改或後處理模型文字來取得 PASS。
- 證據入口：`.work/locale-planner-probe-20260910/evidence/{en,ja,ko}/` 的 `attempt.json`、`receipt.json`、`prepared.json`、`raw-response.json`、`planning-stage/locale-plan.json` 與 `planning-stage/planning-result.json`。`evidence/verification-summary.json` 彙整時間、payload/response/plan digest 與總呼叫數。
- 裁決：**GO，限本輪單篇 planning 候選及原三語樣本。** 已確認 Gemini 接受此固定 schema，三筆皆完成原生 planning 驗證；三個樣本不能代表長期成功率，也未證明換模因果或任意來源都成功。
- 尚未授權或驗收：整合、部署、舊單篇 pending migration、多篇 fixed 改善、獨立正文 Reviewer、Publisher、公開頁 HTTP 200/正文比對及四線端到端驗收。
- 未 commit/push/deploy/publish；沒有修改正式排程、quota 或 failed runs。所有舊交易、worktree 與未追蹤文件保留。

- 實測後獨立 Reviewer 終驗：離線核對三語各一次 Lite／LOW、payload／brief／code／operation 綁定、raw＝external、原始與投影 schema、原 validator、41 個唯一 facts 順序及無正文／review artifacts，均通過。支持本輪單篇 planning 候選 3/3 驗收；未新增 API、未修改檔案、未重跑全 suite。
