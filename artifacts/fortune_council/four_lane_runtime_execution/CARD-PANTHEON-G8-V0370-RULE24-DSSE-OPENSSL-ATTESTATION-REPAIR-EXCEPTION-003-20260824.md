---
id: CARD-PANTHEON-G8-V0370-RULE24-DSSE-OPENSSL-ATTESTATION-REPAIR-EXCEPTION-003-20260824
chain_id: PANTHEON-G8-V0370-PRODUCTION-ADOPTION-RESET-READINESS-20260822
role: rule24-dsse-openssl-attestation-implementer-rework
status: ready
type: repair
thickness: strict
risk: critical
exception_authority: user-approved-third-repair-20260824
candidate_sha: 8f09e88f4087e2993daa84e9c9ca1c3f51b3f3f8
traces_to:
  - RULE24-TRUST-03
---

# Rule24 repair exception 003 — non-UTF-8 fail-closed

## Scope

只修 Reviewer 的 P1：`_load_json()` 遇到非 UTF-8 bytes 時不得逸出 `UnicodeDecodeError`，必須回既有 caller-specific deterministic `NO-GO` reason。

## Acceptance

- trust policy 非 UTF-8 → `NO-GO / trust_policy`。
- challenge fixture 非 UTF-8 → `NO-GO / challenge_contract`。
- envelope file 非 UTF-8 CLI → `NO-GO / envelope_contract`，exit 2，stdout 是 machine-readable JSON。
- 不得用 broad `except Exception`；只補正確 decode exception boundary。
- 原 40 tests 與新增測試全綠。

## Boundaries

- P2 空 claim 檔保留為 residual risk，本卡禁止順手修。
- 只改原 script、tests、RESULT、validation receipt。
- 不安裝／下載／vendor；不整合、不 push/tag/deploy、不碰 production/remote。
- parent 必須精確等於 `8f09e88f4087e2993daa84e9c9ca1c3f51b3f3f8`，產單一 successor candidate。

## Re-review

完成後回同一 Reviewer thread，只驗本 P1 關閉與 regression；不得新增 P2/P3 阻塞。
