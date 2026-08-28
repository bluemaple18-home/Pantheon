---
schema_version: 1
title: Pantheon Acceptance B gen05 production entrypoint INVALID_RECEIPT RCA
date: 2026-08-28
owner: codex-rca-worker
status: COMPLETE
mode: RCA_ONLY
target_run: auto-i18n-ja-1414b75a404721e95e74
job_id: 61a83c341d39c882d5eed8ea23b7f805a89085e3
target_commit: 23eab63ea31031094aa084faee0e5ff65d326533
production_actor: 23eab63ea31031094aa084faee0e5ff65d326533
evidence_dir: artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_production_entrypoint_invalid_receipt_rca_20260828
---

# 目標

針對 retry1 的 production lane runner `INVALID_RECEIPT` 做 bounded RCA。
只回答 root cause 與可恢復邊界，不執行 production mutation。

# 禁止

- 不 retry production。
- 不 replacement execute。
- 不呼叫 provider。
- 不 push、promotion、deploy、publish、tag。
- 不建立 gen06。
- 不手改 production queue/state/registry。
- 不讀出 credential secret 值，只記 presence、路徑、權限、digest 與 identity。

# 必答

- 正式 i18n-new LaunchAgent plist/template/current installed plist/launchctl
  read-only identity。
- runner 所需 credential pool/allocator/model-route env 與 helper 差異。
- `process_once` production_enabled 判定與 env 缺失時 fallback path。
- provider/network attempt=0 是否成立。
- primary verdict：OPERATOR_ENTRYPOINT_MISMATCH 或
  RUNTIME_FORMAL_TRANSPORT_GUARD_GAP 或其他。
- last success / first failing mechanism / durable invariant /
  authoritative owner / promotion-replacement boundary。
- 既有 failed external job replacement seam 是否能 read-only plan/preflight
  恢復此精確 `INVALID_RECEIPT`。
- why_not_less / why_not_more / do_not_absorb。
- DATA_RESIDUE_ONLY 還是需要唯一 bounded Repair。
