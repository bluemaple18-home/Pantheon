# CARD-PANTHEON-G8-REGRESSION-RECEIPT-CLOSURE-20260818

## 五行派工契約

- 工作：為既有 G8 Repair candidate 補齊可持久保存的 16-file regression receipt。
- 範圍：回原正式 Repair thread／原 worktree；只驗證既有四檔 diff，不改 source、test 或契約。
- 禁區：禁止 production、push、tag、publish、LaunchAgent mutation、重建 thread／worktree、第三次盲重跑。
- 驗收：一次 suite 完整終態、durable log、`git diff --check`、無 debug marker；全綠才建立 candidate commit。
- 證據：`.work/CARD-PANTHEON-G8-REGRESSION-RECEIPT-CLOSURE-20260818/` 與 candidate SHA。

## Identity

- `chain_id`: `PANTHEON-G8-PREFLIGHT-SOURCE-CONTRACT-REPAIR-20260818`
- `role`: `verification-continuation`
- `cycle`: `1`
- `model`: `gpt-5.6-terra`
- `reasoning`: `low`
- `source_card`: `CARD-PANTHEON-G8-PREFLIGHT-SOURCE-CONTRACT-REPAIR-20260818`
- `reuse_thread`: `01a0156e-2888-7b73-8498-472e6ff172f4`

## 已知事實

- 原任務已證明 canonical 四測試 `4 passed`。
- 原任務既有未提交修改只應包含：
  - `scripts/agy_gemini_coordinator.py`
  - `scripts/pantheon_content_actor_recovery.py`
  - `scripts/pantheon_content_capability_probe.py`
  - `tests/test_pantheon_runtime_activation.py`
- 上一輪 16-file suite 因 terminal receipt 遺失而 `BLOCKED`；不是 source regression 結論。

## 執行契約

1. 先回報 `HEAD`、`git status --short`、四檔 diff 範圍；若出現第五個 tracked 修改檔，立即停止。
2. 建立 evidence 目錄；使用 `zsh -o pipefail` 搭配 `tee` 執行卡片原定 16-file suite，確保 stdout/stderr 持久保存。
3. 本卡只允許一次 suite execution。測試失敗或 harness／cell 遺失時保存現有 log 並停止，不再重跑。
4. Suite 全綠後執行 `git diff --check` 與 `rg -n '\\[DBG-'`；任何失敗都停止。
5. 僅在全部驗收通過後提交上述四檔，回報 candidate SHA、suite 數量、log 路徑與 clean state；不得自行整合。

## 停止條件

- 需要改 source/test、擴 allowlist 或變更驗收指令。
- Suite 非全綠、durable log 缺終態、同一命令被要求第二次執行。
- 發現 production／外部狀態 mutation。

