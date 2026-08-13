# APF-004-REACTIVATION-REALIGN-PLAN-001

- 目標：把 preflight `NO-GO` 的 stage／manifest／runtime actor／capacity guard identity 漂移，收斂成一份可單次執行、可回滾、fail-closed 的 exact realignment payload；`traces_to: US-004, FR-012, FR-014, SC-001, SC-003, SC-008`。
- 輸入：integration `8fea7a47a86a97e0dd1eb6af94df1ba6056e7a17`；preflight evidence `396dd65c84`；已確認 stage=`5face6.../canary-79bd...`、manifest=`2b367c.../canary-038c.../actor 038c...`、runtime actor=`79bd...`、capacity guard=`EX_CONFIG` 指向 missing legacy actor。
- 可做：CodeGraph 後限域讀 installer/runtime manifest/capacity guard 原始碼與已提交 evidence；只寫本卡與 `.ai/evidence/apf_004_reactivation_realign_plan_001.md`；列出 source→main/origin→runtime actor→manifest→private stage→zero-write gate→activation 的完整順序、exact identity/env/command schema、backup、rollback、stop-loss、expected receipts。
- 禁止：不得執行 merge/push/install/activate/bootstrap/kickstart/bootout、plist/manifest/runtime write、stage delete、capacity guard mutation、external model、publish/transaction/tag/deploy/schedule；不得產 secrets、本機絕對路徑或未驗證參數。不得用舊 stage/receipt 冒充新 generation。
- 驗收：回 `REALIGNMENT_PAYLOAD_READY | BLOCKED`，附 commit；READY 必須將 realignment 與 later activation 分成兩個 confirmation gates，證明每步可重入／失敗停止／不污染既有 evidence，並明示 `mutation_executed=false`。若 public CLI 缺可驗證入口，回唯一 source-gap remediation，不擴 scope。

## 停損

- 只准一次限域分析；不得重跑 live action。
- lineage 非 ancestry 不算 blocker；以 allowlist content equivalence 與 fixed SHA 判定。
- evidence gates：secret/path/binary scan、`git diff --check`；只提交卡與 evidence。
