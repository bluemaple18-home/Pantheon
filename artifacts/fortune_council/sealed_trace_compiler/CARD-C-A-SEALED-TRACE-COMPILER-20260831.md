# C-A sealed trace compiler

狀態：`CA_R2_IMPLEMENTATION_READY_FOR_FREEZE`

## 範圍

新增 `scripts/pantheon_sealed_trace_compiler.py` 與單元測試。只在 disposable staging copy 重用既有 editorial/translation Writer/Reviewer flow 與 outbox request builder，產生既有 R2 schema bundle；不改 Runner、Coordinator、installer、manifest、Publisher 或 pipeline。

## 不吸收

- 不新增 controller、runtime、queue writer、FSM、ledger 或 manifest schema。
- 不預測 deterministic branch；每個實際 trace entry 固定 `required=true`，budget 等於 entry count。
- 不執行 provider、activation、production 或 C-B。

## Why not less / why not more

source snapshot、actor authority、raw bundle evidence 的 strict validation 是讓 staging trace 可被後續 R2 runtime 重驗的最小邊界；沒有吸收任何 cohort scheduling 或 runtime state，因其不屬於 compiler authority。

## Freeze boundary

單元測試以 bounded `_git` monkeypatch 驗 production loop；worktree 含本次未 freeze 檔案，因此 clean actor integration 為 `NOT_RUN`。candidate freeze 後主線必須以 clean actor worktree 重跑 actor HEAD/base/clean validation。

R2 將 bundle 與 compile receipt 收斂為不可分割的 evidence artifact directory：所有 compiler publisher 必須先取得 owner-only sibling `O_EXCL` claim，再寫 0600 temp files、fsync files / temp dir / parent，最後發布 0700 directory；claim race 不覆寫也不刪除既有 claim。所有 source/staging/evidence parent/queue roots 的 canonical、owner、安全權限與 non-overlap 均在 copy 前驗證，copy 後、pipeline 前再重算 staging snapshot。
