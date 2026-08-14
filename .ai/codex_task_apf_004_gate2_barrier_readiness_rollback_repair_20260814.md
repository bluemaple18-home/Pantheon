# APF-004-GATE2-BARRIER-READINESS-ROLLBACK-REPAIR-001

## 正式狀態

- 工作：修復 Gate 2 barrier readiness/token cycle 與 rollback receipt 判定
- 現在狀態：REPAIR_READY / production 停線 / 零 live mutation
- base：a153219f919f965821dd7ee15d23a01f0469133f
- finding：APF004-G2-P1-BARRIER-READINESS-CYCLE
- mutation_executed：false
- live_mutation_executed：false
- production_mutation_executed：false
- activation_executed：false

## 契約邊界

- 沿用既有 Repair formal task；未建立 replacement。
- 不執行 production install / activate / launchctl mutation。
- 不 merge、不 push、不發文。
- 不放寬 token、manifest、python、path、identity、business I/O gates。
- positive installer fixture 不以直接 copy readiness 作為唯一證據；新增 fixture 會實際執行 `barrier-exec` 產生 readiness。

## Source decision

- worktree 啟動時 clean。
- `origin/main` / `FETCH_HEAD` 已確認 exact base `a153219f919f965821dd7ee15d23a01f0469133f`。
- CodeGraph 查詢此 worktree 未初始化 `.codegraph`，依契約 fallback 限域讀：
  - `scripts/pantheon_content_runtime_manifest.py`
  - `scripts/pantheon_runtime_activation.py`
  - `scripts/install_agy_gemini_coordinator_launchd.sh`
  - `tests/test_pantheon_content_runtime_manifest.py`
  - `tests/test_agy_gemini_coordinator.py`

## RED

1. 真實 `barrier-exec --activation-only`，無 pre-existing token：
   - 現版在 readiness ack 寫出前 return 78。
   - `ready/<service>.json` 不存在。
2. normal `barrier-exec`，barrier 已存在但 env 無 pre-existing token：
   - 現版 return 78。
   - child 沒有收到 `PANTHEON_RUNTIME_ACTIVATION_TOKEN`。

## 修復摘要

- `validate_runtime_tick()` 新增 `require_activation_token`，預設仍為 true。
- `barrier-exec` pre-barrier path：
  - 驗 manifest、service label、queue/state/actor/log path、runtime identity、python identity。
  - 不要求 activation token。
  - 寫入 service readiness ack。
- barrier 出現後：
  - validate exact barrier。
  - 將 absolute barrier path 設為 child env `PANTHEON_RUNTIME_ACTIVATION_TOKEN`。
  - activation-only 驗 barrier 後直接 PASS，不 exec child。
  - normal path 才 exec child。
- installer：
  - production default barrier timeout 仍為 90 秒。
  - 測試可用 `PANTHEON_ACTIVATION_BARRIER_TIMEOUT_SECONDS` 降低 timeout，但值必須 1..300。
  - rollback failed receipt 新增 sanitized `rollback_check_ids`，定位 bootout / restore / bootstrap / identity / barrier 類 failure。

## 驗證摘要

- barrier-exec activation-only real path：PASS
- normal child token propagation：PASS
- no-token/no-barrier child I/O guard：PASS
- runtime manifest full suite：PASS
- runtime activation suite：PASS
- seven real readiness → barrier activation：PASS
- barrier timeout rollback complete / forced failed：PASS
- inert-six / capacity-only / normal isolation matrix：PASS
- affected coordinator suite：PASS
- three installer `bash -n`：PASS
- final scans / diff checks：見 evidence

## Remaining risk

- Barrier timeout rollback fixture 使用 1 秒 test-only timeout env；production default 未變。
- Installer real-readiness fixture 使用 fake launchctl 啟動 repo-owned `barrier-exec` subprocess，仍非 production launchd。
- 未宣稱 integration 或 production ready。
