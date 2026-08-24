# V0386 source-contract receipt

## 結論

- CodeGraph：已嘗試以 worktree 與明確 `projectPath` 查詢；worktree 沒有 `.codegraph`，服務回報未初始化，因此依契約退回受影響檔案的限域 `rg`。
- production mutation：`0`；remote access：`0`；本卡未讀取 production path。
- readiness contract：target generation readiness 不是 apply 前必要輸入，而是 `apply` 的 `STAGE_INSTALLED` 輸出。
- Rule24 contract：正式入口是 `run_capacity_proof_evidence_bundle`（two-cycle fresh harness）及 `produce_signed_capacity_evidence`；目前沒有可由 argv 直接重現完整 fresh producer bundle 的 repo CLI。

## 來源與精確定位

| 來源 | 證據 |
|---|---|
| `scripts/pantheon_content_runtime_promotion.py:452-475` | `plan` 只讀 current stage tree digest；沒有讀 target generation readiness directory。 |
| `scripts/pantheon_content_runtime_promotion.py:478-495` | plan 把 readiness acknowledgement 與 barrier 列為 `STAGE_INSTALLED` write-set。 |
| `scripts/pantheon_content_runtime_promotion.py:611-626` | `apply` 依序寫 actor、manifest，再呼叫 stage installer。 |
| `scripts/pantheon_content_runtime_promotion.py:665-674` | `_install_private_stage` 建立 `readiness/<target_generation>`、寫各 service ack、啟用 barrier。 |
| `scripts/pantheon_content_runtime_promotion.py:681-700` | postcheck 才讀取並驗證 readiness files 與 barrier。 |
| `scripts/pantheon_content_runtime_promotion.py:707-735` | rollback 先移除新 stage/barrier，再還原 backup；不存在的 target readiness 不應先手造。 |
| `scripts/pantheon_writer_vnext_runtime_activation_capacity.py:466-706` | formal Rule24-compatible two-cycle harness；含 host reserve、project bytes/files、RSS/swap、reclaim、projection、stop-loss。 |
| `scripts/pantheon_writer_vnext_runtime_activation_capacity.py:864-955` | exact-byte evidence bundle，固定 `capacity-receipt.json` 與兩個 cycle measurements，並 fail closed 於 drift。 |
| `scripts/pantheon_rule24_signed_capacity_evidence.py:372-470` | fresh bundle 後以正式 Rule24 DSSE producer 綁定 policy、兩 cycle 與 capacity receipt。 |
| `scripts/pantheon_rule24_dsse_attestation.py:1016-1099` | 只有 DSSE `produce/verify` CLI；沒有呼叫 capacity two-cycle producer 的 CLI。 |
| `tests/test_pantheon_content_runtime_promotion.py:191,558-608` | plan zero-write、capacity preflight fail-closed、apply failure/rollback matrix。 |
| `tests/test_pantheon_writer_vnext_runtime_activation_capacity.py:106-456` | two-cycle/reclaim、exact-byte bundle、artifact drift、budget/negative matrix。 |
| `tests/test_pantheon_rule24_signed_capacity_evidence.py:246-532` | signed producer、byte drift、domain failure、replay 與 CLI verify fail-closed。 |

## V0385 blocker 判定

V0385 `gate-summary.json` 的 `target_private_stage_readiness=BLOCKED` 是 **過早 gate / preflight contract bug**：它把 apply 的輸出當成 apply 前輸入。`rule24_fresh_current_receipt=BLOCKED` 則是真實 fresh-evidence 缺口。V0383 的 plan/argv/digests 僅是分析基線，不是本次授權。

## 正確順序

1. apply 前：fresh Rule24 bundle、source/actor/manifest/current-stage/queue/state no-drift、authorization 與 protected tripwire。
2. apply：`PREPARED → ACTOR_PROMOTED → MANIFEST_WRITTEN → STAGE_INSTALLED`；由正式 `_install_private_stage` 建立 target readiness 與 barrier。
3. postcheck：讀取新 readiness/barrier，連同 actor、manifest、queue 與 capacity receipt 驗證。
4. failure：依既有 rollback order 還原；不得把 missing pre-apply target readiness 當作 drift 而手造。

## 裁決

`BLOCKED`：preflight 修正方向已明確，但 fresh Rule24 producer 缺少可由命令列直接重現的正式入口，且本次不得執行 production apply 或建立 production readiness；不能發出可立即核准的 exact production authorization。
