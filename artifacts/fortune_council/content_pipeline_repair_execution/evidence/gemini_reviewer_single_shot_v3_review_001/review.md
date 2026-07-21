# Single-Shot V3 independent review

## Verdict

`NO_GO`

- Reviewed candidate: `a5309552a9e7caf3ba85fb627a82dbfee0b3c21c`
- Fixed range: `37e1cf2b81eb10006ad2ec41bfdc81df12e94144..a5309552a9e7caf3ba85fb627a82dbfee0b3c21c`
- Provisioning commit: `bbd19cfb6be852cbe4342eef5a3095cba8a1174b`（不屬於 candidate）
- Review kind / thickness: `full / strict`
- Gemini invocation: `0`；所有驗證皆為離線 replay 或 test double。

任一 P1/P2、production safety risk 或 single-shot invariant 無法沿 production caller 重現即須 `NO_GO`。本次有五筆阻塞 finding。

## Findings

### [P1] V3 operation contract 未接入 production callers

- Path: `scripts/agy_gemini_transport_probe.py:332`, `scripts/agy_gemini_transport_probe.py:666`, `scripts/agy_seo_copy_pipeline.py:1847`, `scripts/agy_seo_copy_pipeline.py:1877`, `scripts/agy_seo_copy_pipeline.py:1910`, `scripts/agy_gemini_outbox.py:263`, `scripts/agy_gemini_outbox.py:268`, `scripts/agy_gemini_runner.py:44`, `scripts/agy_gemini_runner.py:57`
- Trigger: 由 production CLI/HTTP、outbox tick 或 runner 執行 Writer/Reviewer；pipeline 進入 schema/content repair loop。
- Evidence: repo caller trace 顯示 `execute_single_shot_operation`、`plan_resume_operations`、`replay_operation_records` 只在 `agy_gemini_transport_probe.py` 的 corpus/probe 路徑內被呼叫。Production `_generate_with_receipt` 直接呼叫 `client.generate_json`，且 `run_writer_reviewer` 仍以 `while True` 推進多個 generation；production receipt 沒有 V3 operation ID、manifest、terminal、gate、request/run/candidate binding，也沒有第三個同 blocker後停止的 operation history。
- Risk: candidate 只證明 sanitized probe 單次啟動，無法證明 production 同 operation 最多一個 external process、精確 launcher accounting、resume policy 或 immutable evidence；V2 public API 等價反例在 production boundary 仍未被結構性消除。
- Suggested fix: 把 operation binding、exclusive manifest、單次 launcher、terminal/gate 與 resume planner整合到所有 production transport callers；每次 external call 必須先有 fresh operation identity，且 production history成為唯一 resume/stop authority。
- Validation gap: focused tests 全綠，但沒有測試沿 production CLI/HTTP/outbox/runner caller 驗證 V3 records與同 operation 0/1 process。
- Confidence: high。

### [P1] Outbox pending resume 未驗證落盤 request binding

- Path: `scripts/agy_gemini_outbox.py:243`, `scripts/agy_gemini_outbox.py:253`, `scripts/agy_gemini_outbox.py:258`, `scripts/agy_gemini_outbox.py:260`
- Trigger: pending receipt 跨 tick 後，預期 job ID 的 outbox/processing/archive 檔存在，但檔內 request 是錯誤或遭替換的 binding；inbox response 則符合重新計算的 expected request。
- Evidence: `adversarial_probes.py` 在 expected filename 寫入錯誤 `request_sha256`，再寫入符合 expected binding 的 response；`consume_existing_json` 只檢查任一路徑存在，未讀取與 strict validate該 request，最後回傳 response。結果：`wrong_stored_request_binding_consumed=true`。
- Risk: 跨 tick consume 可脫離實際排入 queue 的 request bytes；錯 request／錯 binding 不會 fail closed，machine 可把未由該落盤 operation 授權的 response接回舊 operation。
- Suggested fix: 唯一定位 existing request，strict parse、validate並逐欄比對 expected request；duplicate path、malformed、mismatch或缺檔皆在 consume前拒絕，且不得建立新 job。
- Validation gap: 現有 test 只覆蓋正確 bound response，未覆蓋 expected filename 搭配錯 request bytes。
- Confidence: high。

### [P1] 自洽替換整組 record 可繞過 hash-chain replay

- Path: `scripts/agy_gemini_transport_probe.py:470`, `scripts/agy_gemini_transport_probe.py:496`, `scripts/agy_gemini_transport_probe.py:499`
- Trigger: manifest、terminal、gate 三份 record 全部被替換，攻擊者同步改 item/request/candidate binding並重算兩個 parent hash。
- Evidence: offline probe 先用 public V3 API建立合法 triple，再將三份 record 的 `item_id`、`request_id`、`candidate_sha256` 一起替換並重算 chain；`replay_operation_records` 接受且回傳 replacement item。結果：`self_consistent_whole_triple_replacement_replayed=true`。
- Risk: hash chain只證明三份目前 bytes彼此自洽，沒有不可替換的外部 anchor；candidate/operation evidence 可被整組重寫而仍通過 replay，違反 immutable evidence與無 record replacement旁路要求。
- Suggested fix: 將 manifest digest提交到不可覆寫且獨立驗證的 operation index/ledger，或使用受信任簽章／append-only anchor；replay 必須同時驗證外部 anchor與 triple。
- Validation gap: 現有 tamper matrix只改單一 record而不重算下游 hash，未測 whole-triple self-consistent replacement。
- Confidence: high。

### [P1] Preflight 與 launcher 間存在 concurrent-writer TOCTOU

- Path: `scripts/agy_gemini_transport_probe.py:340`, `scripts/agy_gemini_transport_probe.py:341`, `scripts/agy_gemini_transport_probe.py:359`, `scripts/agy_gemini_transport_probe.py:366`, `scripts/agy_gemini_transport_probe.py:395`
- Trigger: caller通過初始 `exists()` 檢查並 exclusive建立 manifest後，另一 writer 在 launcher前建立 terminal path。
- Evidence: offline probe在 manifest exclusive create完成時插入 concurrent terminal，隨後 candidate仍呼叫 launcher一次，直到寫 terminal才收到 `FileExistsError`。結果：`concurrent_terminal_case_launcher_calls=1`。
- Risk: malformed/partial/concurrent state沒有在 process前 fail closed；同 operation可能已啟動 external process，卻留下不可信 partial records，且無可靠 accounting/gate closure。
- Suggested fix: 對 operation取得跨 process exclusive claim/lock並預先保留完整 record namespace，或使用單一原子 operation directory ownership；任何既有/競態建立需在 launcher前阻止 process。
- Validation gap: 現有 concurrent coverage只驗證兩個 caller同搶 manifest，未覆蓋 manifest建立後、launcher前的 terminal/gate競態。
- Confidence: high。

### [P1] Model witness 可用 swapped existing quote 通過 machine gate

- Path: `scripts/agy_gemini_transport_probe.py:190`, `scripts/agy_gemini_transport_probe.py:195`, `scripts/agy_gemini_transport_probe.py:199`, `scripts/agy_gemini_transport_probe.py:203`
- Trigger: 兩個合法 model code 都存在於 target，但每個 finding 的 `evidence_quote` 對調成另一個 code 的既有文字。
- Evidence: `GUARANTEE_CLAIM` 使用「官方研究」，`UNSUPPORTED_AUTHORITY` 使用「保證今天投資獲利」；validators只在整體 target搜尋固定關鍵字，quote只需任意存在 target，結果 `swapped_existing_quotes_machine_accepted=true`。
- Risk: evidence quote與 code predicate未綁定，無關／other-claim quote仍能 machine REJECT；脆弱 keyword validator不符合 code-specific local proof要求，可能造成錯誤阻擋內容。
- Suggested fix: 每個 machine code建立能直接驗證該 finding quote語義/結構的 code-specific predicate；無法本地可靠證明者降為 advisory，不得影響 machine verdict。
- Validation gap: 現有 tests只驗 quote存在 target與 expected code集合，未測 swapped quote、generic token或 unrelated existing quote。
- Confidence: high。

## Spec axis

- `FAIL`：sanitized corpus確實重現 6 operations / 6 processes，且 basic duplicate、CLI missing/nonzero/timeout、strict JSON與單-record tamper tests通過。
- `FAIL`：production callers沒有採用 V3 operation contract，因此 single-shot、resume、count、third-blocker stop與 immutable records不能沿 production path成立。
- `FAIL`：outbox wrong binding、whole-triple replacement、concurrent writer與 evidence/code binding均有可重現旁路。

## Standards axis

- `PASS`：fixed range符合 implementation allowlist；provisioning commit只新增 Review card；review輸出只在 Review evidence allowlist。
- `PASS`：focused 102 tests、py_compile、git diff check與privacy scan通過。
- `FAIL`：production safety invariant以 probe-only module代替 production integration；tests因測試邊界過窄而未偵測上述五個阻塞問題。

## Testing gaps

- 缺 production caller graph的 end-to-end operation/accounting tests。
- 缺 outbox existing request bytes strict binding與duplicate queue-state tests。
- 缺 whole-triple replacement + recomputed hash的 trusted-anchor test。
- 缺 manifest後、launcher前 concurrent terminal/gate create測試。
- 缺 swapped/generic/other-item evidence quote對 code predicate的 negative tests。

## Residual risks

- Provider內部 model calls不可觀測，維持 `unobservable/unknown`，不得推論為 6。
- Reviewer未呼叫 Gemini；stored corpus只證明既有六次 sanitized execution的 record一致性，不證明 production integration。
- Full suite未由本 Review重跑；implementation evidence記載的 Ziwei兩筆 baseline failure不得視為全綠，且與本次五筆 blocker無抵銷關係。

## Decision

`NO_GO`。禁止 merge、push、deploy、publish或恢復內容線；candidate不得由本 Review修補。
