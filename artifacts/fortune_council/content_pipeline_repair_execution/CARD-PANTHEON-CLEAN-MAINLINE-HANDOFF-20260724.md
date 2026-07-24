---
card_id: CARD-PANTHEON-CLEAN-MAINLINE-HANDOFF-20260724
status: HANDOFF_READY
type: clean-mainline-handoff
project: Pantheon
created_at: 2026-07-24 16:59 CST
owner: mainline
---

# Pantheon Clean Mainline Handoff

## Purpose

This card exists to start a fresh Codex visible thread without inheriting stale sidebar Git badge metadata from the previous long-running thread.

## Current Git baseline

- Repository: `Pantheon`
- Remote: `origin`
- Production branch: `main`
- Current `origin/main`: `3d39751f599aef0512dbb31bff75f587aa08dd8e`
- PR #3: `Integrate GSC, SEO gate, multilingual rewrite work` — merged.
- PR #4: `Gemini V4 broker shadow integration` — merged.
- Local main worktree: aligned to `origin/main`.
- Old local Pantheon branch names were removed after archiving their tips.
- Archive refs: `refs/archive/pantheon-cleanup-20260724/*`

## Important boundary

Gemini V4 is integrated into `main` as an explicit / shadow-capable technical lane.

Do not promote Gemini V4 as the default reviewer or publisher path unless a later rollout card explicitly authorizes default promotion.

## Known verification status

- V4 focused tests: `85 passed`.
- Full pytest on V4 integration branch before merge: `378 passed, 2 failed`.
- The 2 failures were reproduced on `origin/main` and are existing `ziwei provider` expectation failures:
  - `tests/test_api.py::test_predict_route_returns_charts_and_ai`
  - `tests/test_calculators.py::test_ziwei_returns_palace_payload`
- `git diff --check`: PASS.
- Cloudflare Pages check on PR #4: SUCCESS.

## Current operational intent

Continue from a clean Pantheon mainline:

1. Keep new article production running.
2. Keep legacy article rewrite flow running.
3. Keep sitemap / feed / release record updates healthy after every publish.
4. Treat V4 as available but not default-promoted.
5. Do not reopen old V2/V3/V4 repair branches unless explicitly requested.

## Sidebar cleanup note

The previous thread may show an old Codex App Git badge for PR #3 (`codex/pantheon-integrate-gsc-seo-multilingual`). That is thread UI metadata, not a live Git branch.

This new thread should be the fresh Pantheon mainline.
