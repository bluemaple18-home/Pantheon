---
id: CARD-PANTHEON-G8-V0389-FRESH-RULE24-DSSE-SIGN-VERIFY-20260825-RESULT
verdict: DELIVERED_CANDIDATE
execution_mode: local_task_owned_only
production_mutation: false
canary_created: false
authorization_granted: false
---

# V0389 fresh Rule24 DSSE sign/verify result

## 結論

`DELIVERED_CANDIDATE`。V0388 accepted bundle 的三份 artifact 已直接從 `033f9aaa0a` Git object 取出，並逐一通過 SHA-256 與 byte length exact-byte 核對。正式 DSSE producer 以本卡唯一 ephemeral Ed25519 keypair 產出 envelope；正式 signed-capacity domain verifier 首次回傳 `PASS`，以同 envelope、challenge 與 external replay state 第二次驗證則以 `challenge_replay`、exit code `2` fail closed。

此結果只證明 local task-owned 離線候選 evidence；不代表 production trust、可 apply、可 promotion 或取得 authorization。

## 綁定與身分

- Baseline：`ada64586f5`；V0388 accepted evidence：`033f9aaa0a`。
- Canonical task root：`/private/tmp/pantheon-v0389-v0389-20260825T120000Z-dd8ce8ee32a7a2e2`；所有 key、target、policy、challenge、trust、replay state 與暫存 envelope 都是 strict descendants。
- Correlation：`v0389-20260825T120000Z-dd8ce8ee32a7a2e2`。
- Challenge：本卡唯一 256-bit random value；correlation/challenge digest：`fae16415a19301cc736805384aa93c6224b1bb7da3b3373c55cb0a4b63cea253`。
- Producer：`rule24-producer:v0389-fresh-local-task-owned`。
- Public-key fingerprint：`81eb5277de94a620b303b26a5d35e4afce30794ea9d3bb2bdd2dd69a1b1506bb`。
- Target name：`pantheon-v0389-fresh-rule24-capacity-attestation`；media type：`application/vnd.pantheon.rule24.fresh-capacity-attestation-target+json`。

## Exact-byte digests

| Resource | SHA-256 |
|---|---|
| target | `950040a5e5fd55f84f4756d272803aa1ae684bc6e7c9bd0e2db944861493d5b1` |
| Rule24 policy | `343649dcd526162dccda22db12e30881e33d32e2477aac5a48ae548b9fa19bf8` |
| capacity receipt | `776ae80fd611bb85b3693a1629176dc9d137c81b51d16fda62e6c3d200391ad4` |
| cycle 1 measurement | `669c6fc5b23d0ce88462a6bdd558c915d182788c91e853c6e38ee9a41bcc15e3` |
| cycle 2 measurement | `b1ab2cfe0d928a1d8de975c4912752117bea51fe5ae1507ce723fe874fd1441e` |
| authenticated statement | `406b18797851b90e31bef4f9e59e58890dce34842d34b986ad2631b437925fc9` |

## 驗證證據

- CodeGraph 在目前 worktree 未初始化；source decision 依契約改用限域 `rg`，鎖定 `scripts.pantheon_rule24_dsse_attestation` producer 與 `scripts.pantheon_rule24_signed_capacity_evidence` domain verifier。
- OpenSSL preflight：`PASS`，Ed25519 capability `true`；正式 read-only receipt 已保存。
- V0388 exact bytes：三份均 `MATCH`，沒有重跑 capacity harness，沒有修改 V0388 bytes。
- Produce：`PASS`；`production_mutation=false`、`canary_created=false`。
- Domain verify：`PASS`；`authorization_granted=false`、`production_mutation=false`、`canary_created=false`。
- Replay negative：第二次 verify 回傳 `NO-GO`／`challenge_replay`，exit code `2`。
- 受影響測試：`<repo-root>/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pantheon_rule24_signed_capacity_evidence.py tests/test_pantheon_rule24_dsse_attestation.py` → `77 passed in 8.07s`。
- Repo evidence JSON parse、SHA-256 manifest、secret scan 與 `git diff --check` 均由同目錄 receipt／manifest 與最終 gate 證明。

## Private-key lifecycle 與邊界

- 本卡只生成一組 ephemeral Ed25519 keypair；未讀取既有 keychain、SSH key 或 production signing key。
- Private key 只曾位於 task root 的 `keys/ephemeral.private.pem`，完成 produce、positive verify 與 replay negative 後已銷毀；repo 只保留 public key 與 fingerprint。
- Production mutation count：`0`；canary created count：`0`；remote access、deploy、promotion、push、tag 均未執行。

## Evidence index

- `artifacts/fortune_council/four_lane_runtime_execution/g8_v0389_fresh_rule24_dsse_sign_verify_20260825/`
- `preflight-receipt.json`、`source-exact-byte-receipt.json`、`produce-receipt.json`、`verify-receipt.json`、`replay-negative-receipt.json`
- `envelope.json`、`ephemeral.public.pem`、`trust-policy.json`、`target.json`、`rule24-policy.json`、`challenge.json`
- `portable-argv.json`、`key-lifecycle.json`、`test-receipt.json`、`validation-receipt.json`、`digest-manifest.json`
