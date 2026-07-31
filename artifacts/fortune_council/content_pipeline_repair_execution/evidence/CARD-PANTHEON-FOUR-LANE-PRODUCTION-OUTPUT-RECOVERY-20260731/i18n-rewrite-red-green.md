# i18n-rewrite deterministic evidence

## 身分與邊界

- card：`CARD-PANTHEON-FOUR-LANE-A4-MULTILINGUAL-CONTRACT-NATIVE-QUALITY-REPAIR-20260731`
- formal thread：`019fb5d8-3c6a-7c11-b507-a2f56c97a1ea`
- base：`de68b6b283493a3e9ca5f80286c682cb7846735e`

本 evidence 只證明 deterministic source／locale eligibility、candidate persistence
與 native-quality reviewer contract。沒有修改 Publisher／coordinator、呼叫
provider、套用 approval、發布 locale、deploy、reload 或 canary。

## Fixture coverage

### Source／locale eligibility

`test_legacy_rewrite_source_is_seeded_once_and_terminal_locale_stays_ineligible`
使用 legacy rewrite source identity 建立英、日、韓三個獨立 active locale run：

- 相同 source identity 重播時 run ID 與 brief 保持 idempotent；
- 已標記 `complete` 的 locale state 不被重設為 `active`；
- 不新增第四筆 state，不覆寫 terminal state bytes。

### Candidate／review

`test_i18n_rewrite_persists_candidate_and_preserves_native_quality_gate`
以三組 deterministic reviewer fixture 覆蓋：

| fixture | candidate | review |
|---|---|---|
| clean native fixture | persisted | `APPROVE`、無 findings |
| `NON_NATIVE_SEARCH_INTENT` | persisted | terminal `REJECT`、finding 保留 |
| `AI_TEMPLATE_STYLE` | persisted | terminal `REJECT`、finding 保留 |

三組都走 source→locale plan→translation/rewrite→candidate→review；拒絕組沒有
因 liveness 需求而刪除 finding、改成 approve 或繞過 Reviewer。

## Verification

```text
.venv/bin/pytest -q \
  tests/test_agy_multilingual_pipeline.py::test_i18n_rewrite_persists_candidate_and_preserves_native_quality_gate
```

結果：`3 passed`。

```text
.venv/bin/pytest -q \
  tests/test_agy_multilingual_pipeline.py::test_legacy_rewrite_source_is_seeded_once_and_terminal_locale_stays_ineligible
```

結果：`1 passed in 0.05s`。

```text
.venv/bin/pytest -q tests/test_agy_multilingual_pipeline.py
```

結果：`158 passed in 0.19s`。

## Acceptance mapping

| acceptance | evidence |
|---|---|
| eligible legacy source | 初次 seed 產生三個 locale states |
| already-terminal source | replay 不重啟 complete locale、不覆寫 state |
| candidate persistence | clean 與兩個 reject fixtures 都比對 root `candidate.json` |
| clean-approved path | clean fixture 為 `APPROVE` 且 findings 為空 |
| native-quality fail-closed | `NON_NATIVE_SEARCH_INTENT`／`AI_TEMPLATE_STYLE` 均維持 `REJECT` |
| 不跨 Publisher ownership | 沒有 apply、approval、registry、Publisher 或 coordinator 變更 |

## Remaining risk

本卡沒有聲稱 legacy translation 已發布，也沒有證明 production canary。真實
provider native quality、Publisher eligibility 與 locale release 仍需主線完成
runtime alignment、strict review，並取得 production mutation 授權後另行驗證。
