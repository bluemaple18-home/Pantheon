# Ziwei Provider Dependency Check 2026-07-14

## Finding

The worktree had the lockfile and bridge source, but no installed `node_modules/iztro`. The bridge therefore failed to import and the application correctly returned its `pantheon_ziwei` fallback, while tests expected the configured `iztro` provider.

## Correction

Installed the existing lockfile without changing versions:

```text
pnpm install --frozen-lockfile
iztro 2.5.8
```

Added the prerequisite to `README.md` and `docs/pantheon_deployment_workflow.md`.

## Verification

- `pnpm run ziwei:chart`: provider `iztro`, status `active`, version `2.5.8`
- `pytest tests/test_api.py tests/test_calculators.py -q`: 21 passed
- `pytest -q`: 80 passed, 2 warnings (existing deprecation warnings)
