---
id: CARD-PANTHEON-G8-PREACTIVATION-STAGE-RESTORE-CYCLE-20-20260821
status: ready
chain_id: PANTHEON-G8-PUBLISHER-CANARY
role: implementation
cycle: 20
thickness: strict
risk: production-adjacent
model: gpt-5.5
reasoning: high
model_reason: production-adjacent private LaunchAgent stage mutation with a fixed operational contract
---

# 恢復 G8 canary private preactivation stage

## Root question

Cycle 19 的 Capacity preflight 為何在 cold reset 後回傳 `preactivation stage mismatch`，以及是否能只用既有正式 installer 恢復 private stage，使 capacity gate 回到 PASS，而不 activation、不執行 canary？

## 已知證據

- Cycle 19 正式 thread：`01a021da-c07a-7063-a3fc-348e26e0a9b3`。
- Cycle 19 終局：`BLOCKED / NO CANARY`。
- 正式 Publisher activation、transaction、tag、push、retry、production mutation 均為 `0`。
- authority：
  - actor/source/origin：`c05929f2a7dac86e94aaeaa5ab6c5455892f5f77`
  - manifest digest：`e3c393bb18a55eba1c8c6cb9e92abfb63b4241936dc78772bfaa5ec952177d32`
  - runtime identity digest：`db8c1691bb5433b23a4803743782d686d8779ef4fec5d5b7d1cb9e038092999e`
  - generation：`g17-c05929f2a7-20260821T827804Z`
  - Python：`/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12`
- exact run：`auto-i18n-en-614aa4dc3542ab2c5637`；target：`ASTRO-BASE-01:en`；queue run count：`140`。
- 七個 live LaunchAgent 已是 coherent activation-only、loaded/no-PID。
- Cycle 19 Capacity 原始輸出同時含：
  - `rss_telemetry_unknown / loaded_service_pid_missing:com.pantheon.agy-content-publisher`；這是 activation-only preactivation 的預期 PID gap。
  - `preactivation stage mismatch`；current read-only inspection 顯示 `/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage` 不存在。

## 目標

1. 先以 read-only 證據確認唯一根因是 private stage 缺失，而非 authority、live aggregate、queue 或 source drift。
2. 僅從 authoritative runtime actor 使用既有 public installers，依序重建 coordinator＋四 lanes、Publisher exact-run、capacity private stage。
3. 證明 capacity formal preactivation transition PASS，且 live 七服務仍為 activation-only loaded/no-PID。
4. 保存可重現證據與一個 candidate commit；交回主線決定是否另開 canary 卡。

## 固定執行順序

1. 核對 actor HEAD/clean、remote `refs/heads/main`、manifest tuple、live aggregate、七服務 loaded/no-PID、queue=`140`、exact run唯一、stage 目前缺失。
2. 所有正式 argv 固定使用 `/usr/bin/env TMPDIR=/private/tmp PANTHEON_USER_HOME_DIR=/Users/mattkuo PANTHEON_PYTHON_PATH=<canonical-python> PANTHEON_RUNTIME_MANIFEST_FILE=<runtime-manifest> PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST=<manifest-digest>`。
3. 從 runtime actor 執行 `scripts/install_agy_gemini_coordinator_launchd.sh --install` 一次，只建立 coordinator＋四 lanes private stage。
4. 以 `PANTHEON_PUBLISH_MAX_RUNS=1`、`PANTHEON_PUBLISH_EXACT_RUN_ID=auto-i18n-en-614aa4dc3542ab2c5637` 執行 `scripts/install_agy_content_publisher_launchd.sh --install` 一次，只建立 Publisher private stage。
5. 執行 `scripts/install_pantheon_content_capacity_guard_launchd.sh --preflight` 一次。必須接受 activation-only 的 publisher PID gap 並輸出 transition `PASS/accepted`；失敗立即 `BLOCKED / NO ACTIVATION`，禁止 retry、禁止 `--install`。
6. 只有步驟 5 PASS，才執行 `scripts/install_pantheon_content_capacity_guard_launchd.sh --install` 一次；其內建 mutation 前 revalidation 不算 retry，不得另加第二次 public preflight。
7. 驗證七份 staged plist、metadata、exact run/max-runs、live aggregate仍 activation-only、七服務仍 loaded/no-PID、queue與 exact run未變；Publisher activation/transaction/tag/push/canary/retry 全為 `0`。

## 可改範圍

- `/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage/**`，且只能由上述既有 installers 寫入。
- 本 worktree：`.work/CARD-PANTHEON-G8-PREACTIVATION-STAGE-RESTORE-CYCLE-20-20260821/**`。
- committed result：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-PREACTIVATION-STAGE-RESTORE-CYCLE-20-20260821-RESULT.md`。

## 禁止

- 禁止修改 source、tests、config、workflow、runtime manifest、live plist、queue、state、registry、sitemap、feed。
- 禁止 `launchctl bootstrap/bootout/kickstart`、`--activate`、`--activate-only`、`--activate-publisher-only`。
- 禁止 Publisher transaction、tag、push、canary、lane run。
- 禁止重跑同一失敗步驟、換入口、direct module、wrapper、mock telemetry、放寬 capacity gate。
- 禁止另開 thread、Reviewer、Repair 或額外診斷卡。

## 驗收

- root cause 精確定位為 stage lifecycle 缺口；若不是，保留證據並 fail closed。
- coordinator installer=`1`；Publisher installer=`1`；capacity public preflight=`1`；capacity install=`0|1`；retry=`0`。
- capacity preactivation transition=`PASS/accepted`。
- 七服務 staged coherent；live 七服務仍 activation-only loaded/no-PID。
- queue=`140`、exact run count=`1`、其他 queue/lane 未變。
- activation/transaction/tag/push/canary=`0`。
- `git diff --check` PASS；candidate commit 只含 result artifact。

## 終局

只能回報：

- `STAGE RESTORED / CAPACITY PASS`
- `BLOCKED / NO ACTIVATION`
