---
id: CARD-PANTHEON-G8-CURRENT-READINESS-RECEIPT-RETRY-20260820
chain_id: PANTHEON-G8-CURRENT-READINESS-20260819
parent_card_id: CARD-PANTHEON-G8-CURRENT-READINESS-RECEIPT-20260819
role: verification
cycle: 2
status: ready
type: capability_readiness_receipt
thickness: standard
risk: medium
model: gpt-5.6-terra
reasoning: medium
model_reason: 規格、generator 與驗收契約均已固定，只需以 task-local UV cache 重跑一次正式 current receipt 並跨七段 capability、兩週期 capacity 與 official gate 驗收；使用 Terra medium，不升級 Sol。
ownership:
  - artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness/**
  - .work/CARD-PANTHEON-G8-CURRENT-READINESS-RECEIPT-RETRY-20260820/**
forbidden_scope:
  - 修改 scripts、tests、rules、config、workflow、Ai Core 或既有 G8 卡
  - 修改全域 UV cache、外接硬碟 ACL、macOS privacy 或 Codex sandbox
  - production、publish、tag、push、deploy、schedule、LaunchAgent staging/activation
  - 手改 readiness JSON、queue、transaction、plist、barrier 或 runtime live state冒充生成結果
  - 第二次生成、fallback command、現場修補、擴充 allowlist 或另開 Repair
verification:
  - 唯一生成命令 exit 0且readiness-summary status READY
  - capability PASS、capacity PASS、兩週期、official gate READY
  - missing-step official gate BLOCKED且canary_created false
  - diff僅限ownership、git diff --check通過、candidate commit後worktree clean
evidence_path: artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness/
---

# G8 current readiness receipt retry：task-local UV cache

## 工作名稱 → 正在做什麼 → 現在狀態

驗證 G8 四線正式入口 retry → 只改用 task-local UV cache 重建 current non-production receipt → `READY TO DISPATCH`

## Root Question

在不改 generator、source、驗收門檻或 production 的前提下，把 `UV_CACHE_DIR` 綁定到隔離 worktree 的可寫 task-local cache 後，current source 是否能成功產出可驗收的 APF-004 capability／capacity／official readiness package？

## 已確認事實

- cycle 1 正式 task 已依契約只執行一次生成命令，`uv` 在 Python generator 啟動前因外接硬碟共享 cache 權限失敗。
- cycle 1 沒有 current receipt、candidate、tracked diff 或 production mutation；原 task 已停止，禁止回原 task 重跑。
- blocker 位於 environment／permission boundary，不是已證明的 Publisher、四線、capacity 或 receipt generator 邏輯故障。
- cycle 1 parent base：`785f62325f0465a79803f82ac32a0d674cf4b98e`；cycle 2 的正式 task 必須以本 retry 卡 commit 為 exact HEAD，建立後再核對 SHA。
- 舊 tracked `readiness-summary.json` 雖顯示 READY，但不是 cycle 2 current 生成結果，不能作 acceptance。
- 使用者已將外接硬碟 UV cache 權限問題回報 Ai Core；該全域診斷不授權本卡修改 Ai Core 或外接硬碟設定。

## 需求與成功準則

- `FR-RDY-01`：七段 capability 必須由既有正式 dry-run seam 產生，同一 execution line／correlation／actor／runtime identity 串接，正向 `PASS`、負向 `BLOCKED`。
- `FR-RDY-02`：capacity receipt 必須包含兩週期、cleanup、projection 與 stop-loss 證據，結果 `PASS`。
- `FR-RDY-03`：official readiness gate 對 current receipt 回 `READY`，對 missing-step fixture 回 `BLOCKED`。
- `FR-RDY-04`：本 cycle 唯一環境差異為 `UV_CACHE_DIR` 指向 task-local `.work` 目錄；不得修改全域 cache 或降低 sandbox。
- `SC-RDY-01`：`readiness-summary.json` 為 `READY`，七 capabilities、`capacity_cycles=2`、official ready／blocked statuses 正確，所有 mutation flags 為 `false`。
- `SC-RDY-02`：candidate 只含 evidence ownership，無 source／test／config diff，`git diff --check` 通過且 worktree clean。
- `SC-RDY-03`：generation log 證明 task-local cache 生效，且不再存取外接硬碟 UV cache。

## 唯一 frontier slice

### `SLICE-RDY-TASK-LOCAL-UV-CACHE`

- `traces_to`: `FR-RDY-01`, `FR-RDY-02`, `FR-RDY-03`, `FR-RDY-04`, `SC-RDY-01`, `SC-RDY-02`, `SC-RDY-03`
- `blocking_edges`: cycle 1 已停止；本卡與 main/card commit 必須可由新正式 task 讀取；新 verification identity/cycle、隔離 worktree、CodeGraph task-semantic query 與 activation 必須完成。
- `frontier`: 新正式 task 驗證 clean worktree、exact HEAD、`uv`、generator、Ai Core gate 與 task-local cache path 後，只執行一次下方唯一命令。
- 不改 generator invocation、output root、Ai Core root locator、ownership、驗收門檻或停損；唯一差異是命令前建立並 export task-local `UV_CACHE_DIR`。
- 結果 `READY` 才提交 evidence candidate；非零、summary 非 READY 或任何 identity／gate／capacity drift，保存完整 log 後停止。

## 唯一生成命令

```bash
cd <repo-root>
mkdir -p .work/CARD-PANTHEON-G8-CURRENT-READINESS-RECEIPT-RETRY-20260820/uv-cache
export UV_CACHE_DIR="$PWD/.work/CARD-PANTHEON-G8-CURRENT-READINESS-RECEIPT-RETRY-20260820/uv-cache"
zsh -o pipefail -c 'uv run --frozen python scripts/pantheon_content_capability_receipt.py apf-004-readiness --output-root artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness --ai-core-root <ai-core-root> 2>&1 | tee .work/CARD-PANTHEON-G8-CURRENT-READINESS-RECEIPT-RETRY-20260820/generation.log'
```

`<ai-core-root>` 必須由本機 shared-resource locator 解析，不得把本機絕對路徑寫入 committed artifact。不得在唯一命令失敗後改用全域 cache、外部 runtime、direct Python、network install 或第二條命令補跑。

## 執行前 preflight

1. 正式 task、thread ID、worktree、branch、exact HEAD 與 verification cycle 2 identity 可查。
2. worktree clean；card 實體可讀；ownership 與 forbidden scope 已確認。
3. `UV_CACHE_DIR` 在唯一命令前解析到 `<repo-root>/.work/CARD-PANTHEON-G8-CURRENT-READINESS-RECEIPT-RETRY-20260820/uv-cache`，且該路徑可寫。
4. 不以讀取、修復或授權外接硬碟 cache 作為本卡 prerequisite。
5. CodeGraph task-semantic query：`G8 current APF-004 readiness task-local UV cache capability create run select publish transaction tag push capacity official gate`；provider 無結果／失敗才限域 `rg` 確認正式入口與 schema。

## 驗證與交付

1. 唯一生成命令 exit code 與完整 generation log。
2. `readiness-summary.json`：`status=READY`、七 capabilities、`capacity_cycles=2`、`official_gate_status=READY`、`official_blocked_fixture_status=BLOCKED`、所有 mutation flags 為 `false`。
3. capability positive／blocked receipts、兩週期 capacity receipts、`official-gate-ready.json` 與 `official-gate-blocked.json` 的 status、identity、digest 與 return-code 契約一致。
4. 核對 generation log 與 environment evidence：task-local `UV_CACHE_DIR` 生效，未存取 `<external-volume-root>/Caches/uv`。
5. `git diff --name-only` 全部位於 ownership；`git diff --check` 通過。
6. 只有全部 READY／PASS 才提交 current evidence candidate，回報 candidate SHA、changed file count、summary digest、generation log path與 clean state；不得自行整合或宣稱 production 已授權。

## 停損

- 唯一生成命令非零即保存完整 log 並停止；不得 retry 第二次。
- task-local cache 仍無法使用、uv 需要 network／外部 cache、summary 非 READY、gate／capacity／identity 任一漂移：`BLOCKED`。
- 需要修改 source、tests、config、Ai Core、外接硬碟權限、sandbox 或 production：`BLOCKED / SCOPE_EXPANSION`。
- 不得以舊 receipt、單一測試、狀態文案或手改 JSON 補齊缺口。
- 本 cycle 若再次出現相同 UV cache permission blocker，累計為第二次；同一 blocker 第三次即停止整條 retry fork。

## 正式 task 初始 prompt 核心契約

```text
你負責 CARD-PANTHEON-G8-CURRENT-READINESS-RECEIPT-RETRY-20260820，role=verification、cycle=2。目標是在全程零 production mutation 下，只把 UV_CACHE_DIR 指到新隔離 worktree 內的 task-local .work cache，執行一次既有 APF-004 readiness generator，產出 current capability、兩週期 capacity 與 official gate receipts。禁止修改 scripts、tests、rules、config、workflow、Ai Core、外接硬碟權限、sandbox、production，禁止回原 task、第二次生成、fallback 或 direct Python。先驗證 clean worktree、exact HEAD、card、task-local cache 可寫、正式 generator 與 Ai Core gate 存在，完成 CodeGraph 任務語意 query；然後只執行卡片鎖定的唯一生成命令一次。非零或任一 gate／capacity／identity drift，保存完整 log 後立即停止。只有 summary READY、七段 capability、兩週期 capacity、official READY/BLOCKED、零 mutation、allowlist diff 與 git diff --check 全部通過，才提交 evidence candidate並回報 SHA；不得整合、push、deploy或宣稱 production READY。
```
