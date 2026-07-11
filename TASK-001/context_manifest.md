# TASK-001 Context Manifest

## Local Files

- `pyproject.toml`
- `main.py`
- `app/api/routes.py`
- `app/api/schemas.py`
- `app/core/registry.py`
- `app/calculators/base.py`
- `app/calculators/bazi.py`
- `app/calculators/ziwei.py`
- `app/ai/prompts.py`
- `app/ai/agent.py`
- `scripts/ingest_ziwei_samples.py`
- `docs/attribution.md`
- `docs/report_syntax.md`
- `docs/life_chart_engine_intake.md`
- `docs/ziwei_fusion_strategy.md`
- `app/calculators/ziwei_fusion.py`

## External References

- `https://github.com/hhszzzz/taibu`
- `https://github.com/china-testing/bazi`
- `https://github.com/Renhuai123/ziwei-doushu`
- `https://github.com/zhenheco/life-chart-engine`

## License Notes

- `taibu`: README states core/MCP packages are MIT; other repo code is AGPL-3.0-only.
- `china-testing/bazi`: no clear license was found on the GitHub page during this pass.
- `ziwei-doushu`: README states code is MIT and dataset is attribution-required.
- `life-chart-engine`: 2026-07-11 GitHub README/badge shows MIT; older local notes recorded AGPL. Keep it as field contract, external verifier, and golden sample reference until dependency licenses are re-audited.
- Ziwei fusion: Pantheon/`ziwei-doushu` is the primary line; `life-chart-engine` can only validate, supplement, or flag conflicts.
