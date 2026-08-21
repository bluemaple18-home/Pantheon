---
id: CARD-PANTHEON-G8-PUBLISHER-ONLY-CANARY-CYCLE-30-20260821-RESULT
card_id: CARD-PANTHEON-G8-PUBLISHER-ONLY-CANARY-CYCLE-30-20260821
status: blocked
terminal_state: BLOCKED / NO RETRY
candidate_thread: 01a02271-884e-7561-ad72-97d371effa93
---

# G8 Publisher-only canary Cycle 30 result

## 終局判定

`BLOCKED / NO RETRY`

本次未發布 canary。首次正式 Publisher child 在 release regression 階段失敗，transaction 進入 `failed_recovered`；之後 live Publisher LaunchAgent 因 `RunAtLoad`／`StartInterval=60` 自動啟動第二次 child，違反本卡 `Publisher child=1`、`retry=0` 契約。主線立即對唯一 Publisher label 執行精確 stop-loss bootout，最終驗證 service not found，阻止第三次執行；其餘六服務未動。

## 前置閘門

- formal thread、獨立 worktree、required base `7bb397d7980f311b2c231dcb788ffee8eda94c00`、clean、card blob：PASS。
- CodeGraph readiness：PASS，577 files / 6,538 nodes / 14,218 edges；indexed SHA 與 required base 相同，Publisher-only semantic query 完成。
- current capability/readiness：七項 capability PASS、official gate READY、fail-closed fixture BLOCKED、`canary_created=false`。
- current synthetic capacity：PASS，連續兩 cycle；host capacity/preactivation：PASS，`preactivation_transition=accepted`、`production_mutation=false`。
- live/stage：coherent G23；actor/origin/manifest/queue/state/exact run：PASS。
- bounded wait：七服務連續三次 loaded/no-PID，PASS。
- formal Publisher preflight：PASS；exact run `auto-i18n-en-614aa4dc3542ab2c5637`、target `ASTRO-BASE-01:en`、`max_runs=1`、`push_mode=push`。

## 正式執行與失敗

- 從 current actor、`TMPDIR=/private/tmp`，第一次即以 host execution 執行正式 `install_agy_gemini_coordinator_launchd.sh --activate-publisher-only`，entrypoint invocation 僅一次。
- 首次 Publisher child 執行 release regression，結果為 `7 failed, 413 passed, 1 warning`；七項失敗皆在 `tests/test_agy_seo_copy_pipeline.py`，錯誤邊界為 formal model route config identity 不完整。
- release regression 位於 release commit、tag、push 之前；失敗後 transaction wrapper 回報 `translation.status=failed_recovered`、`translated=0`、`retry_status=candidate_preserved_deferred`。
- rollback/recovery receipt 完成 archive、restore、unlink、tag-delete 與 final evidence write；actor 回到原始 SHA `b1719c0d6243c7ec6372889405a846ccd1b666ed` 且 final clean。
- origin `main` 仍為 `b1719c0d6243c7ec6372889405a846ccd1b666ed`；exact-run tag 不存在，ordinary push 未發生。

## 自動第二次 child 與停損

- 首次 child 退出後，normal Publisher plist 仍帶有 `RunAtLoad=true` 與 `StartInterval=60`。
- 唯讀檢查觀察到 live Publisher `runs=2`、PID `23013`：第二次 child 已由 launchd 自動啟動。此為一次未允許的自動 retry；未發生第二次 activation entrypoint invocation。
- 主線立即執行精確 `launchctl bootout gui/501/com.pantheon.agy-content-publisher`；終態驗證為 service not found，阻止第三次 child。
- 其餘六服務未 bootout、未 bootstrap，business child I/O=`0`。
- 本卡不允許 retry、重建 stage、第二次 activation 或 replacement task；至此停止。

## Mutation accounting

- formal activation entrypoint invocations：`1`
- Publisher child executions observed：`2`
- automatic retries observed：`1`
- committed production transactions：`0`
- release commits：`0`
- tag calls / exact-run tags：`0 / 0`
- ordinary pushes：`0`
- other six services business child I/O：`0`
- queue runs before/after：`140 / 140`
- exact run matches before/after：`1 / 1`
- actor final clean：`true`
- Publisher final launchctl state：`service not found`

## 對帳差異

- exact run 仍在 queue，原始 run receipt 與 `complete` 狀態保留。
- exact translation run 新增 Publisher approval marker；state 新增首次失敗與 rollback/recovery evidence。這些是已對帳的失敗證據，不是已提交的 production transaction。
- actor HEAD、origin `main`、tag 集合均無發布差異；因此沒有未對帳的 partial publish。

## 證據

- `/private/tmp/pantheon-g8-cycle30-readiness/readiness-summary.json`（host 暫存）
- `/private/tmp/pantheon-cycle30-before.json`（host 暫存）
- `/private/tmp/pantheon-cycle30-after.json`（host 暫存）
- `<runtime-root>/state/evidence/failed-translation-08240d2029/failure.json`
- `<runtime-root>/state/evidence/failed-translation-08240d2029/recovery-result.json`
- `<runtime-root>/state/evidence/failed-translation-08240d2029/failure-attempt.json`

## 最終狀態

首次 regression 失敗已 fail-closed 並完成 recovery；tag/push 均為 0。雖然 launchd 自動第二次 child 已構成契約違反，主線已立即 stop-loss 並驗證 Publisher service 不存在。actor final clean，無 canary 發布；依卡片契約終局為 `BLOCKED / NO RETRY`。
