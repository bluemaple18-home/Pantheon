---
id: CARD-PANTHEON-UV-SYSTEM-CONFIGURATION-PANIC-RCA-20260820
chain_id: PANTHEON-UV-SYSTEM-CONFIGURATION-RCA-20260820
parent_card_id: CARD-PANTHEON-G8-CURRENT-READINESS-RECEIPT-RETRY-20260820
role: diagnostic
cycle: 1
status: ready
type: environment_runtime_rca
thickness: standard
risk: medium
model: gpt-5.6-terra
reasoning: medium
model_reason: 故障已固定在 Codex sandbox 內的 uv runtime，診斷矩陣與停損明確，無 source 或 production mutation；使用 Terra medium 執行 bounded red／green RCA，不使用 Sol。
ownership:
  - artifacts/fortune_council/four_lane_runtime_execution/uv_system_configuration_rca_20260820/**
  - .work/CARD-PANTHEON-UV-SYSTEM-CONFIGURATION-PANIC-RCA-20260820/**
forbidden_scope:
  - 執行 pantheon_content_capability_receipt.py 或任何 readiness generator
  - 修改 scripts、tests、rules、config、workflow、lockfile、Ai Core、Codex 或 shell environment
  - 修改外接硬碟 ACL、macOS privacy、sandbox、writable roots 或全域 UV cache
  - production、publish、transaction、tag、push、deploy、schedule、LaunchAgent mutation
  - 使用 direct Python 執行 Pantheon generator、下載額外工具、無上限重試或同時改多個變數
verification:
  - 最小 RED 能重現相同 system-configuration NULL object panic，或明確證明不可重現
  - direct venv Python baseline 與 uv runtime boundary 分離
  - 每次 uv-run 只改一個變數，總次數最多三次
  - 至少一個假說被證偽；若取得 GREEN，原 RED 再以完全相同 GREEN 條件驗一次
  - evidence 僅限ownership、git diff --check通過、candidate commit後worktree clean
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/uv_system_configuration_rca_20260820/
---

# Codex sandbox 內 uv system-configuration panic RCA

## 工作名稱 → 正在做什麼 → 現在狀態

診斷 uv system-configuration panic → 用最小 CLI seam 分離 cache、sync、network/proxy 與 Python runtime → `READY TO DISPATCH`

## Root Question

為什麼同一個 task-local UV cache 與已建立的 `.venv` 在控制面 prepare 可正常完成，但正式 Codex sandbox task 執行 `uv run --frozen ...` 時，會在 Python 啟動前因 macOS `system-configuration` NULL object panic；哪個最小、可移植且 fail-closed 的命令契約能避免此 panic？

## 已確認事實

- cycle 2 正式 task：thread `01a01dfb-a7b3-73f1-926c-887ae97f7a62`，exact source `a1c1500da7b5cf61a908868e8a81a283c22679de`。
- 控制面以 task-local `UV_CACHE_DIR` 成功建立 `.venv`、安裝 locked dependencies並完成 CodeGraph index；外接硬碟 cache 權限 blocker 已被繞開。
- 正式 task 唯一 generator 命令在 Python 啟動前失敗，log 為：

```text
thread 'main2' panicked at system-configuration-0.6.1/src/dynamic_store.rs:154:1:
Attempted to create a NULL object.
thread 'main' panicked at uv/src/lib.rs:2629:10:
Tokio executor failed, was there a panic?
```

- cycle 2 未修改 tracked files、未產 current receipt、未 commit、production mutation 為 0；禁止回該 task 重跑。
- Ai Core 已定性外接 cache 問題為本機 environment configuration；本卡只處理其後暴露的 sandbox 內 uv panic，不改 Ai Core canonical contract。

## 可證偽假說

1. `H-UV-01`：Python／`.venv` 本身正常，panic 只發生在 `uv run` runtime boundary。若 `.venv/bin/python -V` 成功而最小 `uv run` RED，支持此假說。
2. `H-UV-02`：uv 在 frozen run 仍初始化 network／proxy system configuration；若只加 `--offline` 即 GREEN，則 panic 位於 network/proxy initialization。
3. `H-UV-03`：panic 位於 uv sync／environment reconciliation；若 `--offline` 仍 RED、只改為 `--no-sync` 即 GREEN，則 sync boundary 為主因。
4. 若 baseline RED、三次 uv-run 均非同症狀，或 GREEN 無法重現，根因維持 `UNKNOWN`，不得為了得到答案擴大矩陣。

## 唯一 frontier slice

### `SLICE-UV-PANIC-MINIMAL-RCA`

- `traces_to`: `H-UV-01`, `H-UV-02`, `H-UV-03`
- `blocking_edges`: 正式 worktree 必須由本卡 commit 建立；控制面 prepare 必須用 task-local cache建立 locked `.venv`；正式 task activation 後才能執行 bounded matrix。
- `frontier`: 先保存 runtime identity與非敏感環境摘要，再依下列順序執行；每一步只在前一步提供對應證據時繼續。

## Bounded red／green matrix

所有 log 寫入 `.work/CARD-PANTHEON-UV-SYSTEM-CONFIGURATION-PANIC-RCA-20260820/`。不得輸出完整環境或任何 secret；只記錄 `CODEX_SANDBOX`、`CODEX_SANDBOX_NETWORK_DISABLED`、`UV_CACHE_DIR`、`UV_LINK_MODE` 是否存在及安全值。

1. Baseline：確認 exact HEAD、clean、`.venv/bin/python` 可執行、task-local cache 可寫；執行 `.venv/bin/python -V`。只用於分層，不得執行 generator。
2. RED：

   ```bash
   UV_CACHE_DIR="$PWD/.work/CARD-PANTHEON-UV-SYSTEM-CONFIGURATION-PANIC-RCA-20260820/runtime/uv-cache" \
   RUST_BACKTRACE=1 \
   uv run --frozen python -V
   ```

   相同 `system-configuration NULL object`／Tokio panic 才算有效 RED。若未重現，保存差異並停止，不以 generator 補做 RED。
3. `H-UV-02` 單變數：保持其他條件一致，只加入 `--offline`。若 GREEN，重複完全相同命令一次確認穩定後停止；第二次 GREEN 不計入失敗停損。
4. 只有 `--offline` 仍為相同 RED 時，執行 `H-UV-03`：回到 RED 參數，只加入 `--no-sync`。若 GREEN，重複完全相同命令一次確認穩定後停止。
5. RED、offline、no-sync 三次皆出現相同 panic即停止；不得第四種變體、不得換 uv 版本、不得改 proxy／network／sandbox。

## 需求與成功準則

- `FR-RCA-01`：RCA 必須以非 generator 的 `python -V` observable seam 重現目標 uv panic。
- `FR-RCA-02`：direct venv Python baseline與 uv-run 結果必須分開記錄，不能把「Python 可跑」誤稱 generator 可跑。
- `FR-RCA-03`：每次實驗只改一個 uv flag，輸出 exact command、exit code、panic signature digest 與結論。
- `FR-RCA-04`：不得依賴外接硬碟 cache、全域設定變更、writable-root 擴張或 production mutation。
- `SC-RCA-01`：至少一個假說有明確 PASS／FALSIFIED 證據。
- `SC-RCA-02`：若取得 GREEN，能給 cycle 3 一個唯一、最小的 generator 命令差異，並說明為何不是降低 readiness gate。
- `SC-RCA-03`：若無 GREEN，輸出 exact blocker、已耗用三次 uv-run 停損與下一個需要 Ai Core／Codex runtime owner回答的問題。
- `SC-RCA-04`：artifact、logs與summary無 secret；tracked diff僅限 ownership，`git diff --check`通過。

## 交付

- `artifacts/fortune_council/four_lane_runtime_execution/uv_system_configuration_rca_20260820/rca.md`
- RED／各 hypothesis command、exit code、signature digest與完整 local-only log path。
- runtime：uv version、Python version、sandbox/network flags、task-local cache path、exact HEAD。
- verdict：`OFFLINE_GREEN / NO_SYNC_GREEN / NON_REPRODUCIBLE / BLOCKED_UNKNOWN`。
- cycle 3 建議：只能是一個已在本卡重現 GREEN 的最小命令差異；不得執行 readiness generator。
- 只有 evidence 契約完整才提交 candidate，回報完整 SHA與 clean state；不得自行整合。

## 停損

- 最小 RED 無法重現：保存差異，回 `NON_REPRODUCIBLE` 停止。
- 同一 panic 在 RED、offline、no-sync 連續三次出現：回 `BLOCKED_UNKNOWN` 停止，不做第四次。
- 任一步需要改 source／config、下載新 uv、放寬 sandbox、改外接硬碟或執行 generator：`BLOCKED / SCOPE_EXPANSION`。
- 任何 readiness／production mutation 立即停止並保全現場。

## 正式 task 初始 prompt 核心契約

```text
你負責 CARD-PANTHEON-UV-SYSTEM-CONFIGURATION-PANIC-RCA-20260820，role=diagnostic、cycle=1。只診斷正式 Codex sandbox 內 uv run 在 Python 啟動前的 macOS system-configuration NULL object panic。禁止執行任何 readiness generator、修改 source/tests/rules/config/workflow/Ai Core/Codex/shell環境、變更外接硬碟或sandbox、碰 production。控制面先用本 task 的 local UV cache建立 locked .venv；activation 後按卡片 bounded matrix執行：direct .venv Python baseline、一次最小 RED、只加 --offline、必要時只加 --no-sync；同一 panic三次即停。每次保存 exact command、exit、backtrace/signature digest。取得 GREEN需以完全相同條件再驗一次，然後只交付 RCA artifact與cycle 3最小命令差異，不得跑 generator。tracked diff只能在ownership，git diff --check通過後提交 evidence candidate並回完整SHA；不得整合或宣稱 readiness READY。
```
