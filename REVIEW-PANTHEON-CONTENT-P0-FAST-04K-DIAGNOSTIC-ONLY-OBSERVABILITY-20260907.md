# REVIEW — CONTENT-P0-FAST-04K diagnostic-only observability

## Review boundary

- Baseline：`42198e9260ec9487ea3634a1b91b32dbd90e1eb1`
- Candidate：`5e444d958faf86cff160a1ba77529b96f081ce7b`
- Exact range：`42198e9260ec9487ea3634a1b91b32dbd90e1eb1..5e444d958faf86cff160a1ba77529b96f081ce7b`
- Risk tier：lite；跨 V4 broker、runner failed receipt、outbox closed contract，但沒有 activation、provider 或 production mutation。

請先獨立檢查 exact diff 與測試，不要把本卡的 evidence summary 當成 verdict。

## Root question

Candidate 是否只增加安全且足以定位 Writer `minLength` failure 的 metadata，並維持既有 schema validation、failure classification、repair prompt、retry 與隱私邊界完全不變？

## User-required contract

對 JSON 已解析後的 Writer `minLength` failure，只允許保存：

- `path`
- `keyword`
- `type`
- `char_count`
- `value_sha256`

禁止保存 raw title／description 或完整 provider payload。禁止 provider call、production mutation、prompt/schema/model/retry/repair-budget/normalizer 變更。

## Changed files

- `CARD-PANTHEON-CONTENT-P0-FAST-04K-DIAGNOSTIC-ONLY-OBSERVABILITY-20260907.md`
- `scripts/agy_gemini_v4_broker.py`
- `scripts/agy_gemini_runner.py`
- `scripts/agy_gemini_outbox.py`
- `tests/test_agy_gemini_v4_broker.py`
- `tests/test_agy_gemini_outbox.py`

## Required review questions

1. `SchemaDiagnostic` 是否從 validator 使用的同一個字串值，以相同 Python `len()` 產生 `char_count`，並以 UTF-8 bytes 產生 SHA-256？
2. metadata 是否只附加於字串 `minLength`，且 runner 對 type、count bound、SHA shape 與 closed schema path 做 fail-closed 過濾？
3. failed receipt 與任何 normalized trace 是否可能洩漏 raw title／description、完整 payload 或其他未允許欄位？
4. outbox 是否保持舊版只有 `keyword/path` receipt 的相容性，同時只接受完整的三欄 observation extension；malformed／partial extension 是否 fail closed？
5. outbox 傳入 `ExternalWriterSchemaInvalid.schema_diagnostics` 的內容是否仍只有既有 `(keyword, path)`，因此 repair prompt 與控制流不變？
6. synthetic RED／GREEN 是否真的打到 V4 `json.loads()` 後的 schema-validation seam：19／69 應失敗，20／70 應通過；測試是否避免只測 private helper？
7. diff 是否意外改到 prompt、schema、model route、retry、repair budget、normalizer、Writer／Reviewer ownership或 production path？

## Evidence to reproduce

RED 曾以以下 command 因安全 metadata 尚不存在而失敗：

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_v4_broker.py::test_single_shot_records_safe_length_observability_at_exact_boundary
```

Candidate 上：

```text
上述 boundary test                         1 passed
V4 boundary＋runner/outbox targeted        2 passed
test_agy_gemini_v4_broker.py + outbox.py  222 passed
test_agy_gemini_runner.py + pipeline.py   182 passed
py_compile                                PASS
git diff --check                          PASS
```

## Scope interpretation

- 這張卡只能證明安全觀測能力；不能證明 production 根因、發文修復或上線 readiness。
- 19／69 是 synthetic one-below-boundary fixture，不代表 production 實際只差一字。
- 此 diff 未呼叫 Gemini、未執行 live attempt、未 promotion。

## Verdict format

請輸出：

1. `GO | NO_GO | NEEDS_MORE_EVIDENCE`
2. P0／P1 findings；若無請明寫 `None`
3. P2／P3 findings
4. 逐題回答 Required review questions 1–7，附 source path／line 或可重現 command
5. `why not less / why not more`
6. 是否可進下一個 commit/push 邊界；不得把 review GO 說成 production acceptance

本 review 為 read-only。不得改檔、不得呼叫 provider、不得碰 production。
