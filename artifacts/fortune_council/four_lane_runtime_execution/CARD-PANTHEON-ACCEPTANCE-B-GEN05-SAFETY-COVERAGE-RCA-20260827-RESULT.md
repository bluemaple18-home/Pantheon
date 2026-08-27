# CARD-PANTHEON-ACCEPTANCE-B-GEN05-SAFETY-COVERAGE-RCA-20260827 結果

## 狀態

status: NO-GO

verdict: GEN05_SAFETY_COVERAGE_RCA_COMPLETE

本任務是唯讀 RCA，RCA evidence 已閉合；Repair 仍為 NO-GO / 未授權。未執行 Repair、generation rerun、provider/article/Reviewer/publisher 呼叫、production mutation、commit、merge、push、tag、deploy 或 publish。唯一 repo 輸出為本檔。

## Root Question

Production exact gen05 為何在 Writer plan transport success 後，於 deterministic hydration 階段穩定停在 `locale plan safety coverage differs for article-01`？

## 結論

唯一主根因：gen05 provider-facing locale-plan contract 仍要求 Writer 在 `coverage_mapping` 自行輸出 `safety_boundary` boolean，但 JA continuation 的 deterministic owner 已經是本地 `_source_fact_package()` / source-ref-map / hydration gate。schema 只能限制 `source_ref` enum 與 boolean 型別，無法把每個 `source_ref` 的 boolean 鎖成 deterministic expected value；prompt 又同時提供 `protected_constraints` / `boundary_candidate_dispositions` 與 fact text，讓 Writer 把 6 個風險語意較強的 fact 誤標成 `true`。本地 hydration 正確將 external flag 視為 assertion，不給 provider authority，並因 6 個 `true != false` fail closed。

這不是 gen04 source-ref coverage blocker 的延續；gen04 blocker 是「已有 persisted external-plan 但缺 source-ref-map」，gen05 已有有效 source-ref-map，source_ref coverage 已解除。gen05 是下一層 safety flag echo / authority mismatch。

## Evidence Snapshot

- CodeGraph：`codegraph_context` 在 `<repo-root>` 回報未初始化，改用限域 `rg` 與精準檔案讀取。
- Workspace HEAD：`e3a2bbd188a0d25f15a02cde1b2b6820df5dd583`。
- Production run root：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue/translation-runs/auto-i18n-ja-1414b75a404721e95e74`。
- Runtime manifest：actor_head `e3a2bbd188a0d25f15a02cde1b2b6820df5dd583`，generation `g52-e3a2bbd1-gen04-semantic-budget-20260827`，python executable `/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12`。
- Actor/worktree source identity：production actor git HEAD、worktree HEAD、runtime manifest actor_head 三者相等；`scripts/agy_multilingual_pipeline.py` worktree SHA、actor SHA、imported production actor SHA 三者皆為 `a07b6fe08c23e773c0cea8ea2236d30fb5661213816097ee802ed768a5b97d8a`。
- gen05 `plan-operation.json`：status `success`，role `writer`，model `gemini-3.5-flash-lite`，transport `_outbox_transport`，prompt SHA `906a41e84195373b7816ba8b6968a932e1133b2e557772c340a5a42194ff0cba`，schema SHA `b2d821ad016108bb11b91dba5eefacbc1fd12bd3450603a87f2910eb33c83`，receipt SHA `ed10f8a4c09b688d409bcb2bb55cf537b182b967799a21a16bcbd7ab3a27aa9d`。
- Recomputed exact prompt/schema SHA：完全等於 gen05 `plan-operation.json`；evidence JSON 內 `prompt_match: true`、`schema_match: true`。
- gen05 `planning-result.json`：`PLANNING_CONTRACT_FAILURE`，terminal stage `PLANNING`，terminal reason `locale plan safety coverage differs for article-01`。
- provider=0 RED harness：`/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12 /private/tmp/pantheon_gen05_safety_coverage_rca_harness.py`，exit code `1`，error type `LocalePlanValidationError`，message `deterministic locale plan failure: locale plan safety coverage differs for article-01`，provider_calls `{}`。
- Harness pass/fail contract：target exact safety error exit `1`；no error exit `0`；other exception exit `2`。`red_capable` 只在 exit `1` + exact safety error + provider0 時為 true。
- Harness evidence：`/private/tmp/pantheon_gen05_safety_coverage_evidence.json`，SHA `d4c7ae44ae86a64b2f4fa1e61c1cacad453ce2efc613fa86577344a0f5e24a62`。
- Fixture path：`/private/tmp/pantheon_gen05_safety_coverage_fixture`。
- Production protected root byte digest before：file_count `44`，total_bytes `102003`，digest `fad9f91f2babb4a39f45cea1dd9ee11953c31420c0a7e10f5157ba4868728d0a`。
- Production protected root byte digest after：file_count `44`，total_bytes `102003`，digest `fad9f91f2babb4a39f45cea1dd9ee11953c31420c0a7e10f5157ba4868728d0a`。
- Production article/reviewer/publish generated artifacts absent：`generations/05/locale-plan.json`、`article-operation.json`、`external-candidate.json`、`candidate.json`、`reviewer-operation.json`、`external-review.json`、`review.json`、`approval.json`、`apply.json`、`publish.json`、`run-evidence.json` 均不存在。

## Exact Coverage Evidence

Source package SHA：`9f98a3690f5b3496d1ed82906779e507cad63d5363795fe23420b67600453ad7`

Coverage rows digest：`4b0fa7519ca7c9f9ac3a964253595c1baaf5b30c0397b271bf91f4d5f5f1b062`

Mismatch digest：`b1ffb5449acbf232f08c43ecf29951e9375eea7e3ea24e689338390cb3ed3a16`

| source_ref | source_fact_id | expected safety_boundary | external actual |
|---|---|---:|---:|
| source_ref_01 | fact-02c295725006 | false | false |
| source_ref_02 | fact-0beac109fa27 | false | false |
| source_ref_03 | fact-23f5088ba3c2 | false | true |
| source_ref_04 | fact-38aed6dba39f | false | false |
| source_ref_05 | fact-3b2d25fec578 | false | false |
| source_ref_06 | fact-3f23c89631b6 | false | false |
| source_ref_07 | fact-4415396b13a0 | false | false |
| source_ref_08 | fact-4464fd5767ce | false | true |
| source_ref_09 | fact-4b44fa760233 | false | false |
| source_ref_10 | fact-5419ff724809 | false | false |
| source_ref_11 | fact-6fc8c0a85cc1 | false | false |
| source_ref_12 | fact-7a8aaaf66773 | false | false |
| source_ref_13 | fact-95ce4850b1be | false | false |
| source_ref_14 | fact-ad6419346192 | false | true |
| source_ref_15 | fact-baddaaa7e604 | false | true |
| source_ref_16 | fact-cefbe5b21d98 | false | true |
| source_ref_17 | fact-d1d58c087583 | false | false |
| source_ref_18 | fact-def80b9806e9 | false | false |
| source_ref_19 | fact-e1d4de7d0af2 | false | false |
| source_ref_20 | fact-ebe435b7bc03 | false | false |
| source_ref_21 | fact-ed7ec3e401ba | false | false |
| source_ref_22 | fact-f729514cc45f | false | true |

The 6 mismatches are exactly `source_ref_03`、`source_ref_08`、`source_ref_14`、`source_ref_15`、`source_ref_16`、`source_ref_22`。

## Fact / Interpretation

Facts:

- `_source_fact_package()` sets JA fact `safety_boundary` from unresolved protected boundary candidates, not from generic risk-looking wording. In this exact source package all 22 fact rows are `false`.
- gen05 source-ref-map is valid and maps `source_ref_01..22` to the current deterministic fact order.
- gen05 external-plan covers all 22 refs once, so source_ref identity coverage is not the failing condition.
- gen05 external-plan sets 6 refs to `safety_boundary: true`.
- `_canonicalize_external_coverage_mappings()` checks each external `safety_boundary` against the deterministic fact package before local hydration writes `locale-plan.json`.
- `_run_locale_generation()` catches that hydration failure, writes planning-result, and stops before article generation.

Interpretation:

- External `safety_boundary` is an assertion that must match deterministic owner; it is not proposal and not authority.
- Deterministic owner is the local source fact package plus persisted request-local source-ref-map.
- Current contract can only fail closed because the external field is currently required output; accepting or silently correcting an already-materialized mismatched assertion would blur whether the provider preserved an existing safety boundary, invented a boundary, or missed the local owner contract.
- The proposed Repair does not accept or secretly mutate the current assertion. It first removes the provider output contract for `coverage_mapping.safety_boundary`, then has local hydration inject deterministic safety from the owner.

## Provider Schema / Prompt Answer

The provider schema requires every coverage item to include:

- `source_ref`: enum `source_ref_01..source_ref_22`
- `planned_h2_slot`: enum `h2-1..h2-4`
- `coverage_note`: string
- `safety_boundary`: boolean

It does not require `source_fact_id`, `fact_id`, `source_sha256`, `source_span_id`, `source_digest`, `source_version_digest`, or other local durable identities.

The exact prompt given to the model includes:

- `source fact package` with `source_ref`, fact `text`, and deterministic `safety_boundary` for each fact; all 22 are `false`.
- `protected_constraints` and `boundary_candidate_dispositions` as JA boundary coverage authority.
- `legacy mapping authority` and `rebuild topology constraints`.
- latest findings: `COVERAGE_MISSING` and `NON_NATIVE_SEARCH_INTENT`.
- `rebuild authority`: `{"article-01": true}`.

The prompt says `coverage_mapping` must preserve facts marked as `safety_boundary`, but the schema still asks the model to emit the boolean. That is the contract gap: the model is asked to echo a deterministic local value that the local hydrator already owns.

## Hypotheses

H1 confirmed: provider-invented safety flags caused the failure. Prediction under the current contract: if all external `safety_boundary` values equal the deterministic package, the same source_ref coverage should pass the safety check; if any one of the 6 actual `true` flags remains, hydration should fail with the same reason. Evidence: exact harness fails on the 6 `true != false` rows, with source_ref coverage complete.

H2 falsified: gen05 failed because source_ref coverage or source-ref-map was missing/stale. Evidence: gen05 contains `source-ref-map.json`, generation `5`, refs `source_ref_01..22`, current fact IDs match `_source_fact_package()`, and the failure reason is not `source ref map missing` or `source ref coverage differs`.

H3 falsified: failure progressed into article/reviewer/publisher stages. Evidence: gen05 has no `locale-plan.json`, no article operation/candidate, no reviewer operation/review, no approval/apply/publish/run-evidence; provider_calls in exact RED harness are `{}`.

## Gen04 → Gen05 Causality

gen04 terminal reason was `source ref map missing for persisted external locale plan`; `generation-lifecycle.json` marks generation 04 as `abandoned`, and `authority-transition-04.json` advances `next_generation` from 4 to 5 with abandoned `[4]`.

gen05 is not reusing or rejudging gen04 output. Its state is active with `semantic_budget: 1`, `abandoned_generations: [4]`, `next_generation: 5`; its own source-ref-map exists and validates against the current package. The previous blocker only explains why authority moved to gen05. It does not explain the 6 safety mismatches.

## History Boundary

Production exact last successful version / behavior:

- `attempts/03/locale-plan.json` successfully hydrated at `2026-08-26T23:35:03+08:00`.
- At that point the formally promoted actor was `204a8bd8b86b37f411048983730ce1efb9fa2734`; v0406 promotion receipt was created at `2026-08-26T14:56:45Z` and committed as `v0406-main-204a8bd8-20260826`.
- Successful locale-plan digest: `c7c0eb857d3b87e3aa254aa1af07552205859a5f61e889ee42c4f56501771810`。
- Successful behavior: a hydrated locale plan existed with deterministic `source_fact_id` coverage and `safety_boundary` accepted by the then-current production actor. This is the last known promoted production behavior before the gen04/05 continuation failures.

Latent defect birth:

- `f0b70b4bba feat: add native locale planning continuation` first introduced the contract pattern where provider output includes `coverage_mapping.safety_boundary` and local validation equality-checks it against deterministic facts. That made provider safety echo a latent failure mode.

Regression activation / authority migration:

- `9f68df0e9d Add JA protected source constraint traceability` moved JA fact safety semantics toward protected source disposition / `UNRESOLVED` ownership. In the current exact source package, all 22 facts are deterministic `false`; this is the authority migration that makes over-inferred provider `true` values conflict with local owner state.

Identity repair:

- `5aea3f98f0 Repair JA cross-version plan authority` solved the prior coverage blocker by introducing request-local `source_ref` and local hydration back to current fact IDs. It did not remove provider `safety_boundary` echo, so the latent echo defect remained.

Observed failure start:

- Production exact gen05 at `2026-08-27T20:13:32+08:00`, under HEAD `e3a2bbd188a0d25f15a02cde1b2b6820df5dd583`, after gen04 was abandoned and authority advanced to generation 05.

Relevant mechanism history:

- `662942386c Fix gen04 semantic budget accounting` allowed abandoned generation 04 to preserve semantic budget and target generation 05 after terminalized partial planning.
- `e3a2bbd188 Merge gen04 semantic budget repair` is the production HEAD where gen05 executed.
- `662942386c` / `e3a2bbd188` opened the path to gen05; they did not create the six safety mismatches. The mismatches were produced by the existing provider echo contract when the gen05 Writer returned the external plan.

Durable invariant:

- For every coverage mapping, external identity coverage may use request-local `source_ref`, but local hydration must map it to current deterministic fact IDs and must reject any `safety_boundary` value that differs from `_source_fact_package()`.

Promotion / replacement boundary:

- A failed terminal planning contract must not promote to `locale-plan.json`, article, review, publish, or replacement lineage without an explicit bounded Repair. Since gen05 stopped before locale plan hydration, publication is correctly blocked.

## Minimal Repair Frontier

Recommended bounded Repair frontier:

1. Future provider output schema/prompt for JA continuation source_ref planning must remove `coverage_mapping.safety_boundary` entirely.
2. Provider input may still include deterministic `safety_boundary`, `protected_constraints`, and `boundary_candidate_dispositions`, but the prompt must mark them read-only local authority. The provider may use them to plan coverage and wording, not to classify or echo safety state.
3. Hydration must map `source_ref` to current facts and inject deterministic `safety_boundary` from `_source_fact_package()` into the hydrated local `locale-plan.json`.
4. Preserve the local hydrated `locale-plan.json` downstream shape with `source_fact_id`, `planned_h2`, `coverage_note`, and deterministic `safety_boundary`.
5. Add one exact regression test using this gen05 shape: complete `source_ref` coverage with six provider-invented `true` flags in legacy shape must be handled only by the explicit legacy-read path below; future-shape output must not contain `safety_boundary`; missing/duplicate/unknown refs must still fail closed.

Current gen05 external-plan promotion / replacement boundary:

- Do not modify the existing gen05 `external-plan.json` in place.
- If the system needs provider-free reuse of this already-written gen05 external-plan, it requires an explicit, versioned `legacy-read` adapter that accepts only the existing legacy shape, ignores the external `safety_boundary` assertion, and injects deterministic owner safety during hydration.
- That adapter must not silently generalize to future provider output. Future output schema must remove the field.
- Without such explicitly authorized adapter work, follow-up must terminalize/replace via a formally authorized bounded Repair. That is outside this RCA card.

why_not_less:

- Prompt-only wording is insufficient. The current schema still requires a boolean, and the provider can still over-infer risk semantics. Retrying the provider or editing the external artifact would only treat the symptom. The minimum effective change is schema/prompt removal plus local hydration injection.

why_not_more:

- No need to change JA protected constraint extraction, source fact IDs, source-ref-map lifecycle, semantic budget accounting, Reviewer, Publisher, replacement, or production queue state. Those layers behaved as intended in this evidence.

do_not_absorb:

- Do not absorb provider safety classification as authority.
- Do not auto-flip existing production external-plan in place.
- Do not silently reinterpret all historical plans; only a versioned legacy-read adapter may handle existing legacy shape.
- Do not rerun gen05 or create gen06 before the bounded Repair is reviewed and authorized.
- Do not weaken source_ref coverage fail-closed checks.

## Remaining Limits

- This RCA did not execute a production entrypoint and did not call any provider.
- The harness proves the current exact failure and root-cause boundary; it does not certify the proposed Repair green path because source edits were explicitly forbidden.
- CodeGraph was unavailable in this worktree, so code evidence used scoped file reads and exact line references from `<repo-root>/scripts/agy_multilingual_pipeline.py`.
