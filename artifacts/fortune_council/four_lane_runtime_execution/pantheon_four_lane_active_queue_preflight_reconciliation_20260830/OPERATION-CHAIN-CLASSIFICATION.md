# EN translation operation-chain classification

## Verdict

`EXPECTED_PLAN_TO_ARTICLE_TO_REVIEWER_LIFECYCLE / SECOND_WRITER_EXACTLY_ONCE_PENDING`

第二個 Writer job `9a8fa1c233a97f08d56a919d53903f7b34e3edab` 是 generation 01 的 article-generation operation，不是 role drift。live multilingual pipeline 的固定單 generation 順序是：

```text
Writer locale plan
  → hydrate/validate locale plan
  → Writer translated article candidate
  → deterministic findings
  → independent Reviewer
```

第一筆 Writer `61ca1a8d...` 已成功完成 locale plan；coordinator 重入同一 generation 後讀取既有 plan，再恰好 materialize 一筆 article Writer。第二筆成功並由下一次 coordinator consume 後，才會建立 Reviewer job。

## Exact envelope classification

兩筆 envelope 的 `operation_level` 都是通用的 `external_generation`，因此不能只靠該欄判 stage；stage authority 是 run-local operation receipt 的 prompt/schema digest binding。

| identity | first Writer | second Writer |
|---|---|---|
| job ID | `61ca1a8d150be47b23cfa6a0bf64f87649c5e321` | `9a8fa1c233a97f08d56a919d53903f7b34e3edab` |
| namespace | `f2324fee6f9d81fe4febbc6e` | `f2324fee6f9d81fe4febbc6e` |
| role / model | `writer` / `gemini-3.5-flash-lite` | `writer` / `gemini-3.5-flash-lite` |
| operation level | `external_generation` | `external_generation` |
| prompt SHA-256 | `10be0130b59edb574946501ebe71f6216f6f463dca65f41410db044e3f2ba435` | `a813c4a201a356916166acc7b10e749ee7d8571f7d1b76521c58e0a9c8992603` |
| schema SHA-256 | `27eae7d09a73e2df2c0bb6f2c3e08a07fb586fd188042d74712a216277be4fac` | `e2865950f5db19967ac320d7a197db6dd5627f6b5a56caefc3a9799e138f7740` |
| request SHA-256 | `61ca1a8d150be47b23cfa6a0bf64f87649c5e3219a31fb7e7e5d128404f9017c` | `9a8fa1c233a97f08d56a919d53903f7b34e3edab7e2ce38f096b95e339fbaa0f` |
| request raw file SHA-256 | `a009f512b1442b35b97aa05bb1748d12800f44be2f300234bb12fcaab5f80319` | `546018e5ee131bfffd778fbdefc095e7b0de789046eb79c0910bc4b08d15ca84` |
| lifecycle surface | archive + inbox + succeeded attempt | outbox only |

Digest binding：

- first envelope prompt/schema digest逐字等於 `attempts/01/plan-operation.json`；該 receipt 現為 `role=writer`、`status=success`。
- second envelope prompt/schema digest逐字等於 `attempts/01/article-operation.json`；該 receipt 現為 `role=writer`、`status=pending`、`error_type=ExternalJobPending`。
- 兩個 job ID 都是各自 request SHA 的前 40 hex；namespace 都等於 run ID `auto-i18n-en-aa637e1bf05d3ad21429` 的 SHA-256 前 24 hex。
- live `validate_external_request` 對第二 envelope PASS；沒有 request/job/namespace/model/role identity drift。

本卡沒有讀取或輸出 prompt、schema payload正文，只讀 identity/digest/role/model/status metadata。

## Generation and exactly-once evidence

這是 legacy flat run，所以 registry 的 `generation` 欄為 `null`；pipeline generation authority 是 run-local `attempts/01`：

- `planning-result.json`：`generation=1`、`transport_status=EXTERNAL_PLAN_AVAILABLE`、`planning_contract_status=PASS`。
- `external-plan.json` 與 `locale-plan.json` 都已存在。
- `plan-operation.json` 唯一且 success。
- `article-operation.json` 唯一且 pending；沒有 runtime-retry operation receipt。
- `external-candidate.json`、candidate、deterministic findings與 `reviewer-operation.json` 尚不存在，符合停在 article Writer transport boundary。
- lane `i18n-rewrite/outbox` 目前只有第二 job 一檔；該 job 的 processing/inbox/archive/failed/production-attempt 全不存在。
- registry仍 `active`，`last_job_id=9a8fa1c...edab`。

Exactly-once 不是只靠目錄計數：`create_external_request` 以 namespace/role/model/prompt/schema/transport-attempt 建 deterministic request/job ID；相同 request若已存在 outbox/processing/archive，會比對整份 request並直接重用，identity不同才 collision fail-closed。`_generate_with_receipt` 對 outbox transport 的 pending/success receipt重入同一 operation，而 `_load_or_generate_external` 在 output已存在時直接復用，不重生內容。

因此 current evidence支持「第二 article Writer恰好一次 pending」，不支持 unexpected duplicate。

## Actual live call chain

`scripts/agy_multilingual_pipeline.py::_run_fresh_writer_reviewer` 對 generation 1 呼叫 `_run_locale_generation`：

1. `_load_or_generate_external_locale_plan(..., plan-operation.json, external-plan.json)`，role固定 `writer`。
2. hydrate/validate plan，寫 `planning-result.json=PASS` 與 `locale-plan.json`。
3. `_load_or_generate_external(..., "writer", _article_prompt(...), _external_candidate_schema(), article-operation.json, external-candidate.json)`。
4. article response成功後 hydrate candidate並產 deterministic findings。
5. `_load_or_generate_external(..., "reviewer", _reviewer_prompt(...), external_review_schema(), reviewer-operation.json, external-review.json)`。

因 outbox transport 每次遇到未完成 external operation 會拋 `ExternalJobPending`，一次 coordinator tick只會 materialize目前第一個未完成 operation。第一筆 plan完成後，下一 tick自然停在第二筆 article Writer；Reviewer 不應在第二 Writer完成前出現。

## Historical successful translation receipt control

已完成 translation run `auto-i18n-ja-1414b75a404721e95e74` 的 `attempts/01` 保存同一序列：

1. `plan-operation.json`：Writer `gemini-3.5-flash-lite` success。
2. `article-operation.json`：Writer `gemini-3.5-flash-lite` success；article schema digest同樣是 `e2865950...f7740`。
3. `reviewer-operation.json`：Reviewer `gemini-3.1-flash-lite` success。

其 formal `runner-i18n-new-reviewer` receipt 又證明 exact run selector處理 Reviewer job後 child `status=processed`。這個已完成 lifecycle control 與 current EN 的 plan→article階段一致，排除 role drift。

## Pending external disclosure

第二 job 與第一 job不是同一目的資料類別：

- data category：以 validated locale plan、source fact references與 deterministic findings組成的 sanitized **translated article generation prompt**，加上 closed external candidate JSON schema；不包含 credential value。
- purpose：產生 EN translated article candidate，供本機 hydrate、deterministic validation與後續獨立 Reviewer使用。
- destination：formal i18n-rewrite Gemini runner所選 Writer route `gemini-3.5-flash-lite`；credential由既有 formal credential pool在 runner內取得，本命令與 receipt不輸出credential。

這是新的 provider disclosure operation，仍需覆蓋 article-generation payload類別的明確 production/provider授權；前一筆 locale-plan generation授權不能由本卡默示擴張。

## 唯一 exact pending command（本卡禁止執行）

Selector仍必須是 run ID，不是第二 job ID：

```sh
/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12 \
  -m scripts.agy_gemini_runner \
  --exact-run-id auto-i18n-en-aa637e1bf05d3ad21429 \
  operator-exact-process-once \
  --manifest /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json \
  --expected-digest 11fb6be90bc282add14a8a41cdb1258add550004049ce866a9bdf0d926aeaf04 \
  --barrier /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state/four-lane-activation-g73-f456a4d8-four-lane-legacy-brief-repair-20260830.barrier \
  --service-label com.pantheon.agy-gemini-i18n-rewrite \
  --ready-root /Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage/readiness/g73-f456a4d8-four-lane-legacy-brief-repair-20260830 \
  --plist /Users/mattkuo/Library/LaunchAgents/com.pantheon.agy-gemini-i18n-rewrite.plist \
  --timeout 300
```

Immediate expected postconditions：

- wrapper `executed/0`，child `processed` 且 `job_id=9a8fa1c...edab`；不得是 idle或其他 job。
- second outbox/processing消失；exactly one matching inbox、archive與 succeeded production-attempt形成，request SHA仍 `9a8fa1c...fbaa0f`。
- first job receipts保持 byte-stable；lane不得出現第二個 outbox job；KO/JA與其他 lane不變。
- run-local `article-operation.json` 要等下一次 exact coordinator consume 才從 pending轉 success；provider runner本身不寫 candidate或Reviewer job。

Subsequent coordinator-only expected postconditions（另一步、另行授權／執行）：

- consume second inbox，寫一份 `external-candidate.json`，hydrate candidate與 deterministic findings。
- materialize恰好一筆 Reviewer outbox，role=`reviewer`、model=`gemini-3.1-flash-lite`，並把 registry `last_job_id` 指向該 Reviewer。
- 在此之前不得宣稱 candidate reviewed、approved或publishable。

## Stop conditions

- second outbox raw SHA、request/prompt/schema digest、namespace、model/role任一漂移。
- second attempt/inbox/archive/processing/failed任一在執行前已存在；尤其 attempt存在即禁止重送。
- outbox出現第二檔、registry不再 active或 last_job不再是 second job。
- manifest/barrier/readiness不是 f456/g73，或 LaunchAgent意外 loaded。
- child idle、處理其他 job、回 nonzero，或一個 runner call形成多於一筆 attempt。
- coordinator consume後不是 Reviewer而是另一筆同 generation article Writer，或 Reviewer role/model不符合 route；此時改判 role/lifecycle drift並 STOP。

## Status

- classification：`EXPECTED_PLAN_TO_ARTICLE_TO_REVIEWER_LIFECYCLE`
- second Writer exactly once：PASS／pending
- role drift：否
- payload正文 read/output：`0`
- provider call：`0`
- production mutation：`0`
- pending command executed：`false`
- next status：`RE_REVIEW_REQUESTED`
