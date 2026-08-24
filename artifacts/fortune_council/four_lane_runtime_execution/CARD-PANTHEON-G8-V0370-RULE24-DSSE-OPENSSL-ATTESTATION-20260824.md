---
id: CARD-PANTHEON-G8-V0370-RULE24-DSSE-OPENSSL-ATTESTATION-20260824
chain_id: PANTHEON-G8-V0370-PRODUCTION-ADOPTION-RESET-READINESS-20260822
role: rule24-dsse-openssl-attestation-implementer
status: ready
type: implementation
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
required_base_ref: main
implementation_baseline_sha: 47e817f6bd23ef63de6dc1f549375eb30eb097d4
traces_to:
  - RULE24-TRUST-01
  - RULE24-TRUST-02
  - RULE24-TRUST-03
ownership:
  - scripts/pantheon_rule24_dsse_attestation.py
  - tests/test_pantheon_rule24_dsse_attestation.py
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0370-RULE24-DSSE-OPENSSL-ATTESTATION-20260824-RESULT.md
  - artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_rule24_dsse_openssl_attestation_20260824/**
forbidden_scope:
  - 安裝、下載或新增 Python/Node/system dependency；不得修改 pyproject.toml、uv.lock 或 lockfile
  - production、launchctl、plist、runtime、queue、state、transaction、stage、barrier mutation
  - remote Git query、fetch、pull、push、tag、branch/ref mutation
  - key provisioning、正式私鑰產生、正式 trust-policy mutation
  - 整合或修改 candidate 0af881df2a7091e5a6817bc4ba1a4de8c26671cb
  - 修改既有 capacity harness、其他 source/tests/config/registry/metadata/evidence
---

# G8 v0.3.370 Rule24 DSSE/OpenSSL attestation trust primitive

## 工作名稱 → 正在做什麼 → 現在狀態

Rule24 DSSE/OpenSSL attestation → 吸收 in-toto Statement v1 與 DSSE v1 契約，沿用機器既有 OpenSSL Ed25519，建立離線 producer/verifier trust primitive → `READY / IMPLEMENTATION ONLY`。

## Root Question

能否在不安裝任何套件、不自行實作密碼學、也不碰 production 的前提下，讓 Pantheon 用既有 OpenSSL 對 Rule24 evidence statement 做 DSSE Ed25519 簽驗，並由 verifier-owned trust policy、policy digest 與 one-time challenge 決定 authority？

## Confirmed Facts

- 主機已有 `OpenSSL 3.6.2`，公開能力列出 `ED25519`。
- Pantheon `.venv` 目前沒有 `cryptography`、`securesystemslib`、`in_toto`。
- 採用語意：in-toto Statement v1、DSSE PAE、外部 pinned public key、verifier-owned policy、authorization challenge。
- 不採用：SLSA Provenance 作 Rule24 schema、Sigstore keyless/Rekor、`JSON + SHA256` 自證、receipt 內 keyid 作 authority。
- `0af881df2a7091e5a6817bc4ba1a4de8c26671cb` 未整合且不得作本卡 baseline。

## Requirements

### RULE24-TRUST-01 — DSSE/in-toto contract

- 使用 `_type=https://in-toto.io/Statement/v1`。
- 使用 `payloadType=application/vnd.in-toto+json`。
- 使用固定 Rule24 `predicateType`，predicate 至少綁：schema version、producer informational id、authorization correlation/challenge、Rule24 policy ResourceDescriptor、精確兩個 measurement ResourceDescriptor。
- subject 必須綁 expected target name/type/digest；不得只靠 receipt 自己聲稱 target。
- DSSE signature 必須簽 `PAE(payloadType, exact_payload_bytes)`；驗證後只能解析同一組已驗 bytes。

### RULE24-TRUST-02 — existing OpenSSL capability

- 只用 Python stdlib 與 PATH 既有 `openssl`；禁止 package install、vendoring crypto、手寫 Ed25519。
- subprocess 必須 argv-only、無 shell、bounded timeout、capture output、fail closed。
- 啟動先驗 `openssl version` 與 Ed25519 capability；缺能力輸出 deterministic NO-GO/error code。
- 實作不得產生正式 key；測試可在 `tmp_path` 內產 ephemeral Ed25519 keypair，結束不留 repo artifact。

### RULE24-TRUST-03 — external authority and replay boundary

- verifier-owned trust policy 必須從獨立 caller-supplied fixture path 讀取；至少綁 producer id、pinned public-key fingerprint、allowed predicate type、threshold=1。
- receipt/envelope 內 `keyid` 僅是 hint；不得提供、替換或擴張 trusted key set。
- verifier 必須從 supplied pinned public key 重算 fingerprint，並驗 trust policy mapping。
- verifier 必須重 hash 本機 target、Rule24 policy、精確兩個 measurement artifacts；digest 不符即 NO-GO。
- verifier 必須比對 caller-owned expected correlation/challenge；missing、mismatch、stale/replay input 一律 fail closed。
- 本卡只建立可信簽驗與 binding primitive，不負責 Rule24 domain metric/threshold 評估；下一張卡才組合既有 capacity evaluator。

## Public Interface

至少提供可測試的 Python API；CLI 若新增，必須顯式 `produce` / `verify` mode。輸出 machine-readable JSON：

- PASS：schema/status/mode、authenticated statement digest、accepted public-key fingerprint、target/policy/measurement digests、correlation/challenge digest、`production_mutation=false`、`canary_created=false`。
- NO-GO：stable reason code、zero-side-effect flags；不得輸出 authenticated PASS fields。

## Adversarial Tests

至少覆蓋：

1. ephemeral trusted key → produce → network-off verify PASS。
2. 相同 inputs/serialized bytes deterministic fixture behavior。
3. payload tamper、payloadType tamper、signature tamper。
4. wrong/untrusted key、key substitution、receipt keyid spoof。
5. wrong predicateType、Statement `_type`、subject target digest/type/name。
6. policy digest mismatch、measurement digest mismatch、measurement 缺/多/亂/重。
7. challenge/correlation missing 或 mismatch、replay/consumed challenge fixture。
8. trust policy producer/predicate/fingerprint/threshold mismatch。
9. verify-then-parse：application 只能使用已驗證 payload bytes。
10. OpenSSL missing/unsupported/timeout/nonzero exit fail closed。
11. relative/noncanonical paths、private key 不得寫入 repo、NO-GO zero side effects。

## Verification

- TDD：先紅測試，再最小實作。
- focused pytest 全過。
- AST/py_compile、JSON parse、`git diff --check`。
- ownership-only；`pyproject.toml`/`uv.lock` 無 diff。
- repo 內無 `.pem`、`.key`、private-key fixture。
- network/remote query=`0`；production mutation=`false`；canary=`false`。

## Delivery

- 單一 candidate commit，parent 精確等於派工時鎖定的 dispatch commit。
- RESULT 回報：OpenSSL capability receipt、正負簽驗、test count、remaining risks。
- 不整合、不 push、不 tag、不部署。

## Blocking Edges / Frontier

- Frontier：本卡現在可開工。
- 後續 `Rule24 signed evidence composition` 被本卡 candidate 驗收與整合阻擋。
- 後續 production authorization/canary 仍被完整 Rule24 evidence 與既有 P0-01 阻擋。
