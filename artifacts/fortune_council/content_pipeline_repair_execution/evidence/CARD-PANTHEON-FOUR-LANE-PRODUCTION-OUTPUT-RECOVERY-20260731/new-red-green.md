# A2 new output contract RED / GREEN

- Card: `CARD-PANTHEON-FOUR-LANE-A2-NEW-CONTRACT-REPAIR-20260731`
- Base: `de68b6b283493a3e9ca5f80286c682cb7846735e`
- Observation: `63979fa6e7b2ea88011011f1655e269013e65662`
- Scope: `new/create` external candidate 的 description `minLength` 與 paragraph `maxLength`

## RED

指令：

```bash
.venv/bin/pytest -q \
  tests/test_agy_gemini_outbox.py::test_runner_normalizes_new_description_and_paragraph_bounds_without_retry \
  tests/test_agy_gemini_v4_broker.py::test_single_shot_delivers_only_revalidated_normalized_result
```

修改 production code 前結果：`2 failed`。

- runner 收到 provider success 但 description 69 字、paragraph 超過 160 字時，回傳
  `V4BrokerFailure`，未產生 inbox candidate。
- broker 不接受 `result_normalizer`，schema-invalid payload 無法在單次 process 內封閉修復。

## GREEN

同一指令結果：`2 passed in 0.62s`。

新增 production-slot deterministic fixture：

```bash
.venv/bin/pytest -q \
  tests/test_agy_gemini_outbox.py::test_runner_normalizes_new_description_and_paragraph_bounds_without_retry \
  tests/test_agy_gemini_outbox.py::test_production_normalizes_new_output_with_one_credential_slot \
  tests/test_agy_gemini_v4_broker.py::test_single_shot_delivers_only_revalidated_normalized_result
```

結果：`3 passed in 0.56s`。

## Contract evidence

- normalization 只在 response schema 精確等於既有 `external_candidate_schema("create")`
  時啟用；schema 的 70–95、80–160、每節 2–4 段均未修改。
- 短 description 只追加完整的通用限制句，修後仍以原 schema 重驗。
- 超長 paragraph 以原 2–4 段容量重新分段，保留全文字串順序與內容；容量不足時
  回傳 `None`，維持 fail-closed。
- 每份 provider result 最多執行一次 deterministic normalization，再用原 schema
  驗證；沒有 retry loop。
- production fixture 只建立一個 provider client、呼叫一次 provider，並只使用
  `account-2` 一個已配置 slot；沒有跨帳號輪替或新 run。
- 完成後再次執行 queue tick 為 `idle`，provider 未重播。
- 非目標 schema mismatch 仍分類為 `SCHEMA_INVALID_PAYLOAD`，保留 bounded
  `schema_diagnostics`，且失敗路徑不保存 raw provider output。
- V4 broker 的 normalized success 只交付重新序列化且通過原 schema 的 result；
  target process 次數仍為 1。

## Regression

指令：

```bash
.venv/bin/pytest -q \
  tests/test_agy_seo_copy_pipeline.py \
  tests/test_agy_gemini_outbox.py \
  tests/test_agy_gemini_v4_broker.py
```

結果：`309 passed in 67.90s`。

`git diff --check`：通過，無輸出。

## Boundaries

- 未呼叫真實 Gemini/provider。
- 未執行 production canary、queue/ledger/candidate mutation、publish、deploy、reload
  或 push。
- 未放寬 schema、reviewer contract、禁詞或品質 gate。
