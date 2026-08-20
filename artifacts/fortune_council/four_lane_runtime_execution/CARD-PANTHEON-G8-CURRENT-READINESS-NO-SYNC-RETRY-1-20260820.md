---
id: CARD-PANTHEON-G8-CURRENT-READINESS-NO-SYNC-RETRY-1-20260820
chain_id: PANTHEON-G8-CURRENT-READINESS-20260819
parent_card_id: CARD-PANTHEON-G8-CURRENT-READINESS-RECEIPT-RETRY-20260820
role: verification
cycle: 3
status: ready
type: capability_readiness_receipt
thickness: standard
risk: medium
model: gpt-5.6-terra
reasoning: medium
model_reason: 規格與驗收契約固定，唯一 runtime 差異已由 RCA 連續驗證；以 standard verification 使用 Terra medium，無架構岔路。
ownership:
  - artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness/**
  - .work/CARD-PANTHEON-G8-CURRENT-READINESS-NO-SYNC-RETRY-1-20260820/**
forbidden_scope:
  - 修改 scripts、tests、rules、config、workflow、Ai Core、Codex、sandbox 或既有 G8 卡
  - 修改全域 UV cache、外接硬碟 ACL 或 macOS privacy
  - production、publish、tag、push、deploy、schedule 或 LaunchAgent
  - 第二次生成、fallback command、direct Python、現場修補或另開 Repair
verification:
  - 唯一生成命令 exit 0 且 readiness-summary status READY
  - capability PASS、capacity PASS、兩週期、official gate READY
  - missing-step official gate BLOCKED 且 canary_created false
  - diff 僅限 ownership、git diff --check 通過、candidate commit 後 worktree clean
evidence_path: artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness/
---

# G8 current readiness receipt cycle 3：`--no-sync`

## 工作名稱 → 正在做什麼 → 現在狀態

驗證 G8 四線正式入口 cycle 3 → 以已驗證的 `uv --no-sync` runtime seam 重建 current non-production receipt → `READY TO DISPATCH`

## Root Question

在不改 generator、source、驗收門檻或 production 的前提下，使用 task-local `UV_CACHE_DIR` 並在既有 frozen `uv run` 加入唯一已驗證差異 `--no-sync`，current source 是否能產出可驗收的 APF-004 capability／capacity／official readiness package？

## 已確認證據

- cycle 2 在 Python generator 啟動前觸發 `system-configuration` NULL object panic，無 candidate、無 tracked diff、零 production mutation。
- RCA candidate `847923d3720dbf338d51981e1cf0daee6ec992c2` 已整合為 main commit `742cacd99b`。
- direct `.venv/bin/python -V` 成功；`uv run --frozen python -V` 與加入 `--offline` 都 exit 101。
- `uv run --frozen --no-sync python -V` 連續兩次 exit 0；最小 GREEN 差異已鎖定為 `--no-sync`。
- 本卡不宣稱 readiness 已通過；必須由 cycle 3 current evidence 決定。

## 成功準則

- 七段 capability 由正式 dry-run seam 產生；正向 `PASS`、負向 `BLOCKED`，identity／correlation 一致。
- capacity receipt 含兩週期、cleanup、projection 與 stop-loss，結果 `PASS`。
- official gate 對 current receipt 回 `READY`，對 missing-step fixture 回 `BLOCKED`。
- `readiness-summary.json` 為 `READY`，`capacity_cycles=2`，所有 production mutation flags 為 `false`。
- candidate 只含 ownership 內 evidence；`git diff --check` 通過且 worktree clean。

## 唯一生成命令

```bash
cd <repo-root>
mkdir -p .work/CARD-PANTHEON-G8-CURRENT-READINESS-NO-SYNC-RETRY-1-20260820/uv-cache
export UV_CACHE_DIR="$PWD/.work/CARD-PANTHEON-G8-CURRENT-READINESS-NO-SYNC-RETRY-1-20260820/uv-cache"
zsh -o pipefail -c 'uv run --frozen --no-sync python scripts/pantheon_content_capability_receipt.py apf-004-readiness --output-root artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness --ai-core-root <ai-core-root> 2>&1 | tee .work/CARD-PANTHEON-G8-CURRENT-READINESS-NO-SYNC-RETRY-1-20260820/generation.log'
```

`<ai-core-root>` 必須由 shared-resource locator 解析，不得寫入 committed artifact。`.venv` 必須在 activation 前由控制面以 locked dependencies 準備完成；`--no-sync` 禁止同步、安裝或變更環境。

## 執行前 preflight

1. 核對正式 task、thread ID、隔離 worktree、exact HEAD、cycle 3 identity、clean state 與實體卡片。
2. 核對 `.venv/bin/python`、`uv`、generator、Ai Core gate 與 task-local cache 可用。
3. CodeGraph query：`G8 current APF-004 readiness no-sync capability create run select publish transaction tag push capacity official gate`；失敗才限域 `rg`。
4. activation 前只可唯讀；activation 後只執行一次上方命令。

## 驗證與交付

1. 保存唯一命令的 exit code 與完整 generation log。
2. 驗證 summary、七段 capability、兩週期 capacity、official READY／BLOCKED、identity、digest、return code 與零 mutation。
3. 核對 diff 全在 ownership 且 `git diff --check` 通過。
4. 全部通過才提交 evidence candidate，回報 SHA、changed file count、summary digest、log path 與 clean state；不得自行整合或宣稱 production 已授權。

## 停損

- 唯一命令非零即保存 log 並停止，不得第二次生成。
- summary 非 READY、gate／capacity／identity 漂移、需要 sync／network／外部 cache：`BLOCKED`。
- 需要修改任何 forbidden scope：`BLOCKED / SCOPE_EXPANSION`。
- 不得用舊 receipt、單一測試、狀態文案或手改 JSON 補證。

## 正式 task 初始 prompt 核心契約

```text
你負責 CARD-PANTHEON-G8-CURRENT-READINESS-NO-SYNC-RETRY-1-20260820，role=verification、cycle=3。目標是在零 production mutation 下，以 task-local UV_CACHE_DIR 和已由 RCA 連續驗證成功的 uv run --frozen --no-sync，執行一次既有 APF-004 readiness generator，產出 current capability、兩週期 capacity 與 official gate receipts。禁止修改 scripts、tests、rules、config、workflow、Ai Core、Codex、sandbox、外接硬碟或 production；禁止第二次生成、fallback、direct Python、sync、network install 或另開 Repair。先完成卡片指定 preflight 與 CodeGraph query，收到 activation 後只執行唯一命令一次。非零或任一 gate／capacity／identity drift，保存完整 log 後立即停止。只有全部 READY／PASS、零 mutation、allowlist diff 與 git diff --check 通過，才提交 evidence candidate 並回報 SHA；不得整合、push、deploy 或宣稱 production READY。
```
