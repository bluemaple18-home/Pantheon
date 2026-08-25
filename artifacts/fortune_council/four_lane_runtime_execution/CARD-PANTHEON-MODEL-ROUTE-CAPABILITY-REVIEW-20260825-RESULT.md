# CARD-PANTHEON-MODEL-ROUTE-CAPABILITY-REVIEW-20260825 Result

Verdict: REVIEW_GO

Reviewed commit: `67f62f233f957bfbcaf51d65e63d58f66e35c206`

Review scope:
- `config/agy_gemini_model_routes.v1.json`
- `scripts/agy_seo_copy_pipeline.py`
- `scripts/agy_gemini_outbox.py`
- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `tests/test_agy_seo_copy_pipeline.py`
- `tests/test_agy_gemini_outbox.py`

## Findings

未發現 P0/P1 阻塞問題。

## Evidence

CodeGraph:
- Bounded query: `Gemini 3.5 Flash 3.1 Pro capability CLI_NONZERO`
- Relevant hits included `scripts/agy_seo_copy_pipeline.py` `ANTIGRAVITY_MODEL_LABELS`, `validate_antigravity_cli_capabilities`, and `scripts/agy_gemini_outbox.py` CLI terminal classification paths.
- Status after review: 582 files indexed, 6924 nodes, 15327 edges.

Model routes:
- `config/agy_gemini_model_routes.v1.json` fixes formal writer to `gemini-3.5-flash`.
- `config/agy_gemini_model_routes.v1.json` fixes formal reviewer to `gemini-3.1-pro`.
- `scripts/agy_seo_copy_pipeline.py` maps these to CLI labels `Gemini 3.5 Flash (Low)` and `Gemini 3.1 Pro (Low)`.
- `tests/test_agy_seo_copy_pipeline.py` asserts both route order and CLI label usage.

Activation capability gate:
- `scripts/install_agy_gemini_coordinator_launchd.sh` computes route identity from repo config before staging/activation.
- `--activate` and `--activate-only` run `validate_antigravity_cli_capabilities([AGY_CLI_PATH])` before plist activation.
- `validate_antigravity_cli_capabilities` first runs `models`, then smoke-tests writer and reviewer labels with plan/sandbox/print mode.
- Failure diagnostics are closed: category/status/hash only, no raw stderr detail.
- Tests cover both-model success, missing reviewer model, and closed smoke diagnostics.

`CLI_NONZERO` terminal policy:
- `scripts/agy_gemini_outbox.py` keeps `CLI_NONZERO` as a closed failure category.
- `CLI_NONZERO` is not present in `RETRYABLE_EXTERNAL_FAILURE_CATEGORIES`.
- `OutboxGeminiClient.generate_json` retries only API quota/rate-limit or categories in the retry allowlist, so `CLI_NONZERO` raises terminal `ExternalJobFailed`.
- `tests/test_agy_gemini_outbox.py` covers `GeminiCliFailure` with `CLI_NONZERO` in terminal categories and asserts no retry enqueue.

Verification commands:
- `/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py tests/test_agy_gemini_outbox.py`
  - Result: `332 passed in 117.98s`
- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`
  - Result: PASS
- `git diff --check`
  - Result: PASS

Environment note:
- An initial `uv run --frozen pytest ...` attempt was interrupted after the user clarified not to create/download a new environment. It had created `.venv` and reached `135 passed`; this run is excluded from acceptance evidence. The generated `.venv` was removed. The accepted test evidence is only the main-workspace interpreter run above.

## Residual Risk

No live activation, publish, push, tag, promotion, or article run was executed by this review. The review verifies source behavior and deterministic tests; live provider availability remains intentionally outside verdict scope per card instructions.
