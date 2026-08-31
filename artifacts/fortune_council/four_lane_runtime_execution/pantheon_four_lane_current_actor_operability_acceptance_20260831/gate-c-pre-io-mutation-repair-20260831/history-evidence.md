# History and owner evidence

- Lock owner: `scripts/agy_gemini_coordinator.py:656-670`, introduced by `b914d6cc37a` (`Make exact run creation transactional`). It creates `run-identity-locks/<id>.lock` before yielding.
- Generation retry owner: `scripts/agy_gemini_coordinator.py:6210-6366`, introduced by `18b121fa335` (`fix: retry failed locale plan in same generation`). Its first generation-boundary validation is at :6239-6244, before the execute lock; a second validation is inside the lock at :6336-6339.
- Wrong-mode owner: `reconcile_translation_replacement_identity` at :3027-3281, introduced by `ced72054eb` (`fix(i18n): reconcile replacement run identity`). Its execute path currently enters `_run_identity_lock` at :3249 before `build_plan()` validates the brief mode.
- Last known test contract: prior G1 and G3 receipts allowed one empty lock; no historical version demonstrates strict no-lock behavior for concurrent post-lock drift. The durable invariant required by this card is invalid input rejection before any durable lock/directory mutation.
