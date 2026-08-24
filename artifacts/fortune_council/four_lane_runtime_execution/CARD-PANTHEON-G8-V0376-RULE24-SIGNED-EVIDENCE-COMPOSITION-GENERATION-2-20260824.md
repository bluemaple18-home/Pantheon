---
id: CARD-PANTHEON-G8-V0376-RULE24-SIGNED-EVIDENCE-COMPOSITION-GENERATION-2-20260824
chain_id: PANTHEON-G8-RULE24-SIGNED-EVIDENCE
role: implementer
cycle: 1
status: ready
type: strict_core_bounded_implementation
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
model_reason: 固定 trust/capacity 核心契約；兩條 upstream seam 已整合並獨立 REVIEW_GO。
required_base_ref: main
required_base_sha: ac7368cdf79c7f6563743baffa268d6d16cf24f4
ownership:
  - scripts/pantheon_rule24_signed_capacity_evidence.py
  - tests/test_pantheon_rule24_signed_capacity_evidence.py
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0376-RULE24-SIGNED-EVIDENCE-COMPOSITION-GENERATION-2-20260824-RESULT.md
  - artifacts/fortune_council/four_lane_runtime_execution/g8_v0376_rule24_signed_evidence_composition_generation_2_20260824/**
forbidden_scope:
  - 修改既有 capacity evaluator、DSSE primitive、其 tests、config、registry、metadata、handoff 或未追蹤檔
  - 讀取、cherry-pick、merge、diff、套用或重建 0af881df、6de8e487、5ca75022ba、d90137815d、d1e1be51aa 的內容
  - 新增 dependency、修改 pyproject.toml/uv.lock、network、remote Git、push、tag、deploy、canary、production mutation
  - 自行實作 DSSE、PAE、crypto、capacity workload/evaluator、trust store 或 replay authority
verification:
  - .venv/bin/python -m pytest -q tests/test_pantheon_rule24_signed_capacity_evidence.py tests/test_pantheon_rule24_dsse_attestation.py tests/test_pantheon_writer_vnext_runtime_activation_capacity.py
  - .venv/bin/python -m py_compile scripts/pantheon_rule24_signed_capacity_evidence.py
  - machine-readable JSON parse、ownership-only audit、git diff --check
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/g8_v0376_rule24_signed_evidence_composition_generation_2_20260824/
result_path: artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0376-RULE24-SIGNED-EVIDENCE-COMPOSITION-GENERATION-2-20260824-RESULT.md
---

# V0376 Rule24 signed evidence composition Generation 2

## 工作名稱 → 正在做什麼 → 現在狀態

V0376 signed evidence composition → 在已驗收 main 上組合 capacity artifact bundle 與 DSSE commit-time re-authentication → READY

## Fixed baseline

- 唯一 baseline：`ac7368cdf79c7f6563743baffa268d6d16cf24f4`。
- upstream integration 已由獨立 Reviewer 回 `REVIEW_GO`；76 tests PASS、`git diff --check` PASS。
- 舊 composition commits 全部禁止；不得看內容、借 patch 或沿用 ancestry。
- CodeGraph task-semantic query 已嘗試但只回不相關索引；執行線須重試，失敗則記 `CONTEXT_DEGRADED`，只讀 baseline public APIs/tests。

## Contract

1. 新 composition layer 只能呼叫 `run_capacity_proof()` 與已整合 DSSE public APIs；不得複製 evaluator 或 crypto。
2. producer/verifier 接受 caller-owned canonical target、policy、精確兩個 capacity artifact paths/bytes、pinned public key、trust policy、challenge/correlation 與 external replay state。
3. evaluator 非 PASS、artifact 缺/多/重/換序/tamper、identity/digest drift、unknown/non-finite/bool-as-int、production boundary 非 false，一律 deterministic `NO-GO`。
4. verifier 必須從 original envelope 與 verifier-owned trust context 重新 authentication；只有 authenticated exact bytes 才能 domain evaluate、atomic claim replay、最後 release observer payload。
5. signature PASS 不得洗白 domain failure；NO-GO 不得輸出 application payload、authenticated PASS fields、accepted key fingerprint、measurement digests 或 release authority。
6. PASS receipt 必須 target/policy/two-artifact/correlation/challenge bound，並固定 `production_mutation=false`、`canary_created=false`、`authorization_granted=false`。
7. CLI 只輸出單一 machine-readable JSON；非 PASS nonzero exit；禁止 network/package manager/production entrypoint。

## Required adversarial tests

- ephemeral trusted key＋真實 evaluator PASS → offline produce/verify PASS。
- evaluator BLOCKED/raise、caller verdict spoof、cycle 0/1/3、missing/unknown/non-finite/bool-as-int。
- target、policy、artifact 1/2、順序、重複、同 path、digest 任一 tamper。
- wrong/untrusted key、keyid/payload/signature/payloadType tamper。
- challenge/correlation mismatch、stale、consumed、replay、repo-internal replay path。
- forged prior authenticated Python object 不得授權 claim 或 observer release。
- observer-before-claim、claim failure、path escape、failure side effects 必須 fail closed。

## Delivery

- TDD；先 RED 再最小 GREEN。
- 單一 candidate commit，parent 精確等於 dispatch source commit。
- RESULT 必須寫 concrete candidate source SHA 或明確 non-self-referential linkage，避免 V0375 P2 placeholder 問題。
- 只交 `DELIVERED_CANDIDATE`；不得整合、push、派 Reviewer/Repair 或開下一張卡。
- 同 blocker 第三次停止。
