---
id: CARD-PANTHEON-G8-CURRENT-READINESS-NO-SYNC-CYCLE-4-20260820
chain_id: PANTHEON-G8-CURRENT-READINESS-20260819
parent_card_id: CARD-PANTHEON-G8-CURRENT-READINESS-NO-SYNC-RETRY-1-20260820
role: verification
cycle: 4
status: ready
type: capability_readiness_receipt
thickness: standard
risk: medium
model: gpt-5.6-terra
reasoning: medium
model_reason: 規格固定；preactivation repair 與 re-review 已 GO，只需在新 source 重建 current evidence，使用 Terra medium。
ownership:
  - artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness_cycle_4_20260820/**
  - .work/CARD-PANTHEON-G8-CURRENT-READINESS-NO-SYNC-CYCLE-4-20260820/**
forbidden_scope:
  - 修改 scripts、tests、rules、config、workflow、Ai Core、Codex、sandbox 或既有 evidence
  - production、publish、tag、push、deploy、schedule、LaunchAgent、sync 或 network install
  - 第二次生成、fallback command、direct Python、現場修補或另開 Repair
verification:
  - 唯一生成命令 exit 0 且 readiness-summary status READY
  - capability PASS、capacity PASS、兩週期、official gate READY
  - missing-step official gate BLOCKED 且 canary_created false
  - diff 僅限 ownership、git diff --check 通過、candidate commit 後 worktree clean
evidence_path: artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness_cycle_4_20260820/
---

# G8 current readiness receipt cycle 4

## 工作名稱 → 正在做什麼 → 現在狀態

重建 G8 四線 current readiness cycle 4 → 在 preactivation repair `GO` 後以 `uv --no-sync` 產生新 source receipt → `READY TO DISPATCH`

## Root Question

整合 read-only selector isolation 與 evidence-path guard 後，current source 是否仍能產出七段 capability、兩週期 capacity 與 official readiness 全部可驗收的零 production mutation package？

## Source Authority

- preactivation repair：`7a4cd32192`。
- Reviewer re-review：`GO`，evidence 整合為 `3e870aec24`。
- 本卡只驗 current source；不重用 cycle 3 receipt，不宣稱 production 已授權。

## 唯一生成命令

```bash
cd <repo-root>
mkdir -p .work/CARD-PANTHEON-G8-CURRENT-READINESS-NO-SYNC-CYCLE-4-20260820/uv-cache
export UV_CACHE_DIR="$PWD/.work/CARD-PANTHEON-G8-CURRENT-READINESS-NO-SYNC-CYCLE-4-20260820/uv-cache"
zsh -o pipefail -c 'uv run --frozen --no-sync python scripts/pantheon_content_capability_receipt.py apf-004-readiness --output-root artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness_cycle_4_20260820 --ai-core-root <ai-core-root> 2>&1 | tee .work/CARD-PANTHEON-G8-CURRENT-READINESS-NO-SYNC-CYCLE-4-20260820/generation.log'
```

`<ai-core-root>` 由 shared-resource locator 解析；不得寫入 committed artifact。activation 前由控制面準備 locked `.venv`；`--no-sync` 禁止同步環境。

## Preflight

1. 核對 formal thread、獨立 worktree、exact HEAD、cycle 4、clean 與實體卡。
2. 核對 `.venv/bin/python`、`uv`、generator、Ai Core gate、task-local cache。
3. CodeGraph query：`G8 current APF-004 readiness capability create run select publish transaction tag push capacity official gate`；失敗才 bounded `rg`。
4. activation 後只執行一次唯一命令。

## 驗收

- summary `READY`；capability 七段 `PASS`。
- capacity `PASS` 且 `capacity_cycles=2`。
- official gate current=`READY`；missing-step=`BLOCKED`。
- `canary_created=false`；所有 production mutation flags=false。
- candidate 僅含新 evidence path；`git diff --check` PASS；worktree clean。

## 停損

- 唯一命令非零：保存 log，立即 `BLOCKED`，禁止第二跑。
- 任一 gate、capacity、identity drift 或需要 forbidden scope：`BLOCKED`。
- 不得 publish、push、deploy、啟動 canary或手改 receipt。

## 正式 task 初始 prompt 核心契約

```text
你負責 CARD-PANTHEON-G8-CURRENT-READINESS-NO-SYNC-CYCLE-4-20260820，role=verification、cycle=4。先 CodeGraph，失敗才 bounded rg。收到 activation 後只執行卡片唯一 uv run --frozen --no-sync 命令一次，輸出到 cycle 4 專屬 evidence path。禁止修改 source/tests/rules/config/workflow/Ai Core、禁止 sync/network/fallback/第二跑與任何 production mutation。驗 capability 七段 PASS、capacity 兩週期 PASS、official current READY、missing-step BLOCKED、canary false、allowlist diff與 git diff --check。全部通過才提交 evidence candidate；否則保存 log後 BLOCKED。不得 push、deploy或宣稱 production 已授權。
```
