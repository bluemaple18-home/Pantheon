# CARD-PANTHEON-G8-V0370-RULE24-DSSE-OPENSSL-ATTESTATION-20260824 RESULT

## 狀態

- status: CANDIDATE_READY
- parent: `4d59fa859c06789e94c4b1f15571ebb8b06ed5ea`
- production_mutation: false
- canary_created: false
- remote_query: 0
- dependency_install: 0
- push_tag_deploy_integrate: 0

## Repair 001 status

- status: SUCCESSOR_CANDIDATE_READY
- repair_parent: `36edc4d323f9f1a2624158e8376cb2570b7d01fa`
- repair_followup_parent: `9b407901669502b97b6e220fc268162c7b98defc`
- repaired_P1:
  - Same envelope + consumed=false challenge now PASS only once; second verify returns `challenge_replay`.
  - Concurrent verifiers now race on stdlib exclusive-create claim; at most one verifier returns PASS.
  - Producer now proves supplied private/public keypair with an OpenSSL sign/verify probe; mismatch returns `key_pair_mismatch` without authenticated PASS fields.
  - Application-facing `verified_payload_observer` is now called only after replay claim succeeds; replay NO-GO keeps observer calls at 0 for the rejected attempt.
  - Claim create/write `OSError` returns deterministic `NO-GO/replay_state_claim` without releasing payload to observer.
- replay_state_contract:
  - verifier requires caller-supplied `replay_state_dir`.
  - replay state path must be absolute, canonical, existing directory, and repo-external.
  - claim is created only after signature, trust policy, target, policy, measurements, challenge, and freshness verification.
  - authenticated payload observer is called only after claim succeeds.
  - claim uses `os.O_CREAT | os.O_EXCL`; no read-then-write replay decision.
  - claim contains only schema, challenge digest, authenticated statement digest, and claim time.

## Repair Exception 003 status

- status: SUCCESSOR_CANDIDATE_READY
- repair_exception_parent: `8f09e88f4087e2993daa84e9c9ca1c3f51b3f3f8`
- repaired_P1:
  - `_load_json()` 將非 UTF-8 fixture 的 `UnicodeDecodeError` 收斂為既有 deterministic `Rule24AttestationError`，未使用 broad `except Exception`。
  - 非 UTF-8 trust policy 回傳 `NO-GO/trust_policy`。
  - 非 UTF-8 challenge fixture 回傳 `NO-GO/challenge_contract`。
  - 非 UTF-8 envelope CLI 回傳 exit `2`，stdout 為 machine-readable `NO-GO/envelope_contract` JSON。

## 交付內容

- `scripts/pantheon_rule24_dsse_attestation.py`
  - Pantheon-owned minimal DSSE envelope / PAE / in-toto Statement v1 glue。
  - Ed25519 sign/verify 與 public key DER export 全部委派給 PATH `openssl`。
  - producer/verify API 與 explicit `produce` / `verify` CLI。
- `tests/test_pantheon_rule24_dsse_attestation.py`
  - 43 個 focused tests，覆蓋 trusted path、CLI JSON roundtrip、非 UTF-8 trust policy/challenge/envelope、determinism、DSSE tamper、key substitution、statement binding、policy/measurement drift、sequential replay、concurrent replay claim、replay observer ordering、replay_state_claim OSError、pre-validation no-claim、trust-policy mismatch、verify-then-parse、OpenSSL fail-closed、canonical path 與 repo key audit。
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
  - Repair 001 keypair probe uses the same OpenSSL sign/verify path with synthetic non-secret probe bytes.

## OpenSSL capability receipt

- PATH openssl: `/opt/homebrew/bin/openssl`
- version: `OpenSSL 3.6.2 7 Apr 2026`
- ED25519: present in legacy and default provider list (`1.3.101.112`, `ED25519`)

## Verification receipt

- TDD red: PASS，focused pytest first failed on missing `scripts.pantheon_rule24_dsse_attestation` module.
- Focused pytest: PASS，initial candidate `34 passed in 2.62s`; Repair 001 `38 passed in 3.31s`; Repair 001 follow-up `40 passed in 3.43s`; Repair Exception 003 `43 passed in 3.98s`
- Test runtime path: `/Users/mattkuo/Documents/Pantheon/.venv/bin/python`
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
- P2：replay claim 檔若在 exclusive create 後遭中斷而為空檔，仍是已知 residual risk；本次修復依契約明確不處理。
