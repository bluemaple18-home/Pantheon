# PANTHEON G8 V0381 exact-target preactivation rerun

## Verdict

`BLOCKED`

正式 machine contract 回傳 `BLOCKED / ACTOR_MANIFEST_AUTHORITY_MISMATCH`。本地 source checkout 是 exact target，但 production actor 與 runtime manifest 仍綁定 `db9fb4343df212fd3b65546b017aba159620a058`，不是 required source `5872284828f9dd6f0a75adf407becaeadb50d61a`。

## Identity matrix

| 項目 | SHA / digest | 判定 |
| --- | --- | --- |
| required source / target | `5872284828f9dd6f0a75adf407becaeadb50d61a` | PASS |
| local HEAD | `5872284828f9dd6f0a75adf407becaeadb50d61a` | PASS |
| remote main | target value from prior published receipt；本次 `ls-remote` DNS/SSH failure | UNKNOWN |
| production actor HEAD | `db9fb4343df212fd3b65546b017aba159620a058` | BLOCKED |
| manifest actor_head | `db9fb4343df212fd3b65546b017aba159620a058` | BLOCKED |
| manifest digest | `d067358d4d6228483484cdd984f25963ccbe131e8250e4a131ea10a6e6d6e08e` | observed |

正式判定前初始 worktree status 為 clean；判定後才建立本卡 evidence。remote 核對只嘗試一次，未 retry。

## Fresh protected evidence

- formal result: `g8_v0381_exact_target_preactivation_rerun_20260824/formal-machine-result.json`
- before snapshot: `g8_v0381_exact_target_preactivation_rerun_20260824/before/protected-snapshot.json`
- after snapshot: `g8_v0381_exact_target_preactivation_rerun_20260824/after/protected-snapshot.json`
- tripwire: `g8_v0381_exact_target_preactivation_rerun_20260824/mutation-tripwire.json` → `PASS`, `changed=[]`
- manifest/actor/source evidence: same directory `manifest-identity.json`, `actor-head.txt`, `source-head.txt`

Protected roots remained unchanged: queue, state, transactions, live, staged, manifest, publisher lock, git refs and packed refs. Formal result records `production_mutation=false`.

## Next step

唯一下一拍：先以獨立、非 production workflow 將 actor/manifest authority 收斂到 exact target，再開 fresh preactivation。因目前 BLOCKED，不產生 adoption/reset authorization payload。

## Explicit boundary

未 push、未 fetch、未 pull、未 tag、未 remote-ref write；未 production write、未 adoption、未 reset、未 deploy、未 canary、未 launchctl mutation。
