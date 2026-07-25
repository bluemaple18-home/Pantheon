# Authentication hardening decision

Date: 2026-07-25

Decision: `READY_FOR_REVIEW`

## Current production candidate

- Keep the reviewed owner-only API-key FD path.
- Do not add a CLI OAuth adapter, token-cache parser, credential pool, retry,
  redirect or fallback.
- Do not implement ADC without a formal Google Cloud project, identity, quota
  project, credential lifecycle and reviewed runtime dependency.
- Keep V4 opt-in only. This decision does not authorize activation, default
  promotion, deploy or publish.

## Key classification

The three existing keys were inventoried without exposing their values. Key
type remains `UNKNOWN`: the key prefix cannot prove standard versus
authorization key, and no active Google control-plane identity is available.

Before default promotion, require either:

1. control-plane evidence that the selected key is an authorization key; or
2. a separately reviewed OAuth/ADC or Vertex workload-identity migration.

## Stable migration seam

Future ADC work may replace only the authentication header provider. It must
preserve the existing request body, provider-schema projection, one model
POST, no retry, no redirect, durable ledger, receipt, replay and fail-closed
semantics.
