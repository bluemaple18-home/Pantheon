---
id: CARD-PANTHEON-G8-V0370-RULE24-CURRENT-TARGET-ENTRYPOINT-20260824
chain_id: PANTHEON-G8-V0370-PRODUCTION-ADOPTION-RESET-READINESS-20260822
role: rule24-current-target-entrypoint-implementer
status: ready
type: implementation
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
required_base_ref: main
required_base_sha: c0e39a4e87061065268038e1095dda55ce201a96
ownership:
  - scripts/pantheon_writer_vnext_runtime_activation_capacity.py
  - tests/test_pantheon_writer_vnext_runtime_activation_capacity.py
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0370-RULE24-CURRENT-TARGET-ENTRYPOINT-20260824-RESULT.md
  - artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_rule24_current_target_entrypoint_20260824/**
forbidden_scope:
  - production、launchctl、plist、runtime、queue、state、transaction、stage 或 barrier mutation
  - remote Git query、fetch、pull、push、tag、branch/ref mutation
  - promotion apply、finalize、rollback、Publisher reset、activation、canary、deploy、schedule
  - 修改其他 source、tests、config、registry、metadata 或既有 evidence
---

# G8 v0.3.370 Rule 24 current-target formal entrypoint

## 工作名稱 → 正在做什麼 → 現在狀態

Rule 24 current-target entrypoint → 沿用既有 capacity proof 能力，補上正式 target-bound、fail-closed machine-readable gate → `READY / IMPLEMENTATION ONLY`。

## Root Question

能否不建立第二套 capacity workflow，讓既有 Rule 24 能接收 fresh post-adoption runtime receipt、target identity/correlation 與兩週期量測，輸出可供 production authorization 使用的 `PASS`／`NO-GO` receipt？

## Confirmed Blocker

既有 `run_capacity_proof` 僅產生 `synthetic-non-production` proof，correlation 固定為 `corr-ra-slice-005-cycle-*`，無法證明本次 adoption target：

- source SHA：`5a9103785ebfc8d5a28fa8188def6069beb12d88`
- manifest digest：`644fad69760b7b05f0256bd3fa65383dd44f8a759db166efdde1d912fc6d602d`
- runtime digest：`5554e075b0a6dcf97dd1cf431544c3456677b5d81174dcb8d660566dd82d5c92`
- generation：`g35-5a9103785e-adoption-auth-20260824`
- correlation：`g8-v0370-5a9103785e-adoption-auth-20260824`

不得把 synthetic proof 改名冒充 production evidence。

## Existing Capability First

1. Source decision 前查主工作區 CodeGraph。
2. 優先擴充 `scripts/pantheon_writer_vnext_runtime_activation_capacity.py` 的既有 validation、measurement、stop-loss、blocked receipt 與 deterministic writer。
3. 若現有 public function 可合法組合，直接沿用；禁止新造平行 harness、第二套 truth 或 adapter workflow。
4. 正式入口必須純計算／檔案輸入輸出，可在 temporary fixture root 測試；不得讀寫 live production。

## Functional Contract

### Inputs

正式 entrypoint 必須顯式接收並驗證：

- fresh runtime/capacity receipt 路徑與 digest；
- source SHA、manifest digest、runtime identity digest、generation、correlation id；
- 兩個有序 cycle measurements；
- growth measurement、monitoring、automatic stop-loss evidence；
- output receipt path；
- freshness boundary（timestamp/age 或等價既有契約）。

不得從 ambient production 路徑或環境偷偷推導 authority。

### PASS output

Machine-readable JSON 至少包含：

- schema/version、status=`PASS`、mode=`current-target-formal`；
- 完整 target identity 與 correlation；
- input receipt digest、兩週期 measurement digests；
- growth/monitoring/automatic-stop-loss 結果；
- deterministic authorization digest；
- `production_mutation=false`、`canary_created=false`。

### NO-GO output

任何 missing/stale/digest drift/identity mismatch/correlation mismatch/cycle 非兩個或無序/growth 未實測/monitoring 缺失/automatic stop-loss 缺失，都必須：

- fail closed；
- 產生 machine-readable `NO-GO` receipt 與穩定 reason code；
- 不啟動下一 cycle、不執行 cleanup production data、不改 external state；
- 不產生 `PASS` artifact。

### Compatibility

- 既有 synthetic entrypoint 與 receipts 保持相容。
- 新正式模式必須由顯式 API/CLI mode 觸發，不能改變既有 synthetic 預設語意。

## Tests

至少覆蓋：

1. exact target/correlation＋兩週期＋完整 Rule 24 evidence → deterministic PASS。
2. 相同 inputs 重跑 → authorization digest 相同。
3. stale receipt。
4. receipt digest drift。
5. source/manifest/runtime/generation/correlation 任一 mismatch。
6. cycle 缺少、超量、亂序或重複。
7. growth 未證明。
8. monitoring 缺失。
9. automatic stop-loss 缺失或未觸發。
10. NO-GO 不啟動下一 cycle、不 external cleanup、不 production mutation。
11. 既有 synthetic tests 不退化。

## Verification

- 受影響 tests 全過。
- JSON/AST parse。
- `git diff --check`。
- ownership-only。
- 禁止 production probe；測試只用 temporary fixture roots。
- remote query count `0`；production mutation `false`；canary created `false`。

## Delivery

- 單一 candidate commit，parent 精確為 `c0e39a4e87061065268038e1095dda55ce201a96`。
- 只改 ownership。
- 回報 candidate、tests、正負 receipts、remaining risks。
- 不整合、不 push、不 tag、不執行 production。
