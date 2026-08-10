# Slice A parent-swap RED

## Scope

- card_id: `CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-001`
- dispatch_key: `v1:f37e9811684d638ecb5c209642f01e32db83be35b97e04ab36c19157bf470b13`
- activation_token: `act-v1:3f4d40e311f66d179c33f9d6a9a3c15076eeb4304c290be0bfd7842484c1c876`
- phase: Slice A only

## RED command

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pantheon_runtime_fs_authority.py
```

## RED result

- exit code: `1`
- result: `1 failed in 0.09s`
- target symptom: parent-swap validation returns successfully, then `formal_capability_preflight()` raises `PublishBlocked` only after external filesystem I/O already happened.
- external tree delta: before empty; after contains `publisher-state` with 2 entries.
- pytest `raises` assertion: matched `PublishBlocked`, proving the public entrypoint eventually detected escaped mutation, but too late.
- source mutation during RED: none beyond the already-added public-behavior test.

## RED conclusion

This is the accepted Slice A RED: the public preflight fails to block before the first queue/state filesystem boundary when the trusted sandbox parent is swapped after descendant validation.
