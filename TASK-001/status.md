# TASK-001 Status

## Current State

MVP backend scaffold is implemented and verified.

## Completed

- FastAPI app and `/api/v1/health`, `/api/v1/predict`.
- Pydantic request/response schema.
- Calculator base class and registry.
- Bazi and Ziwei MVP calculators.
- Reserved plugins for MBTI, Human Design, and Tarot.
- Local AI prompt composer and stub summary.
- SQLite ingest script for downloaded Ziwei JSON/JSONL samples.
- README and attribution notes.
- Consumer-facing frontend with chart mode and red-print fortune-paper mode.
- Unified output syntax v0.2 with multiple narrative strategies.
- `life-chart-engine` intake integrated as external verifier / field contract reference.
- Provider-aware Ziwei fusion scaffold, with Pantheon primary and `life-chart-engine` reserved as secondary validator.
- Birth precision fields added: location, latitude, longitude, UTC offset, birth-time confidence, and target year.
- Bazi scaffold now includes 10-year luck cycle and annual luck fields for the fortune-paper view.
- Luck-cycle wording now separates long-term decade background from annual triggers, including natal-year interaction summary.
- Frontend static JavaScript is split into ES modules: API payload/fetching, dashboard rendering, fortune-paper rendering, and shared formatting utilities.
- Fortune-paper information architecture now follows a user-readable path: chart evidence, combo reasoning, decade luck, annual luck, and suitable/unsuitable advice.

## Blockers

- Full Bazi migration is blocked until license/usage boundary is decided.
- Full Ziwei migration and RAG are blocked until dataset download and storage target are approved.
- Western astrology and Human Design production calculators are blocked until coordinate/timezone schema and ephemeris licensing are decided.

## Next Step

Pick one deep integration path:

1. License-safe Bazi implementation from first principles with golden samples.
2. Ziwei dataset download/import and retrieval layer.
3. Replace luck-cycle scaffold with calibrated qiyun / solar-term implementation.
4. Add month-level timing only after yearly/decanal accuracy rules are calibrated.
5. Life-chart-engine external verifier adapter and golden sample snapshots.
6. Real LLM provider integration with API keys and safety prompt policy.
