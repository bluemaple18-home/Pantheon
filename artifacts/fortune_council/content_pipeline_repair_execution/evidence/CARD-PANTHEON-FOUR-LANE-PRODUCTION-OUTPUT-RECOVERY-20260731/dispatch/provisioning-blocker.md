# Visible thread provisioning blocker

- recorded_at: 2026-07-31 Asia/Taipei
- dispatch_key: `v1:3dc5b577b0a24987083ade7b817d666018e78da7190ba28d742616c00ffc8be1`
- formal_thread_id: `019fb593-406b-7212-8b17-25daa2f63c8e`
- host_id: `slingshot:env_e_6a17b3781858832daee8697c30fc7e7c`
- project_id: `c2xpbmdzaG90OmVudl9lXzZhMTdiMzc4MTg1ODgzMmRhZWU4Njk3YzMwZmM3ZTdjCi9Vc2Vycy9tYXR0a3VvL0RvY3VtZW50cy9QYW50aGVvbg==`
- worktree: `<codex-home>/worktrees/c8eeb5a2-3a1c-4de7-bfad-e62cbdbe01a3/Pantheon`
- worktree_state: `clean`
- reservation_state: `BLOCKED`
- blocker_code: `BASE_SHA_MISMATCH`
- required_base_ref: `origin/main`
- required_base_sha: `dde0cd214fea9b9e6567ed5ec7b7a82113cc836d`
- actual_head: `de68b6b283493a3e9ca5f80286c682cb7846735e`
- actual_origin_main: `de68b6b283493a3e9ca5f80286c682cb7846735e`
- activation_token: `null`
- implementation_started: `false`

## Evidence

The formal thread is visible and completed only its read-only bootstrap preflight.
Its clean worktree was provisioned at the current `origin/main`, but the current
ref advanced beyond the card's frozen SHA before activation.

The required SHA is an ancestor of the actual SHA. The delta contains five
content-release commits:

1. `d8b4b08e5` — `chore(content): publish Gemini approved articles v0.3.179`
2. `9de476baa` — `chore(content): publish Gemini approved articles v0.3.180`
3. `b619d7c17` — `chore(content): publish Gemini approved articles v0.3.181`
4. `7aa19ee49` — `chore(content): publish Gemini approved articles v0.3.182`
5. `de68b6b28` — `chore(content): publish Gemini approved articles v0.3.183`

No activation message was sent. No file edit, test, provider call, commit, push,
production mutation, or replacement thread occurred in the formal worktree.

## Required next decision

Dispatch v4 does not allow retrying activation on this durable blocked
reservation. Continuing requires explicit authorization to create a
`-RETRY-1` successor card/reservation pinned to the newly frozen base SHA.
