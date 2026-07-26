# Repair 1 RED → GREEN

## F1 stale production recovery

RED command：

```text
<local-only-python> -m pytest \
  tests/test_agy_gemini_outbox.py::test_production_pool_stale_recovery_never_retries_consumed_job -q
```

- RED: `3 failed`
- seams: crash before provider、during provider、after inbox response write。
- observed root cause: stale processing 沒有 durable per-job production attempt
  evidence，因此三案都回 outbox 並取得第二個 ordinal/provider attempt。
- GREEN: durable owner-only per-job marker 在 allocation 前落盤；stale recovery
  依 marker terminalize/archive，response 已存在時保留 inbox。
- GREEN command（連同 legacy recovery）: `6 passed`
- provider call count 在 recovery 前後不增加；無 retry、rotation 或第二 slot。

## F2 installer partial mutation

RED command：

```text
<local-only-python> -m pytest \
  tests/test_agy_gemini_coordinator.py::test_installer_metadata_failure_has_zero_target_or_control_side_effects \
  tests/test_agy_gemini_coordinator.py::test_installer_builds_and_lints_every_plist_before_any_mutation -q
```

- RED: `10 failed`
- failure classes: pool corrupt、state corrupt、pool mismatch、non-empty lock、
  unsafe state parent；coordinator 與四 lane 的五個 lint positions。
- observed root cause: shell 只驗檔案外觀，未驗 schema/identity；且 plist
  採逐份 build→mutation，並在 lint 前建立 target directories。
- GREEN: metadata-only Python validator 完整驗 pool/state/lock/parent/identity
  與三個 credential file metadata，不 open/read credential value；installer
  先 build/lint 五份 temp plist，全通過才建立 target dirs 或呼叫 launchctl。
- GREEN command（含 success/static smoke）: `12 passed`

## F3 lock pathname replacement

RED command：

```text
<local-only-python> -m pytest \
  tests/test_agy_gemini_outbox.py::test_allocator_lock_path_replacement_cannot_create_parallel_critical_section -q
```

- RED: `1 failed`；A 持原 inode flock 時，B 在 replacement inode 成功配置
  `(2, account-2)`。
- observed root cause: lock fd/path identity 未持久綁定，pathname replacement
  可讓第二 inode 形成平行 critical section。
- GREEN: state directory fd 提供共同 serialization；durable state 綁定 lock
  device/inode；acquire 與 durable commit 後均核對 lock fd/path identity。
- GREEN regression command: `11 passed`（含 race、4-process/300、crash consumption
  與 state fail-closed）。

所有 debug instrumentation 均已移除；`[DBG-` scan 無命中。
