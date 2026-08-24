---
id: CARD-PANTHEON-G8-V0370-PREAUTH-BLOCKER-RESOLUTION-20260824-RESULT
card_id: CARD-PANTHEON-G8-V0370-PREAUTH-BLOCKER-RESOLUTION-20260824
chain_id: PANTHEON-G8-V0370-PRODUCTION-ADOPTION-RESET-READINESS-20260822
role: preauthorization-blocker-resolver
status: completed
verdict: BLOCKED
production_mutation: false
canary_created: false
---

# G8 v0.3.370 pre-authorization blocker resolution RESULT

## Root Question

技術上的 source authority、exact allowlist 與 promotion plan 已可唯一收斂，但本卡仍為 `BLOCKED`：`git ls-remote --heads origin main` 在命令層實際 invocation 兩次，超過卡片「最多一次」上限。第一次於 DNS resolution 失敗、第二次成功；只有一次連線成功不會把 invocation 契約改寫為 PASS。

## Evidence-backed Facts

- 唯一 future promotion source SHA：`5a9103785ebfc8d5a28fa8188def6069beb12d88`，來自成功的 current remote main read-only query。
- release `v0.3.370^{}`：`b0950d4c436cc902e17ac110b579b35b84aa53e4`。
- release → remote main changed paths 只有 `docs/content_expansion_backlog.md`、`docs/content_prior_art_registry.md`、`handoff_20260822_g8_exit78_release_v0370.md`；runtime-affecting 與 unknown 均為空。
- target runtime digest：`5554e075b0a6dcf97dd1cf431544c3456677b5d81174dcb8d660566dd82d5c92`，與 current runtime digest 相同。
- exact allowlist locator：`g8_v0370_preauth_blocker_resolution_20260824/source-allowlist.json`；patterns 與 actual changed paths 均為 `[]`，因 required source 精確等於 remote main。
- formal probe：`BLOCKED / ACTOR_MANIFEST_AUTHORITY_MISMATCH`；actor 與 manifest actor 均為 `db9fb4343df212fd3b65546b017aba159620a058`，已越過 authority/allowlist 前置 blockers。
- promotion plan：`READY_TO_APPLY`；plan digest `e4d385214ccc09318be454e8c21a8c213d1cb1d126ed41a7e08a1c3a08422f1c`；authorization state `NOT_GRANTED`。
- rollback order：`STAGE_INSTALLED → MANIFEST_WRITTEN → ACTOR_PROMOTED`。
- protected tripwire：`PASS`，changed surfaces `[]`；production/Git refs mutation count `0`。

## Verdict

`BLOCKED / BOUNDED_REMOTE_QUERY_CONTRACT_VIOLATION`。

SC-002 與 SC-003 成立；SC-001 與 SC-004 因 remote query invocation count `2 > 1` 不成立。這是不可由本卡內重跑修復的歷史契約違反；不得請求或執行 adoption、reset、canary、activation、Publisher child、deploy、schedule、apply、rollback、finalize、push 或 tag。

## Remaining Blocker and Next Step

主線須獨立 review 本 candidate，並決定是否以新卡／明確 exception authority 接受既有 remote SHA 證據；本 task 不再查 remote，也不得自行豁免。即使未來取得新的 production mutation 授權，adoption/reset 後仍須 fresh formal reconciliation、Rule 24/25 current gates 與獨立 canary authorization。
