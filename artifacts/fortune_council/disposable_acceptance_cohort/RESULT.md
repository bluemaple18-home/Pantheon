# C-C/T disposable acceptance cohort result

狀態：`PRE_FREEZE_REPAIR_READY`

- 新增一次性 acceptance plist renderer 與 injected one-shot orchestration；不建立 scheduler、daemon 或第二 runtime。
- seven plists 僅在 isolated acceptance root；Coordinator 使用四個 exact run IDs 與 `--external-workers-only`，四 lane 使用 sealed replay command，Publisher outer barrier 從啟動即 activation-only。
- pre-freeze audit repair：readiness 改由 service emulator（對應既有 barrier-exec）在 launch callback 自行寫 ack；controller 只 poll/activate。queue/state/log 改為 acceptance strict descendants，並拒絕與 production roots 的 ancestor/descendant overlap。
- filesystem fingerprint 改為 lstat tree snapshot，另綁 injected service-state digest；teardown 只 bootout 實際 launched services、清除已知 owned residue，並在成功後才寫 one-shot evidence receipt。
- fake launcher tests 覆蓋 seven-service labels、7/7 readiness barrier、launch failure / partial readiness teardown、stale second-run ack、bootout failure、unknown residue、原子 projection failure、production filesystem/service-state fingerprint drift、每類 child argv token mutation，以及 provider/public/push/deploy command absence。
- PASS receipt 僅在七個實際 launch 與七個成功 bootout、已知 owned residue 清除、production filesystem/service-state fingerprint equality 後 create-new 寫入；receipt 綁 before/after digests、manifest、generation、identity、launch/bootout accounting。
- second pre-freeze repair：production proof 強制 `queue`、`ledger`、`publisher`、`public` 四 root exact keyset、canonical owner-safe/disjoint identity mapping；缺漏、extra、substitution overlap 一律在 renderer mutation 前拒絕。
- `BLOCKED_C_C_SESSION_FRESHNESS_CONTRACT` repair 已移除第三 `session_token` 與任何 shared ack/barrier schema 擴張；改由 externally pinned immutable session plan 的 fresh acceptance generation 作為 pre-activation authority，既有 activation token digest 仍只代表 post-readiness cohort authority。
- session plan 嚴格綁 session id/nonce、actor SHA、manifest/runtime identity、七 labels、四 exact runs/bundle digests、Publisher selector、acceptance/disposable/production roots。generation-specific readiness/barrier/lock/evidence/plists 不可 reuse；receipt 綁 plan path/digest、ack/activation digests 與 teardown terminal proof。
- review evidence refs：R2 `6897bb5d54a647b005b1422b207039f856ef232c`；C-A `1ea615ad4096077a2b82af86a2effb0c487c582d`；C-B `fa2e6cb65d5f57209fd3aebb3020246549ce2bc6`。
- 未 commit、push、launchctl、provider、production/public mutation 或 Gate D-E execution。此為 repair-ready，不主張 REVIEW_GO。
