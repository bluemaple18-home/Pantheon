# f456/g73 EN Writer exact runner operator RCA

## 單一裁決

`OPERATOR_SELECTOR_MISMATCH`

`agy_gemini_runner --exact-run-id` 的實際語意是 **pipeline run ID**，不是 job ID，也不是 request SHA。先前 command 傳入 `61ca1a8d150be47b23cfa6a0bf64f87649c5e321`（job ID）；它符合 CLI 的一般字元格式，所以 wrapper 不會 rejected，但 child 會把它當成 run ID 再做 SHA-256、取前 24 hex 作為 namespace selector。算出的 namespace 是 `c43bf61408a023b8de53f805`，與 exact outbox envelope 的 `f2324fee6f9d81fe4febbc6e` 不同，故 `_peek_next_model` 找不到 candidate，按設計回 `{"status":"idle"}`；child return code 與 wrapper return code 都是 `0`，outbox 完全不 claim。

正確 selector 是 registry run ID `auto-i18n-en-aa637e1bf05d3ad21429`。它的 SHA-256 前 24 hex 正是 `f2324fee6f9d81fe4febbc6e`。

## Current immutable evidence

- runtime actor：`f456a4d8c21ce0a237254d31e6662339a1d522fb`
- generation：`g73-f456a4d8-four-lane-legacy-brief-repair-20260830`
- manifest digest：`11fb6be90bc282add14a8a41cdb1258add550004049ce866a9bdf0d926aeaf04`
- registry：`f2324fee6f9d81fe4febbc6e.json`，`status=active`、`lane=i18n-rewrite`、`last_job_id=61ca1a8d150be47b23cfa6a0bf64f87649c5e321`。
- exact lane outbox 只有一檔；raw SHA-256：`a009f512b1442b35b97aa05bb1748d12800f44be2f300234bb12fcaab5f80319`。
- exact `processing/inbox/archive/failed` 全不存在；exact production attempt marker 不存在。
- coordinator 與 i18n-rewrite LaunchAgent 均未 loaded。

先前 execution receipt 的 wrapper/child observation 與 code 完全一致：wrapper `status=executed, returncode=0`，child summary `status=idle`；job 仍只在 outbox，沒有 processing/inbox/archive/attempt。

## Selector code path 與 isolated RED

Actual live actor：

1. `scripts/agy_gemini_runner.py:144-164::_normalize_exact_run_ids` 只驗 selector 字串格式，無法知道呼叫者傳的是 job ID。
2. `scripts/agy_gemini_runner.py:757-789::_claim_next` 與 `:809-842::_peek_next_model` 對每個 `exact_run_id` 計算 `sha256(run_id)[:24]`，再比對 request `namespace`。
3. `scripts/agy_gemini_runner.py:543-620::operator_exact_process_once` 把 outer selector原樣傳給 child `process-once`。
4. `process_once` 找不到 matching model 時回 `idle`；CLI 只有 `status=failed` 才回 nonzero。因此 idle/0 是 fail-safe no-claim，不是 wrapper 成功處理 job 的證據。

已執行 isolated temp-root probe：只讀複製 exact outbox envelope，不載 credential、不呼叫 provider。

```json
{
  "correct_run_id_selector_model": "gemini-3.5-flash-lite",
  "envelope_valid": true,
  "expected_run_namespace": "f2324fee6f9d81fe4febbc6e",
  "fixture_sha256": "a009f512b1442b35b97aa05bb1748d12800f44be2f300234bb12fcaab5f80319",
  "job_selector_namespace": "c43bf61408a023b8de53f805",
  "namespace": "f2324fee6f9d81fe4febbc6e",
  "wrong_job_id_selector_model": null
}
```

這是本 RCA 的 red-capable signal：錯 selector 必須回 `null/idle` 且 temp outbox 不動；正確 run selector 必須選出 envelope model。

Existing tests 同樣鎖定語意：`tests/test_agy_gemini_runner.py::test_runner_exact_run_ids_claims_only_matching_namespace` 傳 `target-ko-run`，以它的 SHA namespace 選到不同 job ID；`test_runner_exact_run_ids_missing_target_does_not_claim_fallback` 證明缺少 run selector只回 idle、不 claim 其他 job。

Previous successful formal receipt `pantheon_acceptance_b_gen06_production_retry_20260828/runner-i18n-new-reviewer.*` 也以 run ID `auto-i18n-ja-1414b75a404721e95e74` 呼叫 `operator-exact-process-once`，child summary 成功處理另一個 job ID `735ffd07d47e4b25d49f85f137d9dd238d8e9967`。這直接反證「CLI 要 job ID」。

## Lane、service、role、model 與 filter 對帳

| edge | observed | verdict |
|---|---|---|
| queue lane | `i18n-rewrite` | MATCH |
| service label / plist label | `com.pantheon.agy-gemini-i18n-rewrite` | MATCH；不需換 label/plist |
| envelope namespace | `f2324fee6f9d81fe4febbc6e` | MATCH correct run ID |
| role | `writer` | MATCH |
| envelope model | `gemini-3.5-flash-lite` | MATCH plist `AGY_WRITER_MODEL` 與 route primary |
| reviewer model | `gemini-3.1-flash-lite` | distinct、非本次 selector |
| `AGY_GEMINI_NEW_ONLY` | `0` | 不會 disable i18n-rewrite |
| model route semantic digest | `1ed24743202ff953bf32d07d570602e61c77194df45889cabc93b13495945e0e` | MATCH plist expected digest |
| model route file raw SHA-256 | `493c09ce9dc1ddf5007387d7cb66be2ec88dba4acd5c24d3a19106afd3e6dd75` | file identity stable |

Plist 的 stored ProgramArguments／runtime generation 仍是舊 g47，但不是本次失敗邊：operator code不執行 plist ProgramArguments；它用 current manifest 建 child command，並在 plist environment 之後用 `_manifest_environment` 覆寫 runtime generation、actor root、queue root、service label等 identity。既有 operator unit test也刻意放入 `stale-generation`／`stale-python`，斷言 child 使用 current manifest。Plist 在這條 seam 只提供 formal transport/model-route environment；其 label、lane filter、Writer model與 route digest皆對上。

Exact envelope 已通過 live `validate_external_request`；job ID、request SHA、prompt SHA、schema SHA、namespace、role/model均沒有 identity drift。因此排除 `FORMAL_ROUTE_MISMATCH`、`JOB_IDENTITY_DRIFT` 與 `CODE_SEAM`。

## 唯一正確 pending command（禁止本卡執行）

與先前 command 相比，只能改 selector 為 **run ID**；service label/plist保持 i18n-rewrite：

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

這是一條 provider mutation command，仍需主線既有明確授權；本 RCA 沒有執行。

## 防止重複外傳的強制前置證據

命令執行前必須在同一個 bounded snapshot 再次全部成立；任一不成立即停：

1. manifest仍是 f456/g73，digest仍是 `11fb6be...f04`，barrier/readiness identity一致。
2. registry仍 `active`，`run_id=auto-i18n-en-aa637e1bf05d3ad21429`、`lane=i18n-rewrite`、`last_job_id=61ca1a8d...e321`。
3. lane outbox只有這一檔，raw SHA仍 `a009f512...f80319`；live validator PASS，namespace仍是 run ID SHA 前 24 hex。
4. exact processing/inbox/archive/failed全部不存在。
5. exact `production-attempts/61ca1a8d...e321.attempt` 不存在。這是 at-most-once 的核心 stop edge；存在時禁止重送，即使 outbox仍存在。
6. `AGY_GEMINI_NEW_ONLY=0`，Writer model／route semantic digest仍與 envelope相符。
7. Gemini/coordinator LaunchAgents仍未 loaded，避免背景 consumer 與 operator race。

執行後必須立即停止，不得自動再跑；先唯讀對帳 wrapper child summary 必須是 exact job `61ca1a8d...e321`、outbox消失、processing歸零、且 exactly one attempt/inbox/archive形成。任何 idle、blocked、failed 或 job identity不同都禁止第二次呼叫。

## Status

- root cause：`OPERATOR_SELECTOR_MISMATCH`
- isolated selector probe：PASS
- job envelope identity：PASS／無 drift
- formal route：PASS
- provider call：`0`
- production mutation：`0`
- correct pending command executed：`false`
- next status：`RE_REVIEW_REQUESTED`
