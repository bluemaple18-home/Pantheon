# Runtime alignment

## Result

```text
status: PASS_SHA_ALIGNED_SERVICES_STOPPED
verified_at: 2026-07-31T10:51:45+08:00
source_sha: 66009a3014ee51ba8977b2cbd33462fc37c029ff
origin_main_sha: 66009a3014ee51ba8977b2cbd33462fc37c029ff
actor_sha: 66009a3014ee51ba8977b2cbd33462fc37c029ff
```

Publisher deployment preflight after all canary attempts:

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
