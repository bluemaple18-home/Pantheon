# Cycle 17 formal preflight 契約分析

- 記錄時間：`2026-08-20T17:22:46Z`
- 狀態：`BLOCKED / PUBLIC PREFLIGHT NO-GO`
- CodeGraph：已先查詢；worktree 未初始化，primary index marker `e4df0fc4349568cb0a7df2de56a4865885361494` 落後目前 HEAD `9094e62817fb39148844c8f0761fbcc45aae8797`，因此以限域 source／tests／installer／manifest 讀取確認。

## H1 verdict：SUPPORTED

current formal runtime manifest 將 actor、manifest digest 與 Python executable 綁成同一 identity tuple：

- actor：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor` @ `88c6c0a95a013d0e9e8ab84c1a0f75a58ada1ff5`
- manifest digest：`db6cc697831947734c86b76e3e0054309d0854aacb7d55044cc559e02f1e24bb`
- manifest Python：`/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/bin/python3.14`（Python 3.14.5）
- target tooling authority：`/Users/mattkuo/Documents/Pantheon/.venv/bin/python`（Python 3.12.12）

installer 先以 `--expected-python-executable "${PYTHON_BIN}"` 驗 manifest，再要求 manifest actor root 等於 installer 的 repo root。因此 current preflight 必須從 current actor 的 public installer、使用 manifest-bound Python 執行；target tooling venv 不得代跑 current manifest module。

## H2 verdict：SUPPORTED

Cycle 16 receipt 是 bounded synthetic capacity safety gate；promotion plan 的 `_validate_capacity_receipt` 消費該 receipt，並以 zero-write plan 產生 target manifest digest。formal runtime identity preflight 則驗證已鎖定的 actor／manifest／digest／interpreter tuple，兩者不是同一 gate。

canonical ordering：

1. 驗證 Cycle 16 bounded capacity receipt（不重跑 exercise）。
2. 建立 deterministic candidate promotion plan，鎖 target manifest digest 與 exact apply argv。
3. 通過既有 mutation authorization／Gate A。
4. apply materialize target actor／manifest／private stage，postcheck 後才以 target manifest-bound actor installer 與 interpreter 執行 formal identity preflight／restaging；任何非 PASS fail closed。

因此 target formal identity preflight 不得被寫成 plan 之前的模糊 `current capacity preflight`，否則會把 current manifest authority 與 target tooling authority 混用並形成循環依賴。

## Public seam 與 mutation 邊界

- public seam：`scripts/install_pantheon_content_capacity_guard_launchd.sh --preflight`
- installer 以自身位置解析 `REPO_ROOT`；manifest `actor_root` 必須與其一致。
- `--preflight` 在 `run_capacity_preflight` 後直接退出，不會執行 stage `mkdir`／`install`。
- tests 鎖定 PASS 與 Python-drift failure 都不建立 target home、不寫 publisher/log、不觸發 launchctl mutation。
- 本次 command 僅產生並清理由 `mktemp` 建立的暫存 plist／receipt；actor HEAD、actor clean state 與 manifest file SHA256 執行後不變。

## 停止條件

唯一一次 public preflight exit `1`，回傳：

- preactivation transition：`plist canonical realpath or owner mismatch`
- capacity sample：`rss_telemetry_unknown`
- RSS detail：`loaded_service_pid_missing:com.pantheon.agy-content-publisher`

依單次與 fail-closed 契約，不重試、不換入口、不修改 Cycle 17 card。

## Invocation counts

- direct-module RED：`0`
- capacity exercise：`0`
- public installer preflight：`1`（`NO-GO`）
- Gate A／push／promotion／restaging／activation／canary／lane／Publisher／tag／publish：`0`
- production mutation：`0`
