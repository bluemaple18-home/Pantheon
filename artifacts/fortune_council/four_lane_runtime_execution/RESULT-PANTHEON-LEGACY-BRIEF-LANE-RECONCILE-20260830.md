---
id: RESULT-PANTHEON-LEGACY-BRIEF-LANE-RECONCILE-20260830
status: reviewed_local_candidate
card: CARD-PANTHEON-LEGACY-BRIEF-LANE-RECONCILE-20260830
production_used: false
remote_used: false
provider_used: false
publish_used: false
promotion_used: false
service_used: false
push_used: false
---

# Pantheon Legacy Brief Lane Reconcile Result

## Stale production plan blocker

The prior ced production `--plan-only` precheck is stale/blocked because live target `brief.json` has:

- `mode: translate_existing`
- no `lane` field
- exact single source article identity `ASTRO-BASE-03`

The merged command rejected before plan creation with:

```text
translate run lane is required for durable identity
```

No production mutation occurred during that precheck.

## Local fix

Only reconciliation-specific validation changed:

- general `_identity_envelope_from_brief` semantics unchanged;
- `brief.mode` must be `translate_existing`;
- brief must contain exactly one article dict whose `source_article_id` exact-matches CLI `--article-id`;
- `locale`, `translation_id`, nested `source.article_id`, `source_path`/`source.canonical_path`, and `source_sha256` must be internally consistent;
- missing brief lane uses already-verified CLI/registry lane to build expected identity;
- present brief lane must equal CLI/registry lane and still use canonical validation.

No production plan/execute was run after the local fix.

## RED

- `test_reconcile_translation_replacement_identity_plan_only_accepts_production_shape_without_mutation` failed after fixture brief lane was removed, matching the live production shape.

## GREEN

- focused reconciliation selectors: `37 passed`
- related producer/promotion selectors: `3 passed`
- `py_compile`: PASS
- `git diff --check`: PASS
- independent review: `REVIEW_GO / no P0-P2`
- commit: pending Mainline

## Production boundary

- production mutation: 0
- remote/provider/publish/promotion/service/tag/push: not used
- independent review: `REVIEW_GO / no P0-P2`
