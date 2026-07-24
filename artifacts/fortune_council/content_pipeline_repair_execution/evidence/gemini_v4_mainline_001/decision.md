# Decision

Status: BLOCKED

Rollout decision: DO_NOT_PROMOTE_DEFAULT

## Facts

- Concurrent-create replay anchor provenance 的唯一 production defect 已由 public seam RED 重現並以最小修正轉 GREEN。
- Flag-off／flag-on synthetic acceptance matrix 為 `21 passed`。
- 唯一真實 `agy 1.1.5` canary 為 durable `COMPLETE/1`，`EXEC_CONFIRMED` 恰一個，strict result schema通過，沒有 retry、fallback或failed record。
- 受監督產文線仍固定 legacy CLI；本卡沒有修改產文、文章、registry、sitemap、feed、prerender或發布狀態。

## Interpretation

本 candidate 已具備送獨立 Review 的 exactly-once transport evidence，但真實 canary 只證明 trusted executable snapshot 的本機 transport completion 與 ledger/anchor/replay accounting，不能獨立證明 provider internal model-call provenance。

在獨立 Review、small shadow run 與另立 migration commit 之前，`AGY_GEMINI_V4_BROKER` 維持唯一 opt-in，V4 不成為預設 transport。

## JSON_INVALID continuation

Activation-004 證明 exactly-once transport 仍為 `COMPLETE/1`，但 caller result 是
`JSON_INVALID`。本 candidate 新增 value-free closed classifier 與 runner 二次
sanitizer，讓下一次結果能區分六種格式類別；它不自動修正 Gemini 輸出，也沒有
新增真實外呼。

因此目前決策維持：

- status：`BLOCKED`
- rollout：`DO_NOT_PROMOTE_DEFAULT`
- legacy default：維持
- next external canary：必須重新揭露 payload 並取得明確確認

## Canary-005 preflight decision

獨立 `gpt-5.5 / medium` Review 對 diagnostic candidate 回報 `GO`，沒有 P0–P3
finding。全新 job、request digest、namespace 與 repo 外 queue 已建立，generation
invocation 仍為 0。

目前 local updater 已把 executable 更新為 `agy 1.1.6`，因此下一次明確確認必須
包含新版本與新 digest。確認前主卡仍為 `BLOCKED`；這份 preflight 只進入
`AWAITING_EXTERNAL_CONFIRMATION`，不授權 retry、fallback、pipeline continuation、
publisher、publish、promotion 或 legacy removal。

## Canary-005 final decision

- process count：`1`
- durable replay：`COMPLETE`
- process outcome：`SUCCESS`
- caller result：`JSON_INVALID`
- closed diagnostic：`PARSE_ERROR_AT_END`
- inbox delivery：`absent`

這個結果證明 exactly-once 與新 closed diagnostic 正常，但長文章 stdout 在末端未
形成合法 JSON。它排除 empty、encoding、fence 與 wrapper 類原因；未讀 raw
response，因此不能進一步宣稱是 provider token limit、CLI truncation 或缺少哪個
結尾 token。

決策維持 `BLOCKED / DO_NOT_PROMOTE_DEFAULT`。本 job 不得 retry；下一步只能先做
針對 output completion boundary 的離線 root-cause／repair，再以新 job 重新取得
外部授權。

## Output completion architecture decision

離線 root-cause 已完成。`agy 1.1.6 --print` 沒有 machine-enforced JSON
Schema／structured-output contract；因此 prompt 內附 schema 無法保證長文章 stdout
形成完整 JSON。現有證據也排除 broker result ceiling、外層 timeout、fence與
wrapper是本次相容根因。

本卡拒絕以下假修復：

- 自動補 JSON delimiter或 tolerant parse；
- 對同一 operation retry；
- 未改變 transport capability 就執行第四次 canary。

最小可行下一步是另立 transport architecture boundary，使用原生 structured
output，或把長文章拆成各自有 operation identity／ledger 的 bounded chunks。
兩者都超出本卡 allowlist與 single-shot contract。

Final decision：

- status：`BLOCKED`
- rollout：`DO_NOT_PROMOTE_DEFAULT`
- legacy default：維持
- V4 flag-on：維持 fail closed
- additional real canary under this blocker：`0`

## Provider-native structured candidate

同一主卡已形成 `gemini_structured_api_v1` candidate。它重用現有 production API
schema payload，但把一次 process、adapter digest、credential FD、redirect refusal、
finish reason與本地 schema gate納入 V4 fail-closed boundary。

目前 decision：

- candidate：`READY_FOR_REVIEW`
- rollout：`DO_NOT_PROMOTE_DEFAULT`
- real structured API call：`0`
- credential mutation：`0`
- legacy publish default：維持

下一個外部步驟只能在獨立 Review後，揭露 model、public payload hash、adapter
digest與最大一次 request，再取得明確確認。未通過前不得移除 legacy rollback。

Local code review已修正唯一維運 finding：structured target的 closed failure code
現在可安全穿過 broker／runner雙 allowlist；未知 stderr仍被丟棄。未發現其餘
P0–P2 finding。這不取代獨立 Review。
