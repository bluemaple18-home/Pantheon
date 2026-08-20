# Cycle 17 public preflight NO-GO parameter RCA evidence

## Facts

- Authoritative card is readable from commit `b2995858c91c1d8de05d613dd7f5e2040a69f101`.
- NO-GO evidence `ef2cdf9e47` records one public preflight invocation and its exact argv contains no `TMPDIR`.
- Installer creates `TEMP_PLIST` at `${TMPDIR:-/tmp}/pantheon-content-capacity-guard.XXXXXX`.
- On this host, `/tmp` is a symlink to `private/tmp`; both `/tmp` and `/private/tmp` resolve to `/private/tmp`.
- `scripts/pantheon_content_runtime_manifest.py::plist_receipt` rejects when `canonical != path` or owner UID differs. Because the generated argument path begins `/tmp/` while its resolved path begins `/private/tmp/`, the canonical-path predicate alone explains `plist canonical realpath or owner mismatch`.
- The error text combines canonical-path and owner checks; no evidence shows owner drift, and setting canonical `TMPDIR` does not change ownership.
- `scripts/pantheon_content_capacity_guard.py::validate_preactivation_transition` explicitly accepts an otherwise exact receipt whose only reason is `rss_telemetry_unknown` and whose error starts `loaded_service_pid_missing:`.
- The transition subsequently requires the complete old-live aggregate to be loaded with no PID. Therefore Publisher no-PID is an expected preactivation transition input, not a request to activate/reload before preflight.
- Tests preserve the same boundary: promoted manifest/barrier/staged services plus old-live activation-only loaded/no-PID is accepted without launchctl mutation; unsafe identity, barrier, stage, PID, or topology drift remains rejected.
- Existing authoritative cards record that `TMPDIR=/private/tmp` produced formal `preactivation_transition=accepted/PASS`.

## Interpretation

The public wrapper first receives the capacity module's no-PID telemetry gap, then uses `preactivation-transition` to decide whether that gap is safe for the exact preactivation topology. The missing canonical `TMPDIR` invalidated only the temporary candidate plist path and prevented this recovery seam from accepting. Activation/reload before this check would reverse the intended gate order and is neither necessary nor authorized.

## Gate order

The formal preflight belongs after the promoted/current manifest, matching barrier, stage metadata, staged non-capacity plists, Publisher exact-run receipt, and coherent old-live activation-only/no-PID aggregate exist; it belongs before capacity plist installation/restaging and before activation. Any tuple or topology mismatch remains fail-closed.

## Counts

- public preflight before this RCA: `1`
- public preflight executed by this RCA: `0`
- direct module: `0`
- capacity exercise: `0`
- launchctl mutation: `0`
- Gate A/push/promotion/restaging/activation/canary/lane/Publisher/tag/publish: `0`
- production mutation: `0`
