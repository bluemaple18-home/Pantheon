---
id: CARD-PANTHEON-G8-V0389-FRESH-RULE24-DSSE-SIGN-VERIFY-20260825
status: ready
execution_mode: local_task_owned_only
production_mutation: forbidden
remote_access: forbidden
---

# PANTHEON G8 V0389 fresh Rule24 DSSE sign/verify

## 工作名稱 → 正在做什麼 → 現在狀態

V0389 fresh Rule24 DSSE sign/verify → 對 V0388 accepted exact bytes做離線 Ed25519 DSSE produce、verify、replay fail-closed → ready；禁止 production與promotion。

## 依賴與目的

- 依賴 main `033f9aaa0a` 的 V0388 fresh unsigned evidence。
- 只補 V0386 phase 2：把 V0388 的 target、policy、capacity receipt、兩 cycle measurements、fresh correlation/challenge 綁成 DSSE envelope並離線驗證。
- 禁止帶入任何舊 signed composition commit、舊 envelope、舊 challenge、舊 replay state或舊 authorization。

## 執行契約

1. 先查 CodeGraph；失敗才限域 `rg`。完全依既有 DSSE/signed-capacity source與tests鎖 schema、media type、trust policy、challenge、key與CLI argv；不得猜。
2. 建唯一 canonical task root：`/private/tmp/pantheon-v0389-<correlation>`。key、target、policy、challenge、trust、replay state與暫存 envelope全在其 strict descendants。
3. 先以正式 read-only preflight證明 OpenSSL Ed25519可用；否則 `BLOCKED`。
4. 產生本卡唯一 ephemeral Ed25519 keypair。private key永不進 repo、永不輸出內容；只記 public-key fingerprint。不得取用使用者既有 keychain、SSH key或production signing key。
5. V0388 三份 source artifact只能從 main `033f9aaa0a` 的 accepted evidence讀取。複製到 task root後先以 V0388 digest manifest重驗 exact bytes；任一 mismatch即 `BLOCKED`。
6. target與Rule24 policy必須是本卡明確、bounded、task-owned exact-byte resources；producer、target name/media type、policy name、fresh correlation/challenge全部記錄。
7. 使用正式 `scripts.pantheon_rule24_dsse_attestation produce` 對兩 measurements與capacity receipt產 envelope；不得重跑capacity harness，不得改 V0388 bytes。
8. 使用 `scripts.pantheon_rule24_signed_capacity_evidence verify` 或 source證據指定的正式 domain verifier，綁 pinned public key、trust policy、target、Rule24 policy、capacity receipt、兩 measurements、fresh challenge與external replay state。
9. 正向 verify必須 `PASS`；隨即用同 envelope/challenge/replay state再驗一次，必須因 replay fail closed。任何 byte drift、domain mismatch、signature mismatch、challenge stale/mismatch、producer不受信或replay未阻擋即 `BLOCKED`。

## 唯一可寫範圍

- 本卡 task root。
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0389-FRESH-RULE24-DSSE-SIGN-VERIFY-20260825-RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/g8_v0389_fresh_rule24_dsse_sign_verify_20260825/`

## Repo evidence契約

- 可保存：DSSE envelope、public key、public-key fingerprint、trust policy、target、Rule24 policy、challenge contract、produce receipt、verify receipt、replay negative receipt、portable argv、digest manifest。
- 禁止保存：private key、secret內容、production credential、非本卡task-root路徑依賴。
- 文件命令使用 `<repo-root>`／相對路徑；task root可記 `/private/tmp/pantheon-v0389-<correlation>` lifecycle。

## 禁止範圍

- 禁止重跑/修改V0388 capacity bundle，禁止任何production actor、manifest、stage、readiness、barrier、queue、state、transaction、LaunchAgents。
- 禁止promotion plan/apply/postcheck、deploy、canary、activation、remote/network、push/tag。
- 禁止修改source/tests/workflow/shared metadata、舊evidence或派下一卡。

## 驗收

- OpenSSL Ed25519 preflight PASS。
- V0388三份 exact bytes與 `033f9aaa0a` digest完全一致。
- produce PASS；envelope綁定target、policy、兩 measurement、capacity evidence、producer、fresh correlation/challenge。
- domain verify PASS；`production_mutation=false`、`canary_created=false`。
- replay第二次 verify確定 NO-GO；negative run不得改 production。
- `<repo-root>/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pantheon_rule24_signed_capacity_evidence.py tests/test_pantheon_rule24_dsse_attestation.py` PASS（若檔名不同，以 `rg` 找到的既有受影響tests為準並記錄）。
- evidence JSON parse、SHA-256 manifest、`git diff --check` PASS；單一commit、clean、不push。

## 交付

- Verdict只能 `DELIVERED_CANDIDATE` 或 `BLOCKED`。
- 回報commit SHA、fresh correlation/challenge digest、producer、public-key fingerprint、target/policy/measurement/capacity digests、正向與replay結果、private-key lifecycle、production mutation count=0。
- 不得宣稱已有production trust、可apply或取得新authorization；後續replan另卡處理。
