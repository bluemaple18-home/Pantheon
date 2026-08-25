---
id: CARD-PANTHEON-G8-V0393-FAILED-EXTERNAL-JOB-REPLACEMENT-REPAIR-20260825
status: completed
chain_id: PANTHEON-G8-FAILED-EXTERNAL-JOB-REPLACEMENT-20260825
role: implementation
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 規格已固定，但涉及 production queue、terminal failure 與 exactly-once recovery 契約；使用 strict/core-bounded 跑道。
traces_to: [SC-001, SC-002, SC-003, SC-004]
---

# Pantheon failed external job 單次 replacement 正式入口

工作名稱：Pantheon failed external job 單次 replacement 正式入口

任務目的：新增一個 fail-closed 正式入口，讓已留下 `CLI_NONZERO` failed receipt、沒有 provider result、原 run 仍 active 的 external job，在明確 authority 下建立同 run identity 的唯一 replacement job；禁止手造 queue/state 與一般化 retry。

## 已知事實

- V0391 run：`v0391-publish-canary-20260825-01`。
- correlation：`8ca37c8df03cbb06b4b65ac0912d485b`。
- namespace／run registry key：`7c2a03c622fcf01536d0574c`。
- failed job：`54f57c7de682e12f5c0f6250576cde08a4f4d06a`。
- archive request 與 failed receipt 都存在；failure 為 `GeminiCliFailure / CLI_NONZERO`，沒有成功 result。
- production actor 只有 `terminalize-pending`；它拒絕已有 failed outcome，沒有 `terminalize-failed-external-job` 或同等 replacement 入口。
- 使用者只授權同 V0391／同 article／同 correlation 建立 1 個 replacement Gemini job；不是第二篇、第二 run、第二 Publisher child 或 retry chain。

## 唯一責任切片

`SLICE-V0393-01`：RED → 最小正式入口 → GREEN。frontier 可立即開始；沒有其他 slice。

## 可改範圍

- `scripts/agy_gemini_outbox.py`
- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_outbox.py`
- `tests/test_agy_gemini_coordinator.py`
- 本卡 RESULT 與 `g8_v0393_failed_external_job_replacement_20260825/` 證據

## 必要契約

- 新入口必須接受 expected `job_id`、`run_id`、`correlation_id`、namespace、failure category/error code 與明確 authority digest；所有 identity 必須與 archive、failed receipt、active run registry 相符。
- 只允許 terminal failed job 且無 success result；`CLI_NONZERO` 不得因此加入一般 retry allowlist。
- replacement 必須重用原 request 的 model、role、prompt、schema、operation level 與 request identity，另有不可混同 transport retry 的 replacement lineage／attempt identity。
- 同一 source failed job 最多成功建立 1 個 replacement；重放同一命令須回既有 receipt，不得再 enqueue。不同 authority／identity、已有 result、registry 非 active、last job 漂移、缺 artifact 一律 fail closed，且 zero mutation。
- mutation 必須原子化：replacement outbox job、lineage receipt、run registry last-job transition 全成或全不成；不得刪改原 archive／failed evidence。
- 提供 `plan-only`／dry-run 預檢與正式 CLI；輸出 machine-readable receipt，足以讓 V0391 原 thread 精確執行一次。

## 成功準則

- `SC-001`：RED 測試證明現況沒有合法入口；GREEN 後可由 exact V0391 fixture 建立唯一 replacement，且原 request payload byte-equivalent（排除明示 lineage/job identity 欄位）。
- `SC-002`：同 authority 重放為 idempotent；第二個 replacement、不同 identity、已有 success、非 active run、last-job drift、缺 archive/failed receipt皆 zero mutation。
- `SC-003`：`CLI_NONZERO` 仍是 terminal、非自動 retry；既有 transport retry 測試不變。
- `SC-004`：targeted tests、兩個完整 test files、`git diff --check` 通過；若完整檔有既存失敗，須證明與 diff 無關並列 targeted regression。

## 禁止範圍

- 禁止操作 production runtime、真實 queue/state、launchctl、activation、Publisher、publish/push/tag。
- 禁止修改 model route、manifest、promotion、Publisher、文章內容、registry schema 或其他 source。
- 禁止手造 V0391 artifacts；本卡只交付 source、tests、正式 CLI 契約與證據。
- 禁止擴成通用 retry framework、無上限 retry、第二張 implementation 卡或新架構岔。

## 停損與交付

- 若原子化需要超出 allowlist、registry schema 必須變更、或無法維持 exactly-once，立即 `BLOCKED`，不得擴 scope。
- 最多兩次有證據修正；交付 1 個原子 candidate commit、完整 SHA、RED/GREEN、CLI help/plan-only receipt 與 RESULT。不得宣稱已整合、已 promotion 或已發文。

## RESULT

狀態：completed

候選 commit：本次交付 HEAD；完整 SHA 以 `git rev-parse HEAD` / final receipt 為準

變更摘要：

- 新增 `replace-failed-external-job` formal CLI/API，接受 expected job/run/correlation/namespace/failure/authority identity，從 source archive + failed receipt + active run registry 建立 deterministic exactly-once replacement。
- 新增 outbox formal replacement lineage validation 與 consume routing；只有 replacement decision receipt 存在時才從 source failed job 導向 replacement result，`CLI_NONZERO` 未加入一般 retry allowlist。
- 新增 coordinator/outbox tests 覆蓋 plan-only、execute、same-authority replay、第二 authority、identity drift、已有 success、非 active、last-job drift、缺 archive/failed receipt、source evidence preservation、replacement logical request identity。
- V0394 修正 reviewer P1：replacement request 先寫 runner 不可見 staging，formal decision 與 registry state durable 後才 final atomic publish live outbox；same-authority replay 可補完 decision/state/final-publish crash partial，不產生 executable orphan。
- V0394 收斂 P2：source archive 與 failed receipt JSON 讀取改為 descriptor-bound `O_NOFOLLOW` + `fstat` 驗證，補 path replacement drift tests。
- Follow-up 修正 production-reproduced referential-integrity blocker：formal replacement plan/execute 以 durable run registry 的 expected `run_id` 作 authority；actor-local `brief.json` 存在時仍驗證，但 promotion 清掉 run_dir 時不再拒絕。
- Follow-up 新增 exact-run continuation recovery：replacement result 存在後，`cycle_once(..., exact_run_ids=...)` 可在 missing actor-local run_dir 下，透過 source archive + formal decision + replacement inbox 完成該 run。
- Follow-up 修正 replacement runner `INVALID_RECEIPT`：root cause 是錯誤 invocation surface／未載入 formal production env；直接 shell runner 缺 `AGY_GEMINI_CREDENTIAL_POOL_FILE` 時落入 CLI fallback，而 Lite model 沒有 Antigravity Low label，於 provider/CLI subprocess 前 deterministic `ValueError`。
- Follow-up 在既有 `replace-failed-external-job` existing-decision 分支加入顯式 `--resume-replacement --local-preflight-reason NO_ANTIGRAVITY_LOW_MODEL_LABEL`；只允許同一 archived replacement job 在 `ValueError/INVALID_RECEIPT`、無 production attempt marker、closed local preflight proof 下保存 failed evidence 並原子移回 outbox，不建立第二 replacement/job。

驗證：

- RED：`uv run pytest tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_cli_entrypoint_exists -q`，實作前失敗於缺少 `replace-failed-external-job` CLI entrypoint。
- V0394 RED：`uv run pytest tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_runner_claim_race_leaves_no_executable_orphan -q`，修復前留下 `processing/<replacement>.json` orphan。
- Follow-up RED：`uv run pytest tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_plan_only_uses_durable_registry_when_run_dir_missing -q`，修復前失敗於 `run directory must contain brief.json`。
- GREEN targeted coordinator：`11 passed in 0.43s`。
- GREEN targeted outbox：`6 passed in 0.13s`。
- V0394 targeted coordinator：`8 passed in 0.28s`。
- V0394 replacement targeted：coordinator `17 passed, 266 deselected in 0.23s`；outbox `7 passed, 167 deselected in 0.04s`。
- Follow-up replacement targeted：coordinator `19 passed, 266 deselected in 0.25s`；outbox `7 passed, 167 deselected in 0.04s`。
- 完整受影響測試：`uv run pytest tests/test_agy_gemini_outbox.py tests/test_agy_gemini_coordinator.py -q`，`459 passed in 444.22s (0:07:24)`。
- Follow-up INVALID_RECEIPT root-cause read-only evidence：actor/main `validate_external_request` 均 PASS archived `b50e5ab655e19388e9858c4a850ac2f37c9d8f3c` payload；shell env 缺 `AGY_GEMINI_CREDENTIAL_POOL_FILE/STATE_FILE`；`_cli_generate_json` 對 `gemini-3.5-flash-lite` 直接 `ValueError no Antigravity Low model label ...`。
- Follow-up INVALID_RECEIPT targeted：`.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -k "failed_external_job_replacement_resume"`，`5 passed, 285 deselected in 0.09s`。
- Follow-up INVALID_RECEIPT 完整受影響測試：`.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py tests/test_agy_gemini_outbox.py`，`464 passed in 448.40s (0:07:28)`。
- 最終 diff：`scripts/agy_gemini_coordinator.py`、`tests/test_agy_gemini_coordinator.py`、本卡 RESULT、`g8_v0393_failed_external_job_replacement_20260825/evidence.md`。
- `git diff --check`：passed。

證據：

- `artifacts/fortune_council/four_lane_runtime_execution/g8_v0393_failed_external_job_replacement_20260825/evidence.md`

風險與邊界：

- 未操作 production runtime、真實 queue/state、launchctl、activation、Publisher、publish/push/tag。
- 未修改 model route、manifest、promotion、registry schema 或文章內容。
- `uv run` 建立測試用 `.venv` 並曾觸碰 `uv.lock` project version；已還原 `uv.lock`，不納入候選 commit。
