---
id: CONTENT-P0-FAST-04K-DIAGNOSTIC-ONLY-OBSERVABILITY-20260907
type: bounded-diagnostic-repair
status: offline_evidence_complete
baseline_commit: 42198e9260ec9487ea3634a1b91b32dbd90e1eb1
---

# CONTENT-P0-FAST-04K — Writer schema failure 安全觀測

## Objective

在既有 V4 broker Writer JSON schema-validation failure seam，留下足以判定 title／description 實際字數的安全 metadata。只補證據，不改內容生成或驗收行為。

## Measured gap

g82／g83 六次 production Writer response 都在 transport success、JSON 可解析後，被判定為 `articles[0].title:minLength` 與 `articles[0].description:minLength`；現有 receipt 只有 `path`／`keyword`，沒有實際長度，因此無法區分有效輸出真的過短與 validator／transformation 問題。

## Scope

- 在 JSON 已解析且 schema diagnostics 已產生的既有 seam，對可安全解析的字串 `minLength` 錯誤只記：`path`、`keyword`、`type`、`char_count`、`value_sha256`。
- 沿用既有 broker diagnostic 與 failed receipt；不得新增 log、ledger、registry 或 runtime。
- 以 synthetic fixture／offline replay 建立單一 RED→GREEN feedback loop。

## Forbidden

- 禁止保存 raw title、raw description 或完整 provider payload。
- 禁止 provider call、production mutation、promotion、canary 或第 4 次 live attempt。
- 禁止修改 prompt、schema、門檻、model route、retry、repair budget、normalizer、Writer／Reviewer ownership。
- 禁止 padding、放寬 schema、換模型或新增 fallback。

## Acceptance

1. 完整 synthetic Writer candidate 的 title=19、description=69 時，offline V4 seam 穩定回傳兩筆 `minLength`，metadata 的 `char_count` 分別為 19、69，且 `value_sha256` 可由 fixture UTF-8 內容重算。
2. title=20、description=70 的 control 通過同一 schema boundary。
3. broker result 到 runner failed receipt 的序列化內容不含 raw title／description；outbox failure classification 與 repair diagnostics 的既有 `path`／`keyword` 行為不變。
4. RED 必須因上述安全 metadata 尚未存在而失敗；GREEN 後重跑相同 command 通過。
5. 受影響測試、`py_compile`、`git diff --check` 通過，且不存在 `[DBG-` 殘留。

## Expected files

- `scripts/agy_gemini_v4_broker.py`
- `scripts/agy_gemini_runner.py`
- `scripts/agy_gemini_outbox.py`
- 上述模組的對應測試

## Hypothesis split

- 若觀測到 `char_count` 低於 effective minimum：有效 parsed output 確實過短；後續另卡研究模型／CLI／structured-output。
- 若 `char_count` 已達 minimum 仍回 `minLength`：優先查 validator。
- 若 offline 無法重現 production diagnostic shape：優先查 executable generation／execution contract。

## Evidence contract

- RED／GREEN command 與輸出寫入本卡 task history 或同卡 evidence。
- 本卡只證明觀測能力，不宣稱發文鏈已修復或可上線。

## Task history

- RED：`.venv/bin/python -m pytest -q tests/test_agy_gemini_v4_broker.py::test_single_shot_records_safe_length_observability_at_exact_boundary` → `1 failed`；failure 為 `SchemaDiagnostic` 尚無安全長度 metadata。
- GREEN：相同 command → `1 passed`。
- Receipt propagation RED：runner failed receipt 只有 `keyword`／`path`，缺少預期安全 metadata；實作後測試併回既有 closed-diagnostics regression，避免保留重複 setup。
- Targeted：V4 boundary 與 runner／outbox closed receipt 共 `2 passed`。
- 受影響 suites：broker＋outbox `222 passed`；runner＋SEO pipeline `182 passed`。
- `py_compile`：PASS；`git diff --check`：PASS；受影響檔案無 `[DBG-` 殘留。

## Offline result

- title=19、description=69：各自穩定產生 `minLength`，receipt 可見 `char_count` 19／69 與可重算的 UTF-8 SHA-256。
- title=20、description=70：同一 boundary 為 `VALID`。
- failed receipt 不含 synthetic raw title／description；outbox 仍只把既有 `keyword`／`path` 傳入 Writer schema repair。
- 此結果未重現簡單的 validator off-by-one；production 實際長度仍未知，必須等未來經審查與 promotion 後的新 canary 才能分流。

## Explicit non-actions

- 未呼叫 Gemini、未碰 production、未執行 live attempt。
- 未修改 prompt、schema、model route、retry、repair budget 或 normalizer。
- 未 commit、未 push、未 promotion。
