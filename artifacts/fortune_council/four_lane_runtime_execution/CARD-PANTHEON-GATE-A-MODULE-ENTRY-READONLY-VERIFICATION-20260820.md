---
id: CARD-PANTHEON-GATE-A-MODULE-ENTRY-READONLY-VERIFICATION-20260820
status: ready
chain_id: PANTHEON-G8-PRODUCTION-READINESS-20260820
role: verification
cycle: 14
thickness: minimal
risk: low
model: gpt-5.6-luna
reasoning: medium
model_reason: 純唯讀、單一固定 CLI seam、明確 PASS/FAIL。
---

# Gate A 正式 module 入口唯讀複驗

## 目標

證明 Gate A 的正式 public CLI 必須以 module 方式啟動，並對上一張卡已產生的 authorization、authorization-state、exact argv artifacts 執行一次唯讀驗證。

## 已知事實

- 上一張卡誤用 `python scripts/pantheon_gate_a_governance.py`，在語意驗證前因 `ModuleNotFoundError: No module named 'scripts'` 停止。
- `tests/test_pantheon_gate_a_governance.py::test_public_cli_emits_machine_readable_receipt` 鎖定正式入口為 `python -m scripts.pantheon_gate_a_governance`。
- 上一張卡 production mutation 全為 0；不得把本卡視為 promotion 重試授權。

## 允許

- 讀取 source、tests 與上一張卡 evidence。
- 執行一次：`<venv-python> -m scripts.pantheon_gate_a_governance --repo-root ... --authorization ... --authorization-state ...`。
- 寫入本卡專屬 evidence 目錄與一個 evidence commit。

## 禁止

- 禁止修改 source、tests、config、workflow。
- 禁止 push、promotion plan/apply、restage、activation、canary、lane run、Publisher transaction、tag、publish。
- 禁止改用第二個驗證入口；第一次正式 module invocation 非 `READY` 即 `BLOCKED`。
- 禁止建立 replacement 或自動派下一張 production 卡。

## 驗證

1. CodeGraph 定位 public CLI seam；以原始碼／測試確認 `-m` 契約。
2. 上一張卡 authorization artifacts digest 與內容可讀。
3. 唯一一次正式 module invocation：exit 0 且 JSON `status == READY`。
4. 核對 remote、actor、manifest、stage、live seven 未變；production mutation 仍為 0。
5. `git diff --check`。

## 交付

- `VERIFIED / NO MUTATION` 或 `BLOCKED / NO MUTATION`。
- evidence 路徑：`.work/CARD-PANTHEON-GATE-A-MODULE-ENTRY-READONLY-VERIFICATION-20260820/`
- 回報完整 evidence commit SHA、CLI receipt SHA256、production mutation 計數。
