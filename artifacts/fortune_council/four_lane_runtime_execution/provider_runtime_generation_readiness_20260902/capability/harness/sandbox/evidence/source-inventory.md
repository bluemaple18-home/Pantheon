# Provider Runtime Generation Source Inventory

- Task: `PANTHEON-PROVIDER-RUNTIME-GENERATION-READINESS-20260902`
- Generation: `provider-readiness-4a3dfeac1943-20260902`
- Actor HEAD: `4a3dfeac1943061edfce5350cb6bb25e35ff64c0`
- Provider fix SHA: `2d03f97a7750e23cb1e67dd850e841fa35e3e194`
- CodeGraph: `CONTEXT_DEGRADED`; bounded source census only.
- Create/run formal boundary: `scripts.agy_gemini_coordinator:coordinator_create_run_receipt_preflight`.
- Select/publish/transaction/tag/push formal boundary: `scripts.agy_content_publisher:formal_capability_preflight`.
- Harness composition: `scripts.pantheon_writer_vnext_runtime_activation_e2e:run_runtime_activation_e2e`.
- Provider mode: deterministic local fake provider; external provider calls remain zero.
- Tag/push mode: sandbox local fake git; real tag/push probes fail closed.
