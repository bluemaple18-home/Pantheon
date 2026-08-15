# APF-004 Gate A loaded-but-inert capacity preflight 修復卡

## 工作身分與目標

- 角色：沿用既有 APF-004 Executor／Repair thread，不建立新 thread 或 root chain。
- 基線 candidate：`634fa8b227e883afd8758e5d193e7db00a292622`。
- parent／`origin/main`：`38e434a9051b1aaea2c08450d71bc82b7e44cb25`。
- 目標：讓正式 runtime identity／topology 明確證明為 loaded-but-inert 的 publisher 不因無 PID 被 capacity preflight 誤判；一般 loaded／running service 無 PID 仍 fail closed。

## 已知事實

- blocker evidence：`artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/gate_a_deterministic_plan_apply_20260815/`。
- `apply_calls=0`、transaction `NOT_CREATED`、`production_mutation=0`。
- public seam：`scripts.pantheon_content_capacity_guard.preflight` 經 `_service_rss_bytes` 觀測 launchd topology。
- 失敗訊號：`rss_telemetry_unknown`／`loaded_service_pid_missing:com.pantheon.agy-content-publisher`。

## 可證偽假說

1. 若根因是 `_service_rss_bytes` 把所有 `launchctl print` 成功但無 PID 的服務都視為錯誤，則加入一個由正式 manifest／topology 明確宣告 inert 的測試後，現況會因 `rss_available=false` 產生目標 assertion failure；只在該 authority 成立時略過 PID 要求應使測試轉綠。
2. 若真正根因是 runtime manifest／topology 尚無足夠資料區分 inert 與異常 missing PID，則 public preflight 無法在不放寬一般 fail-closed 的前提下修復；source inspection 會找不到可驗證 authority，此時必須 BLOCKED，不得猜測或新增第二套 topology 契約。

## 唯一修改範圍

- `.ai/codex_task_apf_004_gate_a_loaded_but_inert_capacity_repair_20260815.md`
- `scripts/pantheon_content_capacity_guard.py`
- `tests/test_pantheon_content_capacity_guard.py`

不得修改其他 code、config、tests、artifact root、manifest、plist、queue、state、transaction 或 production runtime。

## TDD 與驗收

1. CodeGraph context 定位 public observable seam，再限域讀 source／tests。
2. 新增單一 red-capable regression：正式 authority 明示 publisher inert 時無 PID可通過；一般 loaded／running 無 PID仍 `NO-GO`。
3. RED 必須是目標 assertion failure，不接受 import／fixture failure。
4. 最小修復只採用既有正式 identity／topology／manifest authority；若不存在即 BLOCKED。
5. GREEN：目標測試、完整 capacity guard tests、相關 runtime／manifest tests。
6. `rg '\[DBG-'` 零命中於 changed source／test；`git diff --check` PASS。
7. 建立單一 candidate commit，不 amend、不 push。

## 絕對禁止

- apply、rollback、finalize、Gate B、publish、deploy、queue mutation、transaction、tag、push。
- live production paths、LaunchAgent、manifest、plist 或 worker mutation。

## Task History

- `2026-08-15T07:25:00Z`：建立修復卡；保存上述兩個可證偽假說。尚未修改 source／test，production mutation 維持 `0`。
- `2026-08-15T07:31:00Z`：CodeGraph 與限域 source inspection 證實假說 1；`preflight` 已取得 digest 綁定的 formal runtime receipt，但 `_service_rss_bytes` 未使用其 `gate2-actor:<sha>:activation-only` topology，將 publisher loaded/no-PID 一律回報 unknown。
- `2026-08-15T07:33:00Z`：新增 public `preflight` 雙向 regression；RED 為目標 assertion `NO-GO != PASS`，非 import／fixture failure。一般 `:normal` identity 的 loaded/no-PID 負向 assertion 同測試鎖定。
- `2026-08-15T07:33:02Z`：最小修復將已驗證的 `formal-runtime-v2-gate2`／`gate2-actor:<sha>:activation-only` receipt 轉為既有 service allowlist 的 expected-inert topology；僅該 authority 且 launchctl 明示 `state = not running` 時將 loaded/no-PID 記為 inert，一般或不一致 topology 維持 `loaded_service_pid_missing`。
- `2026-08-15T07:33:02Z`：目標 regression `1 passed`；完整 capacity guard `17 passed`；runtime manifest／promotion `60 passed`；`[DBG-` 掃描零命中；`git diff --check` PASS。未存取或修改 production runtime。
- `2026-08-15T07:39:45Z`：Reviewer P1 指出 state parser 使用單次 `search`，輸出若同時含 `state = running` 與 `state = not running` 仍會命中 inert exemption，形成 ambiguous-state fail-open；本 follow-up 不改 identity／config／manifest 邊界。
- `2026-08-15T07:41:00Z`：在既有 public `preflight` regression 加入雙 state 輸出；RED 為目標 assertion `PASS != NO-GO`，證實 ambiguous-state fail-open，非 import／fixture failure。
- `2026-08-15T07:41:05Z`：改為抽取全部 launchctl state；只有 list 恰為 `['not running']` 才豁免，零個、多個、running、waiting 或 mixed state 全部 fail closed。目標 `1 passed`、capacity `17 passed`、runtime manifest／promotion `60 passed`。
- `2026-08-15T07:54:26Z`：read-only production preflight evidence `521b90051ab4cca01b1616e020d2b45ec4eb9895` 證實 launchctl root service state 為 `not running`，但 nested resource／jetsam coalition 各有 `active`；舊 parser 未辨識 brace depth，形成第二次 fail-closed blocker。加入匿名化實機結構 fixture，並鎖定 duplicate top-level、running、waiting、missing、unbalanced 全部拒絕。
- `2026-08-15T07:56:00Z`：匿名化 live fixture 的 public `preflight` regression 得到目標 RED：預期 `PASS`、實際 `NO-GO`；失敗在 status assertion，非 import／fixture failure。
- `2026-08-15T07:56:21Z`：最小 parser 以 launchctl brace nesting 追蹤 root depth，只收 root service object 的 state；唯一 `not running` 通過，duplicate／running／waiting／missing／unbalanced 全部拒絕。目標 `1 passed`、capacity `17 passed`、runtime manifest／promotion `60 passed`。
- `2026-08-15T08:01:24Z`：Reviewer P1 指出 root object header 未綁定當次 requested `gui/<uid>/<label>` target，wrong root、prefix／suffix spoof 或 other label 可能被誤歸屬；新增 exact root 正向與 wrong／prefix／suffix／other label／multiple root／前後 garbage 負向矩陣。
- `2026-08-15T08:03:00Z`：root identity regression 得到目標 RED；`wrong_root` case 預期 `NO-GO`、實際 `PASS`，失敗在 observable status assertion，非 import／fixture failure。
- `2026-08-15T08:03:00Z`：最小修復將 `_service_rss_bytes` 當次組成的 exact launchctl target 傳入 parser，root header 必須完整等於 `<target> = {`；目標 `1 passed`、capacity `17 passed`、runtime manifest／promotion `60 passed`。
- `2026-08-15T08:04:00Z`：補鎖 root header 前後 whitespace 亦不得正規化成通過；最終 regression 數維持 capacity `17 passed`、runtime manifest／promotion `60 passed`，diff-check、debug/path sanitizer PASS。

## Receipt

- 狀態：`READY_FOR_FOLLOW_UP_CANDIDATE_COMMIT`
- RED：`uv run --python .venv/bin/python pytest -q tests/test_pantheon_content_capacity_guard.py::test_preflight_allows_formal_activation_only_service_without_pid_but_rejects_normal`，`1 failed`；目標 assertion failure。
- root cause：capacity preflight 已驗證正式 runtime receipt，但 RSS collector 未接收 activation-only topology，導致預期 inert 的 loaded service 被當成異常 missing PID。
- fix：僅接受正式 Gate 2 config、exact activation-only identity pattern 與 launchctl `not running` 觀測，將固定 manifest service allowlist 傳入 RSS collector；其他 receipt、normal identity、running state、未驗證 runtime 都不豁免 PID/RSS。
- GREEN：目標 `1 passed`；`tests/test_pantheon_content_capacity_guard.py` 為 `17 passed`；`tests/test_pantheon_content_runtime_manifest.py tests/test_pantheon_content_runtime_promotion.py` 為 `60 passed`。
- changed files：本卡、`scripts/pantheon_content_capacity_guard.py`、`tests/test_pantheon_content_capacity_guard.py`。
- production mutation：`0`
- P1 RED：目標 regression `1 failed`；ambiguous `state = running`＋`state = not running` 被錯誤判為 `PASS`。
- P1 fix：抽取所有 state 欄位並要求 cardinality `1`、exact value `not running`；identity／config／manifest authority 不變。
- P1 GREEN：目標 `1 passed`；完整 capacity `17 passed`；runtime manifest／promotion `60 passed`。
- top-level parser follow-up：`READY_FOR_FOLLOW_UP_CANDIDATE_COMMIT`；production mutation `0`。
- top-level parser RED：目標 regression `1 failed`；nested coalition states 被錯算成 root service states。
- top-level parser fix：以 balanced brace depth 辨識唯一 root object，nested coalition state 不計入 service state；identity／config／manifest boundary 未變。
- top-level parser GREEN：目標 `1 passed`；完整 capacity `17 passed`；runtime manifest／promotion `60 passed`。
- root identity binding follow-up：`READY_FOR_FOLLOW_UP_CANDIDATE_COMMIT`；production mutation `0`。
- root identity binding RED：目標 regression `1 failed`；wrong root 被錯誤接受。
- root identity binding fix：exact target 由 `gui/<current uid>/<current label>` command target 傳入，未 hardcode uid／label；prefix／suffix／other label／multiple root／garbage 全部拒絕。
- root identity binding GREEN：目標 `1 passed`；完整 capacity `17 passed`；runtime manifest／promotion `60 passed`。
- root identity binding verification：raw root header exact match；leading／trailing whitespace、prefix／suffix、other label、multiple root、前後 garbage 全部 fail closed。
