---
id: CARD-PANTHEON-G8-CURRENT-READINESS-RECEIPT-20260819
chain_id: PANTHEON-G8-CURRENT-READINESS-20260819
parent_card_id: CARD-PANTHEON-G8-FOUR-LANE-PRODUCTION-CANARY-20260818
role: verification
cycle: 1
status: ready
type: capability_readiness_receipt
thickness: standard
risk: medium
model: gpt-5.6-terra
reasoning: medium
model_reason: 正式入口與唯一生成命令已固定，但需跨七段 capability、兩週期 capacity 與 official gate 核對；使用 Terra medium 節省成本，不使用 Sol。
ownership:
  - artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness/**
  - .work/CARD-PANTHEON-G8-CURRENT-READINESS-RECEIPT-20260819/**
forbidden_scope:
  - 修改 scripts、tests、rules、config、workflow 或既有 production canary 卡
  - production、publish、tag、push、deploy、schedule、LaunchAgent staging/activation
  - 手改 queue、transaction、plist、barrier、runtime live state 或 readiness JSON 冒充生成結果
  - 第二次生成、現場修補、fallback command、擴充 allowlist 或另開 Repair
verification:
  - 唯一生成命令 exit 0且readiness-summary status READY
  - capability PASS、capacity PASS、兩週期、official gate READY
  - missing-step official gate BLOCKED且canary_created false
  - diff僅限ownership、git diff --check通過、candidate commit後worktree clean
evidence_path: artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness/
---

# G8 current readiness receipt

## 工作名稱 → 正在做什麼 → 現在狀態

驗證 G8 四線正式入口 → 以 current source 重建 non-production capability／capacity package → `READY TO RUN`

## Root Question

目前 main 是否能在零 production mutation 下，以同一條 synthetic execution line 證明 `create → run → select → publish → transaction → tag → push`，並同時通過兩週期容量證據與 official readiness gate？

## 已鎖定事實

- 上一張 Repair 已整合到 main：`c05ae6967d`。
- 16-file regression suite：`605 passed, 1 warning`。
- 本卡只更新既有 APF-004 readiness evidence package；不修改 source 或 tests。
- production、publish、tag、push、deploy、schedule、activation 均未授權。

## 需求與成功準則

- `FR-RDY-01`：七段 capability 必須由既有正式 dry-run seam 產生，同一 execution line／correlation／actor／runtime identity 串接，正向 `PASS`、負向 `BLOCKED`。
- `FR-RDY-02`：capacity receipt 必須包含兩週期、cleanup、projection 與 stop-loss 證據，結果 `PASS`。
- `FR-RDY-03`：official readiness gate 對 current receipt 回 `READY`，對 missing-step fixture 回 `BLOCKED`。
- `SC-RDY-01`：`readiness-summary.json` 為 `READY`，`canary_created=false`、`production_mutation=false`。
- `SC-RDY-02`：candidate 只含 evidence ownership，無 source/test/config diff，worktree clean。

## 唯一 frontier slice

### `SLICE-RDY-CURRENT-PACKAGE`

- `traces_to`: `FR-RDY-01`, `FR-RDY-02`, `FR-RDY-03`, `SC-RDY-01`, `SC-RDY-02`
- 先確認 clean worktree、exact HEAD、`uv`、`<ai-core-root>/scripts/production_canary_readiness_gate.py` 與生成入口存在。
- CodeGraph task-semantic query：`G8 current APF-004 readiness capability receipt create run select publish transaction tag push capacity official gate`；無 provider／無結果才以限域 `rg` 確認生成入口與 summary schema。
- 僅執行一次下方命令，完整 stdout/stderr 以 `zsh -o pipefail` 與 `tee` 保存。
- 驗證 summary、positive/negative receipts、capacity cycles、official ready/blocked receipts與 ownership diff。
- 結果 `READY` 才提交 evidence candidate；結果 `BLOCKED` 則保留現場與 log、停止，不重跑、不修補。

## 唯一生成命令

```bash
cd <repo-root>
mkdir -p .work/CARD-PANTHEON-G8-CURRENT-READINESS-RECEIPT-20260819
zsh -o pipefail -c 'uv run --frozen python scripts/pantheon_content_capability_receipt.py apf-004-readiness --output-root artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness --ai-core-root <ai-core-root> 2>&1 | tee .work/CARD-PANTHEON-G8-CURRENT-READINESS-RECEIPT-20260819/generation.log'
```

`<ai-core-root>` 必須由本機 shared-resource locator 解析，不得把絕對路徑寫入 committed artifact。

## 驗證與交付

1. `readiness-summary.json`：`status=READY`、七 capabilities、`capacity_cycles=2`、`official_gate_status=READY`、`official_blocked_fixture_status=BLOCKED`、所有 mutation flags為 `false`。
2. `official-gate-ready.json` 與 `official-gate-blocked.json` 分別為 `READY/BLOCKED`，return code符合 gate 契約。
3. `git diff --name-only` 全部位於 ownership；`git diff --check` 通過。
4. 提交 current evidence candidate，回報 candidate SHA、changed file count、summary digest、generation log與 clean state；不得自行整合或宣稱 production 已授權。

## 停損

- 唯一生成命令非零、summary 非 `READY`、gate／capacity／identity 任一漂移：保存證據停止。
- 需要第二次執行、修改 source/test/config、production mutation或外部 write：`BLOCKED / SCOPE_EXPANSION`。
- 不得以舊 receipt、單一測試、狀態文案或手改 JSON 補齊缺口。
