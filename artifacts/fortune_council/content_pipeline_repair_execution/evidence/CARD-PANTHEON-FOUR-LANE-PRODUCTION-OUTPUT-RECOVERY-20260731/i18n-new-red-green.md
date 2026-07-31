# i18n-new RED→GREEN evidence

## 身分與邊界

- card：`CARD-PANTHEON-FOUR-LANE-A4-MULTILINGUAL-CONTRACT-NATIVE-QUALITY-REPAIR-20260731`
- formal thread：`019fb5d8-3c6a-7c11-b507-a2f56c97a1ea`
- dispatch：`v1:9e18aeb21336d73cf4b919d19a5ef58ad4e98b0f24082e32ce8c769f2a502c63`
- base：`de68b6b283493a3e9ca5f80286c682cb7846735e`
- observation candidate：`63979fa6e7b2ea88011011f1655e269013e65662`

本次只使用 deterministic fixture 與既有 closed response 的封閉結構 metadata。
沒有保存 raw provider output、呼叫 provider、修改 production state、publish、
deploy、reload 或 canary。

## Root cause

既有 provider-facing locale-plan schema 對 `coverage_mapping` 只要求
`minItems: 1`，對 article array 只要求 1–5 筆；application hydration 則要求：

1. target count 與 brief 精確一致；
2. article slot 與 brief 次序一致；
3. 每個 source fact 恰好一筆 mapping；
4. mapping 次序與 source fact package 一致；
5. source hash、locale、safety boundary 與 native-language contract 不漂移。

觀察到的 closed response 有 5 筆 mapping，對應 brief 的 source fact package
有 22 筆。這證明 transport／broker response 成功不等於 application locale-plan
契約成立；舊 schema 允許 partial mapping 先被當成成功，再於 hydration 以泛用
`ValueError` 中止。

## Hypothesis disposition

| 假說 | 結果 | 證據 |
|---|---|---|
| provider transport／credential 是主因 | falsified | closed response 已成功，failure 發生在純記憶體 hydration |
| coverage count 是唯一問題，補齊 mapping 就能接受既有 response | falsified | 純記憶體補齊後仍命中 native locale language validation |
| 外部 schema 與內部 coverage invariant 不一致 | confirmed | schema 原本只要求至少 1 筆；validator 要求完整、有序且唯一 |

## RED

修改前依序執行：

```text
.venv/bin/pytest -q \
  tests/test_agy_multilingual_pipeline.py::test_locale_plan_rejects_coverage_mapping_order_drift
```

結果：`1 failed`，`Failed: DID NOT RAISE <class 'ValueError'>`。

```text
.venv/bin/pytest -q \
  tests/test_agy_multilingual_pipeline.py::test_external_locale_plan_schema_locks_current_brief_coverage
```

結果：`1 failed`，舊 `_external_locale_plan_schema()` 不接受 brief，無法將
target／source facts 寫入 provider-facing schema。

```text
.venv/bin/pytest -q \
  tests/test_agy_multilingual_pipeline.py::test_invalid_generated_plan_fails_before_article_candidate
```

結果：`1 failed`；真實 coverage failure 已重現，但 exception class 仍為泛用
`ValueError`，未形成 deterministic locale-plan 分類。

## GREEN

修復內容：

- provider-facing schema 由 validated brief 產生，鎖定 target count、slot、
  locale、source hash、source fact ID，以及 coverage min/max。
- hydration 對 article slot 順序與 coverage mapping 順序 fail-closed。
- missing、duplicate、order drift 都在 candidate 前拒絕。
- hydration failure 以 `LocalePlanValidationError` 分類；provider client 只呼叫
  一次，不進 semantic repair loop，也不誤歸 credential／transport。
- 合法 plan fixture 完成 plan→article→candidate→review，並保存 root 與
  attempt candidate。

精準 GREEN：

```text
.venv/bin/pytest -q \
  tests/test_agy_multilingual_pipeline.py::test_valid_locale_plan_reaches_candidate_persistence \
  tests/test_agy_multilingual_pipeline.py::test_locale_plan_rejects_incomplete_or_duplicate_coverage \
  tests/test_agy_multilingual_pipeline.py::test_i18n_rewrite_persists_candidate_and_preserves_native_quality_gate
```

結果：`6 passed in 0.07s`。

完整受影響測試：

```text
.venv/bin/pytest -q tests/test_agy_multilingual_pipeline.py
```

結果：`158 passed in 0.19s`。

## Acceptance mapping

| acceptance | evidence |
|---|---|
| coverage RED 可重現 | order drift、dynamic schema、classification 三個修改前 RED |
| 合法 fixture 可進 candidate | `test_valid_locale_plan_reaches_candidate_persistence` |
| 缺漏／重複／次序錯誤 fail-closed | coverage mutation 與 order tests |
| target count/order、source hash 未放寬 | dynamic schema 加嚴；hydration 保留並新增 order validation |
| deterministic failure 不誤分類 | `LocalePlanValidationError` 且 client call count 為 1 |
| 不冒充 production release | 未執行 provider、Publisher、publish 或 canary |

## Remaining risk

尚未在真實 provider structured-output 與 production actor 上驗證新 dynamic schema；
依卡片契約，該驗證必須等 runtime actor alignment、strict review GO 與另行授權。
