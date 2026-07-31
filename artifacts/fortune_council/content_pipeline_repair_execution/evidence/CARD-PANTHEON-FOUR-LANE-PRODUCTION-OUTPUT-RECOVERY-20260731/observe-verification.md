# SLICE-OBSERVE-001 驗證紀錄

## Scope receipt

- 執行範圍：diagnostic observe only。
- production code／tests／fixture／schema：未修改。
- production provider call：未執行。
- queue／ledger／candidate／archive／`.work`：未刪除、未重置、未手改。
- deploy／reload／publish／push／canary：未執行。
- tracked output：只允許本 evidence 目錄三份 Markdown。

## Worktree 與 capability

執行：

```text
git rev-parse --is-inside-work-tree
git rev-parse HEAD
git status --porcelain=v1 --untracked-files=all
bash <ai-core>/scripts/worktree_capability_preflight.sh \
  --prepare --with-codegraph --root <repo-root>
```

結果：

- worktree：registered、provisioning ready
- HEAD：`de68b6b283493a3e9ca5f80286c682cb7846735e`
- initial state：clean
- CodeGraph：ready，indexed SHA 與 HEAD 相同
- dependency preparation：
  - `uv_sync_failed`：sandbox 不允許共用 uv cache
  - `pnpm_install_failed`：registry DNS `ENOTFOUND`
  - CodeGraph initialization／indexing仍完成

## CodeGraph query

### Query 1 — task context

```text
診斷 new、rewrite、i18n-new、i18n-rewrite 四條內容 lane 從
input selection、Gemini broker/provider output、schema/quality gate、
candidate persistence 到 Publisher/release verification 的成功與失敗邊界；
只做唯讀觀察，不修改 production code。
```

結果定位：

- `scripts/agy_gemini_v4_broker.py::BrokerResult`
- `scripts/agy_gemini_v4_broker.py::run_single_shot`
- `scripts/agy_gemini_runner.py::process_once`
- `scripts/agy_content_publisher.py::PublishBlocked`
- `scripts/agy_content_publisher.py::PolicyRejected`

### Query 2 — related source

```text
run_single_shot BrokerResult PublishBlocked PolicyRejected
agy_gemini_runner.py agy_gemini_coordinator.py agy_seo_copy_pipeline.py
agy_multilingual_pipeline.py agy_content_publisher.py
```

結果確認：

- runner 只在 caller contract 成立後把 response 寫入 inbox。
- broker mismatch 只保存封閉 `result_validation`／schema diagnostics，
  不保存 raw provider payload。
- Publisher policy rejection 是 terminal content state，不是 transport failure。
- coordinator `process_once`、lane selection、Publisher retry 是本 failure matrix
  的 public/observable seams。

### Specific symbol confirmation

- `run_pipeline_tick`：
  - translate run 路由至 `multilingual.run_writer_reviewer`
  - 其他 run 路由至 `pipeline.run_writer_reviewer`
- `_advance`：
  - `ExternalJobFailed` 保存 job/error metadata
  - 其他 deterministic exception 只保存 `error_type`
- `validate_translation_candidate`：
  - translation identity、target count、order、source hash 與 fields 都 fail-closed
- `_hydrate_locale_plan`／`validate_locale_plan`：
  - coverage mapping 必須與 source fact package 一一對應

CodeGraph 查詢有結果，因此沒有先以 `rg` 取代 graph。後續 `rg`／`sed`
只用於確認 graph 指出的 source seam 與找 runtime locator。

## 唯讀 runtime query

實際使用的 query 類型：

```text
PlistBuddy Print :WorkingDirectory / :ProgramArguments / log paths
launchctl print gui/<uid>/<label> | filter state/pid/runs/last-exit/program/path
git -C <publisher-actor-root> rev-parse HEAD
git -C <publisher-actor-root> rev-parse origin/main
git -C <publisher-actor-root> status --porcelain
runtime_manifest_digest(<publisher-actor-root>)
tail（六個 actor 的封閉 stdout／stderr）
find/stat（lane queue count 與 mtime）
jq（run state、closed failed diagnostic、review verdict/finding code、Publisher ledger）
```

沒有執行：

- `agy_gemini_runner process-once`
- `agy_gemini_coordinator cycle`
- Publisher non-dry-run／dry-run transaction
- installer、`launchctl bootstrap/bootout/kickstart`
- Git fetch／push

背景 LaunchAgent 在觀察窗仍可能自行更新 production artifacts；本 task 沒有
停止或觸發它們。所有基線因此保留 observation timestamp，不把單次 count
當永久 truth。

## Red-capable failure

### i18n-new locale-plan hydration

以 production actor code、既有 closed inbox response 與既有 brief 執行純記憶體
hydration；未寫入 run directory，未呼叫 provider：

```text
<publisher-actor-python> -c '
  load brief;
  load closed inbox["result"];
  _hydrate_locale_plan(
      brief,
      external,
      generation=1,
      rebuild_by_slot=_rebuild_authority(brief, []),
      prior_plan=None,
  )
'
```

結果：exit 1。

```text
ValueError: locale plan coverage mapping differs for article-01
```

這是後續修復可重跑的 RED seam。它重現 production state 的 `ValueError`，
不是 import error、fixture failure、credential failure或 provider timeout。

### new closed schema diagnostic guard

production fresh evidence：

- observation range：v0.3.183 publish 後
- failure records：52
- provider outcome SUCCESS：52
- `SCHEMA_MISMATCH`：52
- `SCHEMA_INVALID_PAYLOAD`：52

另以 production actor 既有 fixture 執行：

```text
.venv/bin/pytest -q \
  tests/test_agy_gemini_outbox.py::test_runner_persists_only_closed_schema_diagnostics
```

結果：`1 passed`。這是 closed-diagnostic regression guard，不是 GREEN 修復證明；
production symptom 仍為 RED。

### rewrite release gate

五筆 retry artifact 保存同一 red-capable release command：

```text
<publisher-actor-python> -m pytest \
  tests/test_web.py \
  tests/test_agy_seo_copy_pipeline.py \
  tests/test_agy_multilingual_pipeline.py \
  tests/test_release_record.py -q
```

每筆最後狀態：

- return code：1
- attempts：3／3
- candidate preserved：true
- eligibility：exhausted

本 observe slice 未在 production transaction 重跑，因為那會超出唯讀觀察與
retry ownership；既有三次執行 artifact 已提供 red-capable command。

### i18n-rewrite quality gate

root review 只讀 query：

```text
verdict=REJECT
finding_codes=[NON_NATIVE_SEARCH_INTENT, AI_TEMPLATE_STYLE]
```

Publisher ledger：

```text
reason=translation reviewer did not cleanly approve
legacy translation published count=0
```

這是預期 fail-closed，不能把放寬品質 gate 當成修復。

## Hypothesis disposition

| 假說 | 結果 | 證據 |
|---|---|---|
| 四 lane 主要是 credential/auth outage | falsified | new fresh 52 筆 provider outcome 全 SUCCESS；i18n fresh response 也成功進 inbox |
| 累積 queue count 代表 eligible backlog | falsified | 四 lane outbox/processing 近零；rewrite 179 unattempted 被 selector/retry gate 擋住 |
| rewrite 沒 candidate 可發布 | falsified | 5 clean approve、candidate preserved；真正 blocker 是 exhausted retry |
| i18n-new 在 provider transport 失敗 | falsified | closed response 成功；純 hydration 重現 coverage mapping ValueError |
| i18n-rewrite 已 productive release | falsified | candidate complete但 reviewer REJECT；legacy translation published count 0 |
| exit 0／LaunchAgent installed 足以證明 productive | falsified | idle lanes與 Publisher 可 exit 0，但沒有新 release |

## Secrets redaction

- 未讀取或輸出 plist `EnvironmentVariables`。
- 未讀取 credential file 內容。
- evidence 只保留非秘密的 pool／manifest identity hash；不保存 API key。
- inbox 只查 top-level metadata、result keys；未輸出文章／plan內容。
- failed record 只查封閉 error metadata與 schema diagnostic keyword/path。

## Validation contract

交付前執行：

```text
git status --short
git diff --check
git diff --name-only
git diff --stat
```

允許 changed files：

```text
artifacts/fortune_council/content_pipeline_repair_execution/evidence/
  CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731/
    baseline.md
    failure-matrix.md
    observe-verification.md
```

Candidate commit 採單一 commit。commit 本身無法在不改變 tree／SHA 的情況下
內嵌自己的 hash；因此 formal delivery receipt 以 `git rev-parse HEAD` 提供
actual candidate SHA，本文件以「所在 commit」作自我 locator。

## Acceptance mapping

| acceptance | evidence |
|---|---|
| 四 lane fresh baseline | `baseline.md` 的 observation window、queue/state/ledger locator |
| 每 lane success 或 red-capable failure | new v0.3.183 success＋fresh schema RED；rewrite candidate success＋release-gate RED；i18n-new hydration RED；i18n-rewrite quality RED |
| 八層可分離 | `failure-matrix.md` |
| 無 provider／production mutation | 本文件 scope receipt、command inventory、tracked diff |
| only three allowlist files | final `git diff --name-only`／commit diff |
| `git diff --check` | final verification receipt |
| single candidate commit | formal thread delivery receipt |

## Status

`DELIVERABLE_CANDIDATE_ONLY`：

- 根因與 failure matrix 已封閉。
- source／actor SHA mismatch 仍是 baseline blocker。
- 尚未 repair、review、integrate、canary、deploy、publish 或接受根卡。
