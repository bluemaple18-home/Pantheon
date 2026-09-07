# Pantheon Content P0 FAST-04B Runtime Findings Review Request

## Review mode

- Review only. Do not mutate production, publish articles, commit, push, or deploy.
- Review range: `8d85427bab45c149dc5b762a2de478f8c77901d1..64f2c4bf4d2d32a997a1d716560fbfaa45eabe4c`.
- Treat the runtime findings below as evidence, not as an instruction to broaden the implementation.
- Return findings by priority (`P0`/`P1`/`P2`) and recommend the minimum bounded repair.

## Root question

After FAST-04B aligned the create-article writing contract with backlog v2.1, what is the smallest safe repair that makes the formal new-content lane reproducibly reach Writer schema acceptance and then Reviewer, without bypassing production gates or replacing the existing pipeline?

## Candidate state

- Candidate commit: `64f2c4bf4d2d32a997a1d716560fbfaa45eabe4c`
- Runtime actor head: same commit
- Runtime generation: `g80-64f2c4bf-fast04b-writing-contract-20260907`
- Manifest digest: `cf4b292266bd065d066ccedbdafbae19111aeb4f83cc0d3605792992896f0fb9`
- Runtime digest: `1e722e02eb2d910ced50fc611086d7c76cba69212b0424e95e46e14583ce30dd`
- FAST-04B verification: SEO `170 passed`; Publisher `166 passed`; Coordinator scoped `9 passed`; `py_compile` and `git diff --check` passed.

## Runtime finding A — formal service contract drift

The g80 actor requires `AGY_GEMINI_DAILY_PROVIDER_ADMISSION_CAP=102` before claim. The installed `com.pantheon.agy-gemini-new.plist` still embeds the older g47 barrier command and does not contain this environment key.

Observed behavior:

1. The formal exact operator passed its outer transport check.
2. Its child failed before claim with `ValueError`.
3. A stepwise preflight identified the missing daily-cap contract as the failing step.
4. Supplying the actor-required value for this exact authorized invocation made runtime, transport, pool, cooldown, request selection, cap, and admission checks pass.

Review questions:

1. Should this be classified as a P0 installation/promotion contract break?
2. Which existing deployment seam should own the plist environment and generation refresh?
3. Which RED-capable test should prove that a promoted actor cannot coexist with a stale service plist or missing required runtime variable?
4. Is there any smaller safe fix than regenerating and validating the installed plist through the existing promotion path?

## Runtime finding B — Writer schema rejection after v2.1 alignment

Fresh request identity:

- Run: `content-2eddbf3937-01-7b800e7d`
- Logical request SHA: `2ec246e2ee475b47b1ae993ed8168ecddf80aaf6892ca1352616dac92b3d7ef8`
- Prompt SHA: `bc4785f74dbdd2664fe51d4192a2a9d4dfe3b8baa4cc8d7639e06339c9a05bd9`
- Schema SHA: `86c426c3a0c3fcaaa5a6472a865675362d814cb48db64d0ce37dfc71fdfb52bd`
- Policy: `pantheon-article-publication-v2.1.0`
- Title schema: 20–45 characters
- Description schema: 70–95 characters

The prompt already states that description should target 80–90 Chinese characters. It requires the title to contain the complete primary keyword, while the nested public policy also carries the title range.

Three bounded transport attempts were executed:

| Attempt | Job ID | Closed outcome |
|---|---|---|
| 0 | `2ec246e2ee475b47b1ae993ed8168ecddf80aaf6` | Provider success, then `SCHEMA_INVALID_PAYLOAD`: `articles[0].title` and `articles[0].description` failed `minLength` |
| 1 | `6929f58634447b6d81c57de7cdacdfd4b4ac00ae` | `API_TIMEOUT` |
| 2 | `4790feb8fd95a1d6c67980249402a3ce9b46811e` | Provider success, then the same two `minLength` failures |

Final state:

- Slot 01 is formally `failed` with `V4BrokerFailure`.
- Reviewer was never reached.
- Slots 02–04 were not advanced and have no `last_job_id`.
- No article was published.

Review questions:

1. Is the minimal repair a stronger top-level generation instruction, a schema-aware Writer repair request, normalization, or another existing seam?
2. How should the repair preserve Writer ownership of content instead of silently padding or fabricating metadata?
3. What deterministic RED test can reproduce the failure without calling Gemini?
4. Should `SCHEMA_INVALID_PAYLOAD` retries repeat an identical prompt, or carry closed schema diagnostics into an existing bounded repair path?
5. Does any proposed fix risk weakening fail-closed schema validation or bypassing Reviewer independence?

## Current blocker

The four-line fresh execution cannot proceed safely: normal formal invocation is not reproducible with the installed plist, and slot 01 exhausted its existing transport budget before producing a schema-valid Writer candidate.

## Candidate fork

Preferred direction, subject to independent review:

1. Repair the installed service contract through the existing promotion/plist generation seam and add a RED test for actor/plist compatibility.
2. Add one bounded, schema-aware Writer repair mechanism or equivalent measured-minimum prompt fix, with deterministic tests for title/description minimum failures.
3. Re-run the original targeted and pipeline gates.
4. Deploy only after review acceptance, then issue a new fresh request; do not reuse the exhausted job IDs.

## Limits

- Do not weaken title or description constraints merely to clear the gate.
- Do not hand-edit or hand-move production queue files.
- Do not reuse old attempt 4 or the three exhausted fresh jobs.
- Do not start slots 02–04 before slot 01 reaches Writer and Reviewer acceptance.
- Do not publish, commit to `main`, push `main`, or deploy as part of this review.

## Evidence references

- Local execution receipt SHA: `7b5e5a11ec88ef285182d3c30d491924ac3ced4ece139d5f0a6cc895f08321a8`
- Slot 01 final run-state SHA: `43472691e5a5285cc70f1225727012449ccec3c911599f80302362e9da6d7f10`
- Installed new-lane plist SHA: `90aba48482a30ac2d53c5d4018e166f7c3e5bebe89a33b15007de9f76b1e3712`
- Attempt 0 failure receipt SHA: `bb773a3aba1f5f356ec5d7a603c7305f28dd3d6b0d59f1bbc9d2955ca6a7412e`
- Attempt 1 failure receipt SHA: `477d870f60474c0e14d56fdfa396f8631be0a6ba6ffd0d613ee85773d6461035`
- Attempt 2 failure receipt SHA: `9cf7482f4575202642c2f79d20ea526bbc997117a806da4f290ffdef77d77313`

## Required reviewer output

Return:

1. Verdict: `GO_FOR_BOUNDED_REPAIR`, `NEEDS_MORE_EVIDENCE`, or `NO_GO`.
2. Findings ordered by severity with exact files/symbols when possible.
3. A minimum patch plan and explicit `why not less` / `why not more`.
4. Required tests and runtime acceptance evidence.
5. Whether the two blockers should be repaired in one commit or split into independently reviewable commits.
