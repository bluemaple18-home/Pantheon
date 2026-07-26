# Resolved clarification

- previous_status: `BLOCKED`
- current_status: `RESOLVED`
- clarification_source: mainline replacement-card ruling

The allocation ordinal and irreversible digest are not required public receipt
fields. The public queue, inbox, and failed `credential_pool` object remains a
closed three-field schema:

- `pool_id`
- `slot_id`
- `manifest_sha256`

Ordinal uniqueness, continuity, and crash consumption are proved only through
the owner-only allocator state and synthetic test evidence. No allocator state
path, credential path, credential value, or ordinal is added to a public
receipt. `scripts/agy_gemini_outbox.py` remains outside the implementation
allowlist and will not be modified.
