# Swap telemetry capacity blocker RCA evidence

## Verdict

- Verdict: `SANDBOX_FALSE_NEGATIVE`
- Formal thread ID: `01a013f2-bdf2-7003-b83a-faa3754b464d`
- Activation token: `PANTHEON-SWAP-TELEMETRY-CAPACITY-RCA-20260818-G1`
- Authoritative source SHA: `cf08a71b0976bf22fdff16fa49d20e3c0a9c7e44`
- Blocked evidence commit: `92e79845c748c467cf22368dcfad556381dd7c26`
- CodeGraph: `CONTEXT_DEGRADED`; this worktree has no initialized `.codegraph`, so no source decision was made from an index.

## Commands

The same formal command was run once in the sandbox boundary and once with the approved read-only host boundary. The only intended variable was telemetry access.

```text
python3 -m scripts.pantheon_content_capacity_guard exercise \
  --exercise-root <fresh-evidence-root>/capacity-exercise \
  --receipt <fresh-evidence-root>/capacity-receipt.json \
  --cycle-bytes 1048576
```

Host-only read probe:

```text
sysctl -n vm.swapusage
total = 9216.00M  used = 7952.69M  free = 1263.31M  (encrypted)
```

## Comparison

| Boundary | Cycle 1 | Cycle 2 | Swap telemetry | Exit | Production mutation |
|---|---:|---:|---|---:|---|
| Sandbox | `NO-GO` | `NO-GO` | unavailable / `null` | `1` | `false` |
| Read-only host | `PASS` | `PASS` | available / `8338999869` bytes | `0` | `false` |

Both runs used regression `REG-PANTHEON-CAPACITY-WRITE-CYCLES-001`, two 1 MiB cycles, RSS and host-free measurements, cleanup, and stop-loss checks. Both exercise roots were absent after cleanup. No source, gate, policy, canary, runtime, LaunchAgent, transaction, tag, push, activation, or publish mutation occurred.

## Current receipts

- Sandbox receipt: `sandbox-capacity-receipt.json`
  - SHA-256: `88ef8bca138073c26318472e763227f9b4548ee764c4fdd07e6fc4a7114e7fb8`
- Host receipt: `host-capacity-receipt.json`
  - SHA-256: `ac4efbbfe4f27b4acd5d0a8df2bcf27d5ecda4781eb2db01c5c3138293a5169d`

## Root cause and boundary

The blocker is the sandbox permission boundary preventing the formal guard from obtaining `vm.swapusage`; it is not a real host capacity failure. Host telemetry was readable and the unchanged formal exercise passed both cycles. This is a diagnostic conclusion only; the canary remains stopped and must not be resumed by this task.

Production mutation: `0`.
