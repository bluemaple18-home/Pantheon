# Slice C-A / C-B bounded capability與 C-C 審查快照

結果：`C_A_TRACE_COMPILER_GREEN`；`C_B_R2_GREEN`

遠端審查快照：`BLOCKED_C_C_INSTALLER_SHARED_CONFIG_APPROVAL_REQUIRED`

這個快照只供外部 GPT／Reviewer 檢查 scope、必要性與最小充分性。它不是 accepted candidate，也不授權 install、activation、provider、production、public mutation 或 Slice C closeout。

## 已交付 capability

- 以既有 editorial / translation `run_writer_reviewer` 在 disposable staging copy 實際錄取 role、model、prompt、schema，並用既有 `build_external_request` 重算 exact job/request identity。
- 每個 lane output 是一份 strict R2 bundle，綁 accepted base、actor、generation、canonical lane queue root、lane/run/namespace、required entry budget、sealed executable 與 result digest。
- actor root HEAD 與 accepted-base ancestry、generation format、lane-kind pair、root isolation、source 無 candidate/review/attempt resume artifacts均 preflight fail closed。
- production deterministic finding 可合法省略 Reviewer；RecordingSealedClient 忠實留下單一 Writer trace，未用 payload 則 fail closed。
- compiler 只寫 staging copy 與明示 evidence bundle；runtime queue/inbox/state 與 provider/public/push 皆未寫入。

## 未涵蓋範圍

C-A/C-B 不執行 Cohort runtime schedule、activation、terminal closeout 或 Publisher。既有 `BLOCKED_C_NO_EXISTING_FIXED_COHORT_SCHEDULE_SEAM` 不會因本 bounded materializer 自動解除。C-D 為 `NOT_RUN`；C-C 只有未完成、未驗收的 installer preflight 草稿，狀態為 `BLOCKED_C_C_INSTALLER_SHARED_CONFIG_APPROVAL_REQUIRED`。

## Scope audit

目前已進入受控 scope expansion 黃燈：C-A 新增 trace compiler，C-B 新增 production Coordinator materializer，C-C 又觸及共用 launchd installer。雖然沒有新增 daemon、queue、FSM、database、ledger 或第二套 runtime，但原 verification card 已部分轉成 capability implementation。

外部 review 應先裁決：

- C-A／C-B 是否為證明 four-lane runtime 所不可缺的 minimum sufficient seam。
- C-B 是否仍可縮成更薄 mapping，而不犧牲 fail-before-write、crash resume、identity envelope 與 rewrite authority。
- C-C 是否應改用 disposable acceptance-only plist／stage，避免改動共用 installer。
- 若 C-C 必須改共用 installer，是否應另立 implementation card，再回本 acceptance card 驗收。

C-C preliminary diff 只加入 sealed mode 的輸入與 bundle authority preflight；lane plist argv／environment binding 尚未完成，沒有對它宣告測試綠燈，也不得以此 branch 執行 installer。

## C-B exact materializer

- Coordinator 只接受 adapter 產生、source terminal 且 review APPROVE 的單筆 i18n dependency，並只呼叫既有 `multilingual.enqueue_article_translations`；未重寫 translation pipeline。
- source candidate、review、result SHA、source brief mode/run/article、lane pairing、pending digest 與 transaction `exact_run_ids`（含 source / translation id、無重複）皆在 translation queue 寫入前 strict 驗證。
- rewrite metadata 只取該 source run 綁定 `brief.json` 的 `immutable_fields`，經既有 `_campaign_translation_source` 正規化；不讀 current public record。
- 原 pending receipt atomically terminalize 為 `materialized` 並含 exact registration binding；重跑驗 existing brief/state 後回 `already_materialized`。enqueue→receipt crash 僅接受 run directory 只有 byte-identical expected `brief.json` 的既有缺 registry 狀態；extra file 或 brief drift fail closed。
- queue 寫入只來自既有 multilingual owner path；回傳區分 `queue_mutation` 和 `public_mutation=False`。
- R1 強化 transaction `exact_run_ids` 必須為四筆 unique APF cohort identity；缺少或多出任一 id 都在任何 translation queue 寫入前拒絕。source brief 另以既有 `_identity_envelope_from_brief` 與 `_validate_identity_envelope` 對 source state identity envelope 做 exact match。
- i18n-rewrite regression 證明 translation source 的 immutable metadata 取自 bound rewrite brief、`bodySections` 取自 reviewed candidate，並在禁用 `load_source_article` 時仍可 materialize 與 byte-idempotently replay。
- R2 收緊 adapter resume：materialized receipt registration 必須有 exact keys、target run id、source dependency run id、lane 與 SHA-256 shape；重算 receipt digest 也無法以 source registration identity drift 讓 adapter 重入 applied。

## 驗證

見 [raw-test-output.txt](raw-test-output.txt)：C-A 10 tests 與 Runner regression 67 tests 均 PASS；`py_compile` 與 `git diff --check` PASS。

C-B/R2 focused 12 tests PASS（local command runner 的 30 秒單次上限下，採 bounded individual/pair invocations）；較廣 `tests/test_agy_gemini_coordinator.py -k apf_004 -q` 為 38 PASS / 428 deselected；Runner regression 67 PASS；C-A compiler 10 PASS；Coordinator/controller `py_compile` 與 `git diff --check` PASS。
