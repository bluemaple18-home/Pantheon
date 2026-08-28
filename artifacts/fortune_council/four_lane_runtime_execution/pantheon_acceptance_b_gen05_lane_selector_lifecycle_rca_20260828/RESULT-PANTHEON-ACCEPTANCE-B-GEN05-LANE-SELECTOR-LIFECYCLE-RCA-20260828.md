---
schema_version: 1
title: Pantheon Acceptance B gen05 lane selector lifecycle RCA
date: 2026-08-28
status: COMPLETE
verdict: RCA_CLOSED_READY_FOR_ONE_BOUNDED_REPAIR
target_actor: 8a50395f67d22343fec4b0a8a5f41c8f40ac360e
target_run: auto-i18n-ja-1414b75a404721e95e74
provider_calls: 0
production_mutation: false
---

# Root Question

為什麼 8a actor 的 production exact-run 已不再被 dangling registry guard 擋住，
但 target run `auto-i18n-ja-1414b75a404721e95e74` 仍沒有推進到
Writer→Reviewer→publish？

# Verdict

根因是 coordinator 的兩個 runtime lifecycle contract 對同一個 legacy translation
active registry state 的接受邊界不一致：

- `_active_run_integrity_block` 已在 8a 接受 validated `identity_envelope`
  作為 legacy translation lane authority。
- `_lane_for_state` 仍把任何含 `lane` 或 `mode` 的 state 當作新 schema-routed
  state，要求 `routing_schema_version == 1` 且 `mode` 存在。
- production target state 由 translation enqueue owner 寫成 partial legacy shape：
  有 `lane=i18n-new` 與 validated `identity_envelope`，但沒有 `mode` /
  `routing_schema_version`。
- 結果：integrity guard PASS，lane selector 回 `None`，`_select_lane_states`
  跳過 target run，cycle 回 `status=ok active=1 runner=idle`，沒有 provider job、
  沒有 Writer/Reviewer/publish。

# Evidence

## Production observable

Production target state：

```json
{
  "run_id": "auto-i18n-ja-1414b75a404721e95e74",
  "status": "active",
  "lane": "i18n-new",
  "mode": null,
  "routing_schema_version": null,
  "identity_envelope": {
    "article_ids": ["V2-TAROT-DEATH-MONEY"],
    "digest": "5527bccc79f7089b2e8e24d256df5ff81205b574a233e7537e314af9a19da0ef",
    "lane": "i18n-new",
    "mode": "translate_existing",
    "schema_version": 1
  }
}
```

8a promoted exact-run output：

```json
{
  "status": "ok",
  "active": 1,
  "complete": 0,
  "failed": 0,
  "runner": {"status": "idle"},
  "lanes": {
    "i18n-new": {"active": 0, "processing": 0, "queued": 0},
    "i18n-rewrite": {"active": 0, "processing": 0, "queued": 0},
    "new": {"active": 0, "processing": 0, "queued": 0},
    "rewrite": {"active": 0, "processing": 0, "queued": 0}
  }
}
```

Exact-run evidence:
`artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_production_release_8a_20260828/exact-run.stdout.json`

## Source seam

Current 8a source:

- `scripts/agy_gemini_coordinator.py:2250-2305` validates target state as active
  identity-consistent when brief is `translate_existing`, brief has no `lane`, and
  state `lane` matches `identity_envelope.lane`.
- `scripts/agy_gemini_coordinator.py:2359-2364` enters schema-routed branch when
  `routing_schema_version is not None or "mode" in state or "lane" in state`;
  if `routing_schema_version != 1`, it raises.
- `scripts/agy_gemini_coordinator.py:2377-2385` catches selector `ValueError`
  and returns `None`.
- `scripts/agy_gemini_coordinator.py:2388-2409` skips lane `None`; therefore
  the target run is still active but not selected.

Translation state authoritative owner:

- `scripts/agy_multilingual_pipeline.py:155-164` defines
  `translation_identity_envelope(article_id, lane)` with mode `translate_existing`.
- `scripts/agy_multilingual_pipeline.py:888-955` writes new translation state with
  `lane` and `identity_envelope`, but not `mode` or `routing_schema_version`.

Promotion boundary:

- `scripts/pantheon_content_runtime_promotion.py:766-884` validates preserved run
  identity and classification from queue state and run brief.
- `scripts/pantheon_content_runtime_promotion.py:1304-1307` requires queue identity
  and digest to remain unchanged during promotion.
- Therefore promotion is a preservation/verification boundary, not the owner of
  active state schema migration.

# Red-Capable Harness

Command:

```bash
.venv/bin/python artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_lane_selector_lifecycle_rca_20260828/lane_selector_red_harness.py
```

Expected RCA RED exit: `1`.

Result artifact:
`artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_lane_selector_lifecycle_rca_20260828/lane-selector-red-harness-result.json`

Harness result:

- `status`: `RED`
- `provider_calls`: `0`
- `symptom_reproduced`: `true`
- production-shaped case:
  - integrity block: `null`
  - lane selector result: `null`
  - summary: `status=ok active=1 complete=0 runner.status=idle`
  - calls: `tick=0 process=0`
- schema-complete counterfactual:
  - `counterfactual_schema_complete_advances=true`
  - calls: `tick=1 process=0`
- fail-closed negative:
  - `fail_closed_negative_blocks=true`
  - lane drift returns `status=blocked reason=active run registry is dangling`

This is a valid RED signal because it reproduces the production symptom, not an
import/env/provider failure.

# Commit / Mechanism Timeline

- `2b5da2f068` introduced independent multilingual queue/publish support. Early
  translation states were active runs without the later lane identity envelope.
- `fa055e5402` and `36845c9052` repaired exact fresh JA run identity derivation,
  still before the lane authority split observed here.
- `b711184af2` introduced coordinator lane routing ownership:
  `_lane_for_state` treats states with `lane`/`mode` as schema-routed and requires
  `routing_schema_version == 1`; otherwise it can derive/migrate from brief only
  when neither `lane` nor `mode` is present.
- `34d82a3774` introduced translation `identity_envelope` and allowed enqueue to
  write `lane` + `identity_envelope` when lane was supplied.
- `204a8bd8b8` made translation seed lane identity required. From this mechanism
  onward, newly enqueued translations can have the target partial shape:
  `lane` + `identity_envelope`, but no `mode` / `routing_schema_version`.
- `6477ab815e` repaired a legacy migration boundary, but only for states where
  selector can derive from brief; the partial state with `lane` already present
  enters the strict schema branch and bypasses this migration.
- `878db727f4` preserved legacy registry compatibility for identity envelope
  backfill/classification, not lane selector selection.
- `8a50395f67` accepted validated legacy translation lane authority in
  `_active_run_integrity_block`, but its exact-cycle positive fixture still used
  schema-complete state (`routing_schema_version=1`, `mode=translate_existing`).
  The 8a test that removed `mode` only checked integrity guard, not lane selector.

First failing mechanism is therefore the combination of:

1. `b711184af2` selector strict schema branch for states containing `lane`; and
2. `34d82a3774` / enforced by `204a8bd8b8` translation enqueue writing a partial
   lane-authorized legacy shape without selector schema fields.

The production target was registered at `2026-08-26T23:32:41+08:00`, after
`204a8bd8b8`, matching this mechanism.

# Hypotheses

## A. Selector should be compatible with validated legacy partial state

Supported.

If a legacy translation active state has:

- valid `identity_envelope`;
- `identity_envelope.mode == "translate_existing"`;
- state `lane` matches `identity_envelope.lane`;
- brief identity article IDs match the envelope;
- no contradictory `mode` / `routing_schema_version`;

then active integrity and lane selection should share the same authority. The
harness proves the current code accepts integrity but drops selection; the
schema-complete counterfactual proves the run would advance if selector receives
equivalent routing fields; lane drift negative still blocks.

## B. Promotion/migration should fill state; current selector fail-closed is correct

Falsified for this production RCA boundary.

Promotion intentionally preserves queue identity/digest and rejects queue changes
during promotion; it is not the active state schema owner. The state writer is
`enqueue_article_translations`, and it currently writes partial lane identity.
Also, selector does not fail closed in this case: it silently skips the selected
exact run and returns `status=ok active=1 runner=idle`, which is an ambiguous
idle, not an explicit BLOCKED state.

# Durable Invariant

For lane-mode exact-run:

> Any active run that passes active registry integrity for the selected exact
> run ID must either be selected and advanced in its lane, or the cycle must
> return an explicit BLOCKED/failed state. It must never be silently skipped
> while reporting `status=ok active=1 runner=idle`.

This invariant was broken by inconsistent acceptance between the identity guard
and selector.

# Authoritative Owner

- Translation queue state shape owner:
  `scripts/agy_multilingual_pipeline.py:888-955`
- Runtime selection owner:
  `scripts/agy_gemini_coordinator.py:2354-2409`
- Promotion owner:
  `scripts/pantheon_content_runtime_promotion.py`; limited to validation and
  preservation of queue identity/digest during actor promotion.

# Cross-Version Lifecycle / Replacement Boundary

The target state is a cross-version durable active run. It can survive actor
replacement/promotion because promotion preserves queue state and run IDs. That
means new actors must either:

- continue accepting and selecting durable legacy shapes that their own
  integrity guard accepts; or
- fail closed explicitly before exact-run claims `status=ok`.

Replacement/promotion is not allowed to opportunistically rewrite active state
without a transaction dedicated to that lifecycle change.

# Minimum Candidate Repair Seam

Candidate seam:
`scripts/agy_gemini_coordinator.py:_lane_for_state`.

Minimal bounded behavior:

- Before the strict schema-routed branch rejects missing
  `routing_schema_version`, detect the exact legacy translation partial shape:
  state has `lane`, no `mode`, no `routing_schema_version`, valid
  `identity_envelope`, envelope mode `translate_existing`, and state lane equals
  envelope lane.
- Return the validated envelope lane, or perform the same narrow migration to
  `mode=translate_existing` and `routing_schema_version=1` only under CAS /
  current-state verification.

Required fail-closed negatives:

- invalid envelope digest → BLOCKED
- state lane differs from envelope lane → BLOCKED
- envelope mode is not `translate_existing` → BLOCKED
- brief lane contradicts envelope/state lane → BLOCKED
- unknown non-null `routing_schema_version` → BLOCKED
- state has `mode` but missing/invalid `routing_schema_version` → BLOCKED

# why_not_less

只改 exact-run retry、再跑一次 cycle、或手補 state 都不能修 invariant；它們只會繞過
selector 與 identity guard 的 contract split，而且 production state mutation 被本輪禁止。

# why_not_more

不需要新 registry、authority ledger、promotion subsystem、gen06、provider rerun 或 publication
workflow 改造。缺口集中在一個 selector seam 與其 tests；擴大會違反 minimum sufficient。

# do_not_absorb

- 不吸收第二套 runtime FSM。
- 不讓 promotion 自動改寫 active queue state。
- 不新增 manual production state editor。
- 不建立新 canary/publish path。
- 不把 translation planning/provider 流程納入本 Repair。

# Four Stop-Line Evidence Items

1. Last success:
   - schema-complete active translation state在 8a harness 中可被選中並 tick；
   - legacy no-lane/no-mode state仍有從 brief derive/migrate 的 selector path。
2. First failing commit/mechanism:
   - `b711184af2` strict selector branch + `34d82a3774`/`204a8bd8b8`
     partial lane identity state writer。
3. Broken durable invariant:
   - integrity-accepted exact active run must selected-or-blocked；實際被 silent skip。
4. RED-capable test:
   - `lane_selector_red_harness.py` 已執行，result `RED`，provider=0。

結論：四項證據已閉合。可以進入唯一 bounded Repair；但本 RCA worker 不得實作，
需由主線另行開卡，限定於 lane selector legacy partial state compatibility 與 regression
tests。
