---
id: PANTHEON-G8-V0387-FRESH-RULE24-BUNDLE-CLI-20260824
status: ready
type: implementation
traces_to:
  - FR-V0387-CLI-001
  - FR-V0387-BOUNDARY-002
  - SC-V0387-TESTS-001
---

# PANTHEON G8 V0387 fresh Rule24 bundle CLI

## 工作名稱

V0387 fresh Rule24 bundle CLI

## 需求追溯

- `FR-V0387-CLI-001`：為既有 `run_capacity_proof_evidence_bundle` 提供正式、可重現的 command-line entrypoint，產 fresh two-cycle exact-byte bundle。
- `FR-V0387-BOUNDARY-002`：入口只寫 explicit output/evidence root與 task-owned sandbox；拒絕 production/runtime roots、symlink escape、缺欄與無上限 policy。
- `SC-V0387-TESTS-001`：public CLI happy path及 fail-closed cases有可重現測試，既有容量與 promotion tests不回歸。

## 依賴與 frontier

- 依賴：V0386 main evidence `a9dc6179aa`，已完成。
- blocking edges：fresh receipt執行卡、promotion replan卡、apply卡全部依賴 V0387 accepted integration。
- current frontier：只有 V0387。

## 目的

補上 V0386 找到的缺口：不改容量判斷核心，只替既有 two-cycle bundle API 增加薄 CLI，讓 operator 能以固定 argv在 task-owned sandbox產 fresh Rule24 bundle，之後再由既有 DSSE producer簽署／驗證。

## 實作契約

- source decision前查 CodeGraph；失敗才限域 `rg`。
- 先 RED：新增 public CLI行為測試，再最小 GREEN。
- 優先在 `scripts/pantheon_writer_vnext_runtime_activation_capacity.py` 增加薄 argparse入口；若 source證據顯示獨立 wrapper更安全，必須在結果說明。
- CLI只做參數解析、Path邊界檢查、呼叫既有 `run_capacity_proof_evidence_bundle`、輸出 machine-readable summary與明確 exit code；不得複製容量邏輯。
- 必填 inputs/outputs以既有 function signature與tests為準；不得猜 schema。
- output/evidence與cycle sandbox必須 explicit、可重算且禁止 overlap production actor/manifest/stage/queue/state/transactions/LaunchAgents。
- 無上限 policy、非 task-owned sandbox、symlink escape、missing input、artifact drift、second-cycle/cleanup failure須 fail closed且不碰 production。
- 不產 key、不簽 DSSE、不執行 promotion；只產 unsigned fresh bundle。

## 可改檔案

- `scripts/pantheon_writer_vnext_runtime_activation_capacity.py`
- `tests/test_pantheon_writer_vnext_runtime_activation_capacity.py`
- 本卡 result/evidence：
  - `CARD-PANTHEON-G8-V0387-FRESH-RULE24-BUNDLE-CLI-20260824-RESULT.md`
  - `g8_v0387_fresh_rule24_bundle_cli_20260824/`

## 禁止

- 禁止改 promotion、readiness、DSSE/signing核心、workflow/shared metadata或其他 tests。
- 禁止讀寫 production runtime、LaunchAgents或遠端。
- 禁止執行真實 fresh production receipt、apply、deploy、canary、activation、launchctl mutation。
- 禁止安裝工具、push、tag、派下一卡。

## 驗收

- RED→GREEN證據；CLI `--help`與happy path PASS。
- 至少覆蓋 production-root拒絕、symlink escape、invalid/unbounded policy、missing input、既有 drift/cleanup fail-closed。
- `tests/test_pantheon_writer_vnext_runtime_activation_capacity.py` PASS。
- `tests/test_pantheon_content_runtime_promotion.py` PASS。
- `python -m py_compile`、JSON parse、`git diff --check` PASS。
- 只改 allowlist；單一 commit；worktree clean；不 push。

## Verdict

只能是 `DELIVERED_CANDIDATE` 或 `BLOCKED`。
