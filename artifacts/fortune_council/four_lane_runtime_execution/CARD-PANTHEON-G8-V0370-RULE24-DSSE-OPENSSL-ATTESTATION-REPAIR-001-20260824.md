---
id: CARD-PANTHEON-G8-V0370-RULE24-DSSE-OPENSSL-ATTESTATION-REPAIR-001-20260824
chain_id: PANTHEON-G8-V0370-PRODUCTION-ADOPTION-RESET-READINESS-20260822
role: rule24-dsse-openssl-attestation-implementer-rework
status: ready
type: repair
thickness: strict
risk: critical
candidate_sha: 36edc4d323f9f1a2624158e8376cb2570b7d01fa
ownership:
  - scripts/pantheon_rule24_dsse_attestation.py
  - tests/test_pantheon_rule24_dsse_attestation.py
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0370-RULE24-DSSE-OPENSSL-ATTESTATION-20260824-RESULT.md
  - artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_rule24_dsse_openssl_attestation_20260824/**
---

# Rule24 DSSE/OpenSSL attestation repair 001

## 工作名稱 → 正在做什麼 → 現在狀態

Rule24 trust primitive repair → 修正 one-time challenge replay 與 producer keypair binding → `READY / CANDIDATE NO-GO`。

## Mainline findings

### P1 — challenge 未被原子消耗

同一 envelope 與同一 `consumed=false` challenge fixture 連續呼叫 verifier 兩次，兩次皆 `PASS`。目前只讀取 caller 預先填入的 `consumed`，沒有建立不可重用的 verifier-owned claim，因此不能證明 one-time challenge。

### P1 — private/public key 不配對仍 produce PASS

以 trusted private key 簽章、另給不相干 public key，producer 仍回 `PASS`，並把錯誤 public-key fingerprint 回報為 `accepted_public_key_fingerprint`。該 envelope 後續無法由該 public key 驗證。

## Required repair

1. verifier 新增 caller-supplied、repo-external replay-state directory。
2. 完成 signature、trust policy、target、policy、兩個 measurements、challenge 與 freshness 全部驗證後，才以 correlation/challenge digest 建立原子 one-time claim；必須使用 stdlib 的 exclusive-create 語意，禁止 read-then-write。
3. claim 已存在時回 `NO-GO / challenge_replay`；兩個同 challenge 的競爭驗證最多一個 `PASS`。
4. claim artifact 只能含 schema、challenge digest、authenticated statement digest 與必要時間資料；不得含 raw challenge、key、secret 或任意 caller payload。
5. 驗證前失敗不得建立 claim；claim directory／path 必須 canonical、caller 明確提供，不得預設寫 repo。
6. producer 簽完後必須以 caller-supplied public key 驗證相同 PAE/signature，或以 OpenSSL 導出 private key 對應 public key再比對；不配對回 `NO-GO / key_pair_mismatch`，不得回 authenticated PASS fields。
7. crypto 仍只可使用 PATH OpenSSL Ed25519；不得安裝、vendor、複製第三方 source 或手寫 crypto。

## Tests

- 第一次 verify PASS，第二次相同 challenge `challenge_replay`。
- 競爭 claim 最多一個 PASS。
- signature／policy／digest／challenge 任一前置失敗後，claim 不存在。
- private/public mismatch produce `key_pair_mismatch`。
- 原 34 tests 更新契約後維持全綠；focused pytest、py_compile、JSON、`git diff --check`、ownership/dependency/vendor/private-key audit。

## Delivery

- 以 `36edc4d323f9f1a2624158e8376cb2570b7d01fa` 為 parent，產單一 successor candidate commit。
- 更新 RESULT 與 validation receipt，明列 test runtime path。
- 不整合、不 push、不 tag、不部署、不碰 production、不查 remote。
