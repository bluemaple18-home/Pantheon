# RESULT-PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION-APPLY-2CE-20260828

## Verdict
PROMOTION_COMMITTED

## Transaction

- State: `COMMITTED`
- Plan digest: `2ff333ae34c1fcda2af919aa70c1c6428a8817672b4c1fb996f9d35a5d0409cf`
- Apply status: `POSTCHECK_PASSED`
- Finalize status: `COMMITTED`
- Rollback required: `false`
- Rollback bundle exists: `false`
- Rollback bundle finalized: `true`
- Transaction root: `/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/transactions/pantheon-acceptance-b-gen05-runtime-promotion-plan-2ce-20260828`

## Runtime Authority

- Actor SHA: `2ce431ec41f5187531d88b52dfa91cef0373d8b5`
- Actor origin: `git@github.com:bluemaple18-home/Pantheon.git`
- Actor dirty: `false`
- Manifest digest: `7dbedf4e8544675f6203c2d40f96afa561d961a2c7e5a445c8d1f821f0d369f9`
- Manifest actor head: `2ce431ec41f5187531d88b52dfa91cef0373d8b5`
- Manifest generation: `g55-2ce431ec-gen05-runtime-promotion-plan-20260828`
- Manifest runtime digest: `1c4bc28cda62a56fcf31bf007fd7905c4a45a5e1ca6b9fb8d0e9bfcb94498d21`
- Stage digest: `51d0e46da1c495ecf1d717011199444e485754498887823bce1fb17abbac0e29`
- Stage readiness count: `7`
- Stage barrier valid: `true`

## Origin Main

- Local origin/main: `2ce431ec41f5187531d88b52dfa91cef0373d8b5`
- Fresh remote main: `9a43d550aad4c2663abc2ea537ff4db31fd2db1f`
- Remote main contains target: `true`
- Remote merge-base with target: `2ce431ec41f5187531d88b52dfa91cef0373d8b5`

## Protected Bytes

- Queue snapshot before plan: `d466eb1c7523ccbeb48f0d48d0f6dec143e3c87982d54327326190139b3ce498`
- Queue snapshot after finalize: `d466eb1c7523ccbeb48f0d48d0f6dec143e3c87982d54327326190139b3ce498`
- Queue identity before plan: `ba63e493e972f640d44e40b9b75d5cbef8b1b88d7fda851793d2559eb24ed739`
- Queue identity after finalize: `ba63e493e972f640d44e40b9b75d5cbef8b1b88d7fda851793d2559eb24ed739`
- Preserved run count: `136`
- State tree before plan: `e99ce8adc6b8588bc0eb9055f9550368d9ce38bad5a2b4f7a9ae514a370caa62`
- State tree after finalize: `73fbf2c7a4596d5fa345b04605072e16656f8792c8c52500bd0e47f3c429281e`
- Target barrier exists after finalize: `true`

## Mutation Counters

- promotion_apply: `1`
- promotion_finalize: `1`
- promotion_rollback: `0`
- transaction: `1`
- transaction_root_created: `true`
- gen04_to_gen05_transition: `0`
- gen05_provider: `0`
- provider_calls: `0`
- publish: `0`
- tag: `0`
- push: `0`
- deploy: `0`
- service_mutation: `0`

## Evidence

- Apply stdout: `apply.stdout.txt`
- Finalize stdout: `finalize.stdout.txt`
- Official status stdout: `status-after-finalize.stdout.txt`
- Postcheck receipt: `postcheck-receipt-2ce.json`
- `git diff --check`: `PASS`
- Code/config modified: `false`; workspace change is execution evidence only.

Sampled at: `2026-08-28T01:26:09+00:00`
