---
id: CARD-PANTHEON-LEGACY-BRIEF-LANE-RECONCILE-20260830
status: reviewed_local_candidate
type: bounded_implementation_card
priority: P1_HIGH
authority: Owner批准 bounded follow-up；local code/test only；independent REVIEW_GO/no P0-P2；commit pending；production/remote/push false until Mainline
implementation_authorized: false
execution_authorized: false
production_authorized: false
remote_authorized: false
provider_authorized: false
publish_authorized: false
promotion_authorized: false
service_authorized: false
push_authorized: false
base: ced72054eb6b93646fd876bcdb1fcf7e44528121
---

# Pantheon Legacy Brief Lane Reconcile

## Root question

`reconcile-translation-replacement-identity --plan-only` 在 live target 上 fail closed，原因是 legacy `brief.json` 缺 `lane`。如何只在 reconciliation-specific validation 支援此 legacy shape，不改 general `_identity_envelope_from_brief` 語意、不修改 production brief、不放寬 registry/CLI lane guard？

## Scope

Allowed:

- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`
- 本卡與 RESULT

Forbidden:

- production plan/execute/apply/publish/promotion/service/tag/push
- promotion/publisher/multilingual producer
- general `_identity_envelope_from_brief` semantics
- 修改 production runtime artifact

## Required behavior

- Reconciliation fixture 的 `brief.json` 可缺 `lane`，且 plan-only 必須 `plan_only`、zero mutation。
- `brief.mode` 必須是 `translate_existing`。
- brief 必須只有一個 article dict，且 `source_article_id` exact match CLI `--article-id`。
- `locale` 必須為 non-empty string，`translation_id` 必須等於 `<article_id>:<locale>`。
- nested `source.article_id`、`source_path`/`source.canonical_path`、`source_sha256` 必須一致。
- brief 缺 lane 時，使用 explicit verified CLI/registry lane 建 expected envelope。
- brief 有 lane 時，必須等於 CLI/registry lane，且維持 canonical validation。
- registry/CLI lane mismatch 仍 reject。

## Negative matrix

- brief wrong lane
- brief wrong mode
- brief wrong / multiple / missing article IDs
- translation_id / locale / nested source / source_sha256 / source_path mismatch
- registry/CLI lane mismatch

## Verification

- focused reconciliation selectors
- related producer/promotion selectors
- `py_compile`
- `git diff --check`

## Result contract

RESULT 必須記錄：

- ced production plan stale/blocked cause：legacy brief 缺 lane
- local fix evidence
- production mutation：0
- independent REVIEW_GO/no P0-P2；commit pending
