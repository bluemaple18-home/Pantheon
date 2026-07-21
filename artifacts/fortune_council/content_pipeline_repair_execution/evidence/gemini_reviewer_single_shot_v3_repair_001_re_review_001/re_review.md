# Single-Shot V3 Repair 1 independent re-review

## Verdict

`NO_GO`

- Reviewed candidate: `c2061f0945945af3ae6133d655780b8df0b79d8e`
- Candidate parent / Repair provisioning: `a871c0825e06a51e7e29660180e907258c6ec67c`
- Original V3 candidate: `a5309552a9e7caf3ba85fb627a82dbfee0b3c21c`
- Original Review evidence commit: `be19f6223eaebcece71b326f71a497c7b161d3a8`
- Gemini CLI / HTTP / external model invocation by re-review: `0`

五個原 P1 中，strict persisted outbox、caller-owned anchored replay、code-specific witness已關閉；production operation accounting與atomic namespace ownership仍各有一個可重現 P1。依 strict card，任一 P1或 production safety risk存在即為 `NO_GO`。

## Findings

### [P1] Production CLI_NOT_FOUND 被記成已啟動 external process

- Path: `scripts/agy_seo_copy_pipeline.py:1388`, `scripts/agy_seo_copy_pipeline.py:1398`, `scripts/agy_seo_copy_pipeline.py:1458`, `scripts/agy_seo_copy_pipeline.py:1459`, `scripts/agy_seo_copy_pipeline.py:1923`, `scripts/agy_gemini_operations.py:217`, `scripts/agy_gemini_operations.py:227`, `scripts/agy_gemini_operations.py:232`
- Trigger: production `_generate_with_receipt` 使用真實 `_cli_transport`，CLI command不存在或 `subprocess.run` 在 exec前丟出 `FileNotFoundError`。
- Reproducible evidence: fresh offline probe將 `AGY_GEMINI_CLI` 指向不存在的檔案。`_cli_transport` 把 `FileNotFoundError` 包成一般 `RuntimeError`；共用 operation層因此走 generic exception分支。結果為 `error_type=RuntimeError`、`failure_code=PROCESS_FAILURE`、`process_started=true`、`terminal_status=PROCESS_TERMINAL`，實際 external process為 0。
- Risk: production accounting違反 `CLI_NOT_FOUND = 0 external`；launcher count、terminal state與後續 audit/resume policy會把未啟動的 process當成已啟動，無法證明 0/1 invariant的精確性。
- Minimal repair interface: transport需保留「未啟動」的 typed outcome（例如不包裝 `FileNotFoundError`，或回傳明確 `PROCESS_NOT_STARTED/CLI_NOT_FOUND`）；operation層只能在 subprocess成功 spawn後設定 `process_started=true`，不可由 generic exception推論已啟動。
- Validation gap: `tests/test_agy_gemini_operations.py:74`只讓抽象 launcher直接丟 `FileNotFoundError`；沒有沿 production `_generate_with_receipt → GeminiClient.generate_json → _cli_transport` 驗證 CLI missing accounting。
- Confidence: high。

### [P1] Claim directory未在 launcher期間維持 exclusive record ownership

- Path: `scripts/agy_gemini_operations.py:158`, `scripts/agy_gemini_operations.py:172`, `scripts/agy_gemini_operations.py:190`, `scripts/agy_gemini_operations.py:200`, `scripts/agy_gemini_operations.py:202`, `scripts/agy_gemini_operations.py:218`, `scripts/agy_gemini_operations.py:247`
- Trigger: owner完成 manifest claim與 pre-launch檢查後，launcher已開始執行；另一 writer用相同 filesystem權限建立該 operation的 terminal path。
- Reproducible evidence: fresh probe在 launcher內模擬 concurrent writer寫入 `terminal.during.json`。結果 `during_launch_calls=1`，外部 launcher已被呼叫；owner直到 launcher返回後 exclusive寫 terminal才收到 `FileExistsError`，injected bytes保留且 gate缺失。對照 pre-launch注入可正確得到 `prelaunch_calls=0`。
- Risk: claim只阻止啟動前競態，沒有保護 launcher執行期間的 namespace；合法 writer仍可插入 terminal，使 operation已花費一次 external call卻留下 partial/foreign evidence，破壞 immutable triple與精確 accounting。
- Minimal repair interface: claim時原子保留 terminal/gate寫入權（例如預先取得 owner-only file descriptors、單一 append-only journal或等價 reservation），並讓非owner writer在 launcher期間無法建立/替換 record；完成時只能由 claim owner提交一次。
- Validation gap: `tests/test_agy_gemini_operations.py:50`只在 manifest writer返回前插入 terminal，未覆蓋 pre-launch check後、launcher進行中的跨 process create。
- Confidence: high。

## Original P1 closure matrix

### P1-01｜production caller graph：`PARTIAL / FAIL`

- Pipeline、outbox、runner與probe現已呼叫共用 `agy_gemini_operations`；success/nonzero/timeout單次 launcher與 fresh operation結構存在。
- Resume planner fresh probe確認 APPROVED不重送、第三個同 blocker後無第四個。
- 但 production CLI_NOT_FOUND accounting錯誤，故本 P1未完整關閉。

### P1-02｜strict persisted outbox：`CLOSED`

- Fresh probes對 0份、2份、malformed、unknown field、binding mismatch均在 consume前 `ValueError`。
- Outbox job數未增加，未呼叫 generate或建立第二 job。
- Response仍綁 request SHA、operation ID、manifest digest與model。

### P1-03｜caller-owned commitments：`CLOSED`

- Whole-triple replacement並重算 hash後，原 caller commitment拒絕 replay。
- Stored 6-operation corpus由獨立 commitments summary驗證：6 logical、6 external、6 approved、0 blocked、provider calls unknown。
- `allow_other_operations=True` 的唯一 production caller位於 `agy_gemini_outbox.py:328`，每次只傳當前 response的單一 commitment；fresh probe在同 root存在其他 operation時仍只 replay指定 operation，且 target triple必須精確匹配 external commitment，未形成 unanchored replay旁路。
- 共用 API形式上可接受多個 commitments，但每個仍逐一驗證完整 binding與manifest digest；此點未造成 safety bypass。

### P1-04｜atomic namespace：`PARTIAL / FAIL`

- Manifest後、launcher前插入 terminal已能 0-call fail closed並保留舊 bytes。
- Launcher執行期間 ownership仍可被另一 writer繞過，故本 P1未完整關閉。

### P1-05｜code-specific witness：`CLOSED`

- Valid quote通過；swapped、generic、structural、synthetic、other-item quote均不影響 machine verdict。
- Quote本身必須存在 target並滿足對應 code predicate；unknown/unvalidated code不在 schema allowlist。

## Spec axis

- `FAIL`：兩個 production safety invariant仍可重現，未達五個 P1全部關閉的 GO條件。
- `PASS`：strict outbox、anchored replay、stored corpus、witness與resume的指定負向案例通過。

## Standards axis

- `PASS`：Repair candidate commit只修改 Repair card allowlist內檔案；re-review只新增指定 evidence路徑。
- `PASS`：focused 129 tests、stored corpus replay、source compile、runtime retry search與`git diff --check`通過。
- `BASELINE`：full suite為244 passed、2 failed、2 warnings；兩個 failure均為既有 Ziwei provider `iztro` vs `pantheon_ziwei`，不得寫成全綠，也不抵銷本次 P1。

## Testing gaps

- 缺 production CLI-not-found穿越 wrapper後仍為0-process的 regression。
- 缺 launcher已開始後 concurrent terminal/gate writer的 ownership regression。

## Residual risks

- Provider內部 model calls維持 `unobservable/unknown`。
- `allow_other_operations` 是共用 public flag而非型別上限定單 commitment；目前 production只以單 commitment使用，且 exact anchor仍強制成立。
- 原 adversarial script原封執行時在 strict outbox mismatch立即拋出 `ValueError`，因此不會輸出舊版完整 boolean JSON；五項 closure由本 re-review的獨立 fresh probes逐項驗證。

## Decision

`NO_GO`。禁止整合、merge、push、deploy、publish或 content recovery；本 re-review不修 candidate。
