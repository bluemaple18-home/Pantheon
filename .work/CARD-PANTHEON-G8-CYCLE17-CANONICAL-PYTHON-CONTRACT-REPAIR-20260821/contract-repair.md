# Cycle 17 canonical Python 契約修復證據

- dispatch：`G8-C17-CANONICAL-PYTHON-REPAIR-20260821-f78d8c0b13`
- 基線：detached `f78d8c0b13`
- 既有 NO-GO evidence：`68fdc5569e`
- verdict：`CONTRACT REPAIRED`
- source change：不需要；`_canonical_executable` 的 canonical-realpath fail-closed 檢查維持原樣。

## 單一根因

Cycle 17 卡片把 `<repo-root>/.venv/bin/python` 所代表的 tooling symlink 誤寫成 promotion request 與 formal preflight 的 executable identity；source 正確要求 manifest Python 使用 canonical realpath，因此 deterministic plan fail-closed。

## 修復契約

1. 文件只以 `<repo-root>/.venv/bin/python` 表達 tooling source。
2. 執行任何 formal plan 前，必須解析並保存 canonical realpath、精確版本 `Python 3.12.12`、regular executable 狀態與 executable SHA256。
3. plan request、exact apply argv、target manifest、postcheck、formal preflight argv 與 authorization 必須使用同一個 canonical realpath literal；symlink 不得成為 runtime identity。
4. 本次 observation 鎖定 realpath `/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12`，SHA256 `d7e27bef360beb2146e27f6d7edf7dac70e5cbc3a800c15369a0eb73bcea33ae`。
5. 新 host/worktree 必須從 tooling source 重建 evidence；realpath、版本或 digest 不符即 `BLOCKED / NO CANARY`，不得弱化 source check。

## 邊界與計數

- public preflight invocation：`0`
- deterministic plan invocation：`0`
- Gate A invocation：`0`
- install／promotion／restage／activation／canary invocation：`0`
- production mutation：`0`
- source/tests/scripts/config mutation：`0`
- commit：依派工契約不建立，由主線保存。
