# Runtime alignment

## Result

```text
status: PASS_EXACT_FINAL_ORIGIN_MAIN_SERVICES_STOPPED
verified_at: 2026-07-31T10:51:45+08:00
canary_execution_sha: 66009a3014ee51ba8977b2cbd33462fc37c029ff
source_ref: origin/main
actor_ref: exact final origin/main after this evidence commit
```

Publisher deployment preflight at canary execution SHA:

```text
status=ready
mode=read-only
actor=matched
queue=matched
state=matched
runtime_digest=306333ac9502409156c32b74ae3572cd7648077ab78af5c9ecb0802d5ab8d552
push_mode=push
```

The installed Publisher plist expects the same full runtime SHA. The installed
Gemini coordinator points to `<publisher-actor-root>` and `<queue-root>`, with
`NEW_ONLY=1` retained from the isolated new-canary phase.

The NO-GO evidence commit necessarily advances `origin/main` after the canary
execution SHA. To avoid a self-referential commit hash, this receipt records the
final contract by ref: after the final evidence push, the stopped actor and the
installed Publisher expected SHA are updated to that exact `origin/main`, then
the official read-only deployment preflight is rerun. The exact resulting SHA
is reported in the operator handoff without creating another repository commit.

All six related LaunchAgents are intentionally unloaded:

- Publisher
- coordinator
- new
- rewrite
- i18n-new
- i18n-rewrite

They remain stopped because `<queue-root>/lanes/new/outbox/` contains an
unconsumed replacement repair job that is not covered by the consumed canary
authorization. Restarting the services would risk an unapproved provider call.

No queue、ledger、candidate、archive or production attempt artifact was deleted
or reset.
