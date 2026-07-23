# Gemini V4 Publish-main Integration｜Decision

## Delivery

`DELIVERED_CANDIDATE / READY_FOR_INTEGRATION_REVIEW`

## Evidence

- Locked publish base and V4 reviewed tip merged with zero conflicts.
- Publication/article/automation paths have zero drift relative to publish base.
- V4, legacy, coordinator and publisher regressions total `142 passed`.
- Static, ancestry, privacy and diff gates passed.
- No external invocation, queue mutation, article generation, push, deploy, publish or
  default switch occurred.

## Remaining gate

`origin/main` is actively advanced by the content publisher. The candidate is valid
against fixed base `v0.3.7`, but remote integration must not occur until:

1. an independent Reviewer approves this fixed merge;
2. publisher coordination provides a bounded synchronization window;
3. later origin commits are merged and the affected gates are rerun.

This decision does not authorize activation, default promotion or legacy removal.
