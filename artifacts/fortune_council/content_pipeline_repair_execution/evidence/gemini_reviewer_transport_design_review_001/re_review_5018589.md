# Gemini Reviewer transport design 001｜Fixed-candidate re-review

## Findings

未發現阻塞問題。

## Fixed scope

- Review chain: `CONTENT-GEMINI-REVIEWER-TRANSPORT-DESIGN-001`
- Original base candidate: `d15df4b1e892f3b9854f42dc067d89af7ee37cd3`
- Repair source parent: `05adf93b4843d3b4c0149e1c24e0e59d335a7bae`
- Reviewed fixed candidate: `5018589dd014e4c3edf5c6a3d736d912957ec400`
- Repair thread: `019f8262-09d5-7ec3-9438-b1841777990a`
- Reviewer 未呼叫 Gemini CLI、未修改 candidate；只新增本 re-review evidence。

## Original finding closure

1. `RESOLVED` — duplicate JSON keys（含巢狀）fail closed。
   - Code：`scripts/agy_gemini_transport_probe.py:175-203` 使用 pairs-level `object_pairs_hook`，任一 object depth 出現 duplicate key 都回 `STRICT_JSON_DUPLICATE_KEY`，且 `strict_parse=false`。
   - Evidence：15-test suite 覆蓋 top-level verdict 與 nested finding code；Reviewer 額外以 nested duplicate message 重驗，同樣 fail closed。

2. `RESOLVED` — APPROVE interface 與 cross-field contradictions。
   - Code：`scripts/agy_gemini_transport_probe.py:56-65` 允許 `findings=[]`；`scripts/agy_gemini_transport_probe.py:150-166` 只接受 `APPROVE + false + []` 或 `REJECT + true + non-empty`。
   - Evidence：合法 APPROVE parse/schema/rubric 全通過；四種矛盾組合均以 `RUBRIC_FAILURE` 拒絕。

3. `RESOLVED` — observable-only invocation accounting。
   - Code：`scripts/agy_gemini_transport_probe.py:309-339` 固定 2 corpora × 3 external processes，輸出 `external_cli_process_invocations=6`、`external_cli_process_budget=6`、`provider_model_calls=unobservable/unknown`。
   - Evidence：repair `matrix.json` 精確 6 rows，各 configuration attempts 為 1/2/3，沒有 `model_calls` 或 `call_budget` key；current strategy 與 repair evidence 均禁止從外部 process 推導 provider request/retry 次數。

4. `RESOLVED` — finding code/message trim 後必須非空。
   - Code：`scripts/agy_gemini_transport_probe.py:45-53` 對 message 設 `minLength=1`；`scripts/agy_gemini_transport_probe.py:150-159` 對 code/message 執行 trim 後非空 rubric。
   - Evidence：empty message 由 schema 拒絕、純空白 message 由 rubric 拒絕、空白 code 由 allowlisted enum/schema 拒絕。

## Spec axis

`PASS`。四個固定 finding 全部有 deterministic code、負向測試與本 Reviewer 的離線重驗支持。Repair artifacts 只宣稱可觀測的六個 external CLI process invocations，provider model calls 明確為不可觀測；GO 邊界沒有擴張為 production recovery。

## Standards axis

`PASS`。Parser、structural schema、cross-field rubric、mapper 與 accounting 責任分離；15 tests、`py_compile`、matrix recomputation、privacy scan、allowlist 與 `git diff --check` 均通過。未發現 P0/P1 或阻塞 implementation 的 P2。

## Verdict

`GO`

此 GO 只表示 fixed candidate 可通過本 architecture review，得進入後續 implementation/corpus gate；不代表 production pipeline 已修復，不授權 merge、push、deploy、publish，亦不恢復三條內容線。

## Verification evidence

- Reviewer preflight：PASS；初始 worktree clean，初始 `HEAD=05adf93b4843d3b4c0149e1c24e0e59d335a7bae`。
- Detached review：PASS；所有 code/test/evidence 檢查期間 `HEAD=5018589dd014e4c3edf5c6a3d736d912957ec400`，tree clean。
- Scope：完整比較 `d15df4b1e892f3b9854f42dc067d89af7ee37cd3..5018589dd014e4c3edf5c6a3d736d912957ec400`；Repair ownership 以 `05adf93b4843d3b4c0149e1c24e0e59d335a7bae..5018589dd014e4c3edf5c6a3d736d912957ec400` 驗證。
- `py_compile scripts/agy_gemini_transport_probe.py`：PASS（pycache 導向暫存區）。
- `pytest -q -p no:cacheprovider tests/test_agy_gemini_transport_probe.py`：PASS，`15 passed in 0.02s`。
- Matrix recomputation：PASS；6 rows、兩組各 3 rows、attempts 1/2/3、summary 與 decision 重算一致；config/request hashes 均可由 candidate code 重算。
- Receipt boundary：PASS；無 unexpected top/run keys，無 prompt/raw response/stdout/stderr payload keys；只保存 hash、byte count 與 typed gates。
- Accounting：PASS；`external_cli_process_invocations=6`、budget 6、`provider_model_calls=unobservable/unknown`，無 legacy accounting keys。
- Repair changed-file allowlist：PASS；4 個 repair evidence files、策略文件、probe、probe tests，共 7 個檔案。
- Secret/PII/absolute-local-path scan：PASS。
- `git diff --check`：base-to-candidate 與 repair-parent-to-candidate 均 PASS。
- Gemini CLI invocation：未執行；本卡只重審已封裝 receipts 與 deterministic code。

## Remaining risks

- Corpus 仍只有一個短 REJECT 與一個短 APPROVE sanitized case；尚未涵蓋長內容、多文章、混合 policy code 或 production payload。
- CLI binary、server-side routing 與模型行為可能更新；implementation/release gate 必須重新驗證 capability fingerprint。
- Provider 內部 model calls、silent retry、multi-call 與精確成本仍不可由外層 CLI receipts 觀測，後續不得重新宣稱其上限。
- 原 design evidence 作為歷史稽核紀錄仍保留舊 accounting 名稱；current strategy、repair decision/red-green 與本 re-review 已明確將其標示為舊命名並以 observable-only accounting 取代。下游必須以最新 chain evidence 判讀。
- 3/3 小樣本不構成 production SLO；production 三條內容線維持停止，直到獨立 implementation/corpus/release gates 全數通過。
