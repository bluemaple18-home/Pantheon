# Codex sandbox 內 uv system-configuration panic RCA

## Verdict

`NO_SYNC_GREEN`

在此 Codex sandbox 中，最小可重現且經第二次確認的 GREEN 命令差異為在原本 frozen `uv run` 命令加入 `--no-sync`：

```bash
UV_CACHE_DIR="$PWD/.work/CARD-PANTHEON-UV-SYSTEM-CONFIGURATION-PANIC-RCA-20260820/runtime/uv-cache" \
RUST_BACKTRACE=1 \
uv run --frozen --no-sync python -V
```

這只證明 `uv run` 的同步／環境協調邊界會觸發 panic；不代表 readiness generator 已通過，也沒有執行任何 generator。

## Runtime identity

- exact HEAD：`283ae3a5fd719ee1e5eb4bae08c61c2feb0f7636`
- uv：`uv 0.9.25 (38fcac0f3 2026-01-13)`
- direct venv Python：`Python 3.12.12`
- `CODEX_SANDBOX`、`CODEX_SANDBOX_NETWORK_DISABLED`、`UV_CACHE_DIR`、`UV_LINK_MODE`：皆為 present；未記錄其值。
- task-local cache：`.work/CARD-PANTHEON-UV-SYSTEM-CONFIGURATION-PANIC-RCA-20260820/runtime/uv-cache`

## Bounded matrix evidence

| Step | Exact command | Exit | Result | SHA-256 of local log |
| --- | --- | ---: | --- | --- |
| Baseline | `.venv/bin/python -V` | 0 | `Python 3.12.12`; Python／`.venv` 可執行 | `11127b908355ca05c3fd89fb6e7622ae40cd54419cb5d62508fd633c259ee313` |
| RED | `UV_CACHE_DIR="$PWD/.work/CARD-PANTHEON-UV-SYSTEM-CONFIGURATION-PANIC-RCA-20260820/runtime/uv-cache" RUST_BACKTRACE=1 uv run --frozen python -V` | 101 | 同症狀 panic | `b89001b7a6a61ffecaf8ee4f0286d1b7aaa438ecab604cbe1bbf059f00e37ac6` |
| H-UV-02 | `UV_CACHE_DIR="$PWD/.work/CARD-PANTHEON-UV-SYSTEM-CONFIGURATION-PANIC-RCA-20260820/runtime/uv-cache" RUST_BACKTRACE=1 uv run --frozen --offline python -V` | 101 | 與 RED 相同 panic | `b107e557ded82010ef43620ce978081ba9ce3c5ed535f668be47b49dd1cdeb8a` |
| H-UV-03 | `UV_CACHE_DIR="$PWD/.work/CARD-PANTHEON-UV-SYSTEM-CONFIGURATION-PANIC-RCA-20260820/runtime/uv-cache" RUST_BACKTRACE=1 uv run --frozen --no-sync python -V` | 0 | GREEN：`Python 3.12.12` | `11127b908355ca05c3fd89fb6e7622ae40cd54419cb5d62508fd633c259ee313` |
| GREEN confirmation | 與 H-UV-03 完全相同 | 0 | GREEN：`Python 3.12.12` | `11127b908355ca05c3fd89fb6e7622ae40cd54419cb5d62508fd633c259ee313` |

完整 local-only logs 位於：

- `.work/CARD-PANTHEON-UV-SYSTEM-CONFIGURATION-PANIC-RCA-20260820/baseline-python.log`
- `.work/CARD-PANTHEON-UV-SYSTEM-CONFIGURATION-PANIC-RCA-20260820/red-uv-frozen.log`
- `.work/CARD-PANTHEON-UV-SYSTEM-CONFIGURATION-PANIC-RCA-20260820/offline-uv-frozen.log`
- `.work/CARD-PANTHEON-UV-SYSTEM-CONFIGURATION-PANIC-RCA-20260820/no-sync-uv-frozen.log`
- `.work/CARD-PANTHEON-UV-SYSTEM-CONFIGURATION-PANIC-RCA-20260820/no-sync-confirmation-uv-frozen.log`

RED 與 offline 的 panic signature 為 `system-configuration-0.6.1/src/dynamic_store.rs:154:1` 的 `Attempted to create a NULL object.`，隨後出現 `Tokio executor failed, was there a panic?`。

## Hypothesis disposition

- H-UV-01：**PASS**。direct `.venv/bin/python -V` 成功，而最小 `uv run --frozen` 在 Python 啟動前 panic，支持 runtime boundary 為差異。
- H-UV-02：**FALSIFIED**。只增加 `--offline` 後仍為相同 panic；network／proxy 初始化不是可由 offline 消除的最小原因。
- H-UV-03：**PASS**。在 RED 參數上只增加 `--no-sync` 即 GREEN，且相同條件第二次 GREEN，支持同步／environment reconciliation 邊界為主因。

## Cycle 3 recommendation

只有在 cycle 3 另行授權且仍需以這個 runtime seam 執行時，使用唯一已驗證的最小差異 `--no-sync`。此建議不得被解讀為降低任何 readiness gate；本卡未執行 readiness generator，也未修改 source、設定或 sandbox。
