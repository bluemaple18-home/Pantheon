# REVIEW — CONTENT-P0-FAST-04M direct API observability repair

## Review boundary

- Baseline：`318604ee8304288d205ad0ec49dd0604f4eda57c`
- Candidate：`ee50dc62b2224f7047dec0e8ea3703b73fa46d37`
- Exact range：`318604ee8304288d205ad0ec49dd0604f4eda57c..ee50dc62b2224f7047dec0e8ea3703b73fa46d37`
- Diff SHA-256：`38910230424f6839957ae62cbf8fa32ddcb98b1b466ec9f8c68a288bf0055c13`
- Risk tier：`lite / standard`；只改 runner 的既有 closed projection seam 與 direct-path regression，沒有 provider、activation 或 production mutation。

請獨立檢查 exact diff 與測試，不要把本卡的 evidence summary 當成 verdict。

## Root cause

04L g84 production canary 使用 `credential_pool_direct_api`。該路徑在 `process_once()` 完成 JSON parse 與正式 schema validation 後，手動把 `SchemaDiagnostic` 降成 `keyword/path`，因此丟失 04K 已建立的 `type/char_count/value_sha256`。04K 的完整安全投影只接在未啟用的 V4 broker branch。

本 candidate 只讓 direct API post-validation branch 重用既有 `_closed_schema_diagnostics()`。它不新增觀測格式，也不改任何生成行為。

## User-required contract

對 Writer `minLength` failure，只允許 failed receipt 保存：

- `path`
- `keyword`
- `type`
- `char_count`
- `value_sha256`

禁止 raw title／description 或完整 provider payload。禁止改 prompt、schema、model、retry、repair budget、normalizer、Writer／Reviewer ownership。

## Changed files

- `scripts/agy_gemini_runner.py`
- `tests/test_agy_gemini_outbox.py`

## Required review questions

1. `_closed_schema_diagnostics()` 同時接受 V4 broker result 與 direct validator diagnostics tuple，是否仍對兩條路徑執行完全相同的 keyword、path、type、count、SHA fail-closed 過濾？
2. Direct API branch 是否只替既有 `SCHEMA_MISMATCH` receipt 增加安全 extension，沒有改 schema validation、normalization、failure classification 或 retry 控制流？
3. Synthetic direct-path test 是否真的經 `process_once()` 的非 V4 provider-result branch，並以 title 19／description 69 驗證實際 `char_count` 與 UTF-8 SHA-256？
4. Failed receipt 是否仍不含 raw title、raw description 或完整 provider payload？
5. `consume_external_response()` 是否仍只向 Writer repair 暴露既有 `(keyword, path)`，因此 prompt 與 Writer ownership 不變？
6. 既有 V4 04K safe-observation behavior 與 legacy diagnostics 是否保持相容？
7. 是否有任何 P0／P1，或需要在下一次 canary 前補的 deterministic regression？

## Evidence to reproduce

Baseline RED：

```text
.venv/bin/pytest tests/test_agy_gemini_outbox.py::test_runner_direct_api_persists_safe_schema_observations -q
1 failed：direct receipt 只有 keyword/path，缺 type/char_count/value_sha256
```

Candidate GREEN：

```text
tests/test_agy_gemini_outbox.py                   180 passed
tests/test_agy_gemini_runner.py +
tests/test_agy_gemini_v4_broker.py                54 passed
04L public-interface offline replay              GREEN
py_compile                                        PASS
git diff --check                                  PASS
```

Offline replay 額外確認：`fake_provider_calls=1`、title 與 description 兩個 diagnostics 的安全 extension 均存在、raw values absent。未呼叫 Gemini。

## Scope interpretation

- 這張卡只修 production transport 使用到的 observability seam。
- Review GO 不代表 production acceptance，也不代表已找到 Writer 為何產生過短 description。
- 下一步只有在本 candidate 通過 review 且 Owner 另行授權後，才能 promotion 並執行一個 fresh bounded canary。

## Verdict format

請輸出：

1. `GO | NO_GO | NEEDS_MORE_EVIDENCE`
2. P0／P1 findings；若無請明寫 `None`
3. P2／P3 findings
4. 逐題回答 Required review questions 1–7，附 source path／line或可重現 command
5. `why not less / why not more`
6. 是否可進 promotion／fresh bounded canary 邊界；不得把 review GO 說成 production acceptance

本 review 為 read-only。不得改檔、不得呼叫 provider、不得碰 production。
