# CARD-PANTHEON-G8-V0370-RULE24-DSSE-OPENSSL-ATTESTATION-20260824 RESULT

## 狀態

- status: CANDIDATE_READY
- parent: `4d59fa859c06789e94c4b1f15571ebb8b06ed5ea`
- production_mutation: false
- canary_created: false
- remote_query: 0
- dependency_install: 0
- push_tag_deploy_integrate: 0

## 交付內容

- `scripts/pantheon_rule24_dsse_attestation.py`
  - Pantheon-owned minimal DSSE envelope / PAE / in-toto Statement v1 glue。
  - Ed25519 sign/verify 與 public key DER export 全部委派給 PATH `openssl`。
  - producer/verify API 與 explicit `produce` / `verify` CLI。
- `tests/test_pantheon_rule24_dsse_attestation.py`
  - 34 個 focused tests，覆蓋 trusted path、CLI JSON roundtrip、determinism、DSSE tamper、key substitution、statement binding、policy/measurement drift、challenge replay、trust-policy mismatch、verify-then-parse、OpenSSL fail-closed、canonical path 與 repo key audit。
- `artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_rule24_dsse_openssl_attestation_20260824/validation_receipt.json`
  - 本卡驗證 receipt。

## Provenance

- 規格常數 / wire contract
  - in-toto Statement v1 `_type=https://in-toto.io/Statement/v1`
  - DSSE `payloadType=application/vnd.in-toto+json`
  - DSSE PAE bytes: `DSSEv1 <len(payloadType)> <payloadType> <len(payload)> <payload>`
  - Rule24 fixed `predicateType=https://pantheon.local/rule24/trust-predicate/v1`
- Pantheon 自有 glue
  - ResourceDescriptor binding、canonical JSON bytes、caller-supplied trust policy、caller-owned challenge fixture、machine-readable PASS / NO-GO receipt、zero-side-effect flags。
  - 沒有複製或 vendor `securesystemslib`、`in-toto` 或其他第三方 repository 的 source file/class/function。
- OpenSSL 委派
  - `openssl version`
  - `openssl list -public-key-algorithms`
  - `openssl pkey -pubin -outform DER`
  - `openssl pkeyutl -sign -rawin`
  - `openssl pkeyutl -verify -rawin -pubin`

## OpenSSL capability receipt

- PATH openssl: `/opt/homebrew/bin/openssl`
- version: `OpenSSL 3.6.2 7 Apr 2026`
- ED25519: present in legacy and default provider list (`1.3.101.112`, `ED25519`)

## Verification receipt

- TDD red: PASS，focused pytest first failed on missing `scripts.pantheon_rule24_dsse_attestation` module.
- Focused pytest: PASS，`34 passed in 2.62s`
- py_compile / AST parse: PASS
- PAE vector: PASS，`PAE("test", b"abc") == b"DSSEv1 4 test 3 abc"`
- OpenSSL failure matrix: PASS，missing / unsupported / timeout / nonzero all NO-GO。
- JSON parse: PASS，artifact receipt parse verified。
- git diff --check: PASS
- ownership audit: PASS，only owned files changed。
- dependency audit: PASS，`pyproject.toml` / `uv.lock` unchanged。
- private-key audit: PASS，repo diff contains no `.pem`, `.key`, or private-key fixture。
- vendor/header audit: PASS，diff contains no third-party copyright header, vendored module, or dependency addition。

## Remaining risks

- 本卡只建立 Rule24 evidence statement 的可信簽驗與 binding primitive；不做 Rule24 domain metric / threshold evaluation。
- 正式 key provisioning 與正式 trust-policy mutation 仍在本卡 scope 外。
- 後續 composition card 需要把本 primitive 接到既有 capacity evaluator 與 Rule24 evidence composition。
