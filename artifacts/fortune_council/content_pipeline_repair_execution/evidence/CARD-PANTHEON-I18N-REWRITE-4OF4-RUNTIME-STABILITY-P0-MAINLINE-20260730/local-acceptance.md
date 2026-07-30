---
id: CARD-PANTHEON-I18N-REWRITE-4OF4-RUNTIME-STABILITY-P0-MAINLINE-20260730-LOCAL-ACCEPTANCE
status: LOCAL_ACCEPTED_EXTERNAL_AUTH_PENDING
type: mainline-acceptance-evidence
accepted_at: 2026-07-30 Asia/Taipei
---

# Runtime／Transport P0 Mainline Local Acceptance

## Lineage

- Parent base：`0e9870764b193d5d45e131c8b7ba284ab65a2862`
- Implementation card commit：
  `7c0ce9f637ade2684751c6c1938999f20476d1fa`
- Implementation candidate：
  `b7f4b0f1bf1c40f3c62e1d65038a0b9011c4c4ad`
- Independent Review evidence：
  `31156da5a2a7af11f1c39df53d2ffc24129ad2e7`
- Review verdict：`REVIEW_NO_GO`
- Blocking finding：`RT-TR-REV-001`
- Repair-1 candidate：
  `8812be81eb560a5445add0239ad4e50d2a339fd5`
- Targeted re-review evidence：
  `a3ab853e04ecce632d3577291d54e9e5640f96e8`
- Targeted re-review verdict：`REVIEW_GO`
- Integrated mainline commit：
  `f8278d84a57526ed05b54c8b0d7ac9ac268b42cc`

Implementation、Review 與 Repair 均有獨立 formal thread及 worktree；Review／Repair
未在 Implementation thread內混線。

## Accepted scope

### P0-A — Publisher runtime identity

- Runtime identity使用封閉 `TRANSACTION_RUNTIME_PATHS` manifest。
- Manifest綁定 path membership、byte length與 SHA-256，再以 canonical JSON產生
  runtime digest。
- Content-only `origin/main` descendant仍可通過 deployment preflight。
- Runtime path、membership、bytes或 expected digest漂移時 fail closed。
- LaunchAgent template、installer與 CLI parser的 runtime digest argument一致。

### P0-B — Transport／semantic budget separation

- Provider／payload failure有 closed category與 operation receipt。
- Schema-invalid payload在 inbox與 semantic repair前拒絕。
- Retry使用 explicit allowlist：
  `CLI_NONZERO`、`MALFORMED_PAYLOAD`、`NETWORK`、
  `PROVIDER_UNAVAILABLE`、`SCHEMA_INVALID_PAYLOAD`。
- `AUTH`、`QUOTA`、`MODEL_UNAVAILABLE`、`CLI_UNAVAILABLE`立即 terminal。
- Bounded retry維持 logical request SHA，queue attempt可區分，不推進 semantic
  repair且不建立 candidate／approval／apply／publish副作用。

## Mainline fresh verification

Command：

```text
<shared-venv-python> -m pytest \
  tests/test_agy_content_publisher.py \
  tests/test_agy_seo_copy_pipeline.py \
  tests/test_agy_multilingual_pipeline.py \
  tests/test_agy_gemini_outbox.py \
  tests/test_agy_gemini_transport_probe.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_gemini_v4_broker.py \
  tests/test_agy_gemini_reviewer_cutover.py -q
```

Result：`462 passed, 1 warning in 83.53s`。

Warning為既有 selector-resolution `DeprecationWarning: invalid escape sequence '\/'`，
不影響本 acceptance。

```text
git diff --check 0e9870764b193d5d45e131c8b7ba284ab65a2862 HEAD
```

Result：PASS。

## Current boundary

- P0-A／P0-B：`LOCAL_ACCEPTED`。
- P0-C i18n-rewrite第一篇真實發布：尚未執行。
- 尚未 push、deploy、安裝／重裝 LaunchAgent、呼叫 provider或 publish。
- Production actions必須另取得精確授權，並在執行前鎖定：
  - push branch／target ref；
  - deployment target與 runtime digest；
  - 唯一 deferred `fortune-0039` locale run；
  - provider operation與 sanitized capability probe；
  - next scheduler／Publisher cycle觀察窗口。
