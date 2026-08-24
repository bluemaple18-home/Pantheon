---
id: CARD-PANTHEON-G8-V0371-RULE24-SIGNED-EVIDENCE-COMPOSITION-20260824
chain_id: PANTHEON-G8-V0370-PRODUCTION-ADOPTION-RESET-READINESS-20260822
role: rule24-signed-evidence-composition-implementer
cycle: 1
status: ready
type: implementation
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
model_reason: Rule24 signed evidence composition 屬固定核心 trust／capacity 契約；authority、replay 與 fail-closed 影響高但架構 fork 已由 handoff 收斂，使用 GPT-5.5 high。
required_base_ref: main
implementation_baseline_sha: dd7de7c204a31ba779456de83acb359298842924
traces_to:
  - CONTENT-P0-01
  - RULE24-COMPOSITION-01
  - RULE24-COMPOSITION-02
  - RULE24-COMPOSITION-03
ownership:
  - scripts/pantheon_rule24_signed_capacity_evidence.py
  - tests/test_pantheon_rule24_signed_capacity_evidence.py
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0371-RULE24-SIGNED-EVIDENCE-COMPOSITION-20260824-RESULT.md
  - artifacts/fortune_council/four_lane_runtime_execution/g8_v0371_rule24_signed_evidence_composition_20260824/**
forbidden_scope:
  - 修改 scripts/pantheon_rule24_dsse_attestation.py 或 tests/test_pantheon_rule24_dsse_attestation.py
  - 修改 scripts/pantheon_writer_vnext_runtime_activation_capacity.py、tests/test_pantheon_writer_vnext_runtime_activation_capacity.py 或另造 capacity workflow
  - 安裝、下載、vendor 或新增 Python、Node、system dependency；不得修改 pyproject.toml、uv.lock 或 lockfile
  - production、launchctl、plist、runtime、queue、state、transaction、stage、barrier、adoption、reset、canary、deploy、schedule mutation
  - remote Git query、fetch、pull、push、tag、branch/ref mutation
  - 正式 key provisioning、正式 private key、正式 trust policy mutation
  - 讀取、cherry-pick、merge、套用或改寫 candidate 0af881df2a7091e5a6817bc4ba1a4de8c26671cb 或 6de8e4874d
  - 修改其他 source、tests、config、registry、metadata、既有 evidence、handoff 或使用者未追蹤檔
verification:
  - focused pytest 全過；既有 Rule24 primitive 與 capacity evaluator focused suites 無 regression
  - AST/py_compile、machine-readable JSON parse、git diff --check、ownership-only audit
  - NO-GO 不輸出 application payload、authenticated PASS fields 或 release authority
  - production_mutation=false、canary_created=false、network/remote query=0
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/g8_v0371_rule24_signed_evidence_composition_20260824/
result_path: artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0371-RULE24-SIGNED-EVIDENCE-COMPOSITION-20260824-RESULT.md
---

# Rule24 signed capacity evidence composition

## 工作名稱 → 正在做什麼 → 現在狀態

Rule24 signed evidence composition → 把既有 capacity evaluator 的 domain PASS 與已整合 DSSE/OpenSSL trust primitive 組成同一 target-bound、verifier 可重驗 receipt → `READY / IMPLEMENTATION ONLY`。

## Root Question

如何不整合舊 candidate、不新增套件、不重造 capacity workflow，把 Pantheon-owned Rule24 DSSE/OpenSSL primitive 接到既有 capacity evaluator，形成 verifier 可驗證、target-bound、fail-closed 的 signed evidence receipt？

## 已確認既有介面

- Trust primitive：`scripts/pantheon_rule24_dsse_attestation.py` 的 `ResourceInput`、`produce_rule24_attestation()`、`verify_rule24_attestation()`；固定 in-toto Statement v1、DSSE PAE、外部 pinned public key／trust policy、one-time challenge／external replay state。
- Capacity evaluator：`scripts/pantheon_writer_vnext_runtime_activation_capacity.py` 的 `run_capacity_proof()` 與 `DEFAULT_POLICY`；既有輸出含精確兩個完整 non-production cycle、before／peak／after-cleanup、host/RSS/swap、policy、1h／1d／retention projection、cleanup 與 stop-loss evidence。
- 舊 `scripts/pantheon_content_capacity_guard.py` 是 runtime preflight／monitor，不是本卡要重造或替換的 signed composition evaluator。
- CodeGraph task-semantic query 未命中上述介面，已按規則限域讀 source/tests 確認。

## RULE24-COMPOSITION-01 — 單一 domain truth

1. 新 composition layer 只能呼叫／消費既有 capacity evaluator 公開輸出；不得複製其 workload、measurement、budget、projection、cleanup 或 stop-loss engine。
2. domain verdict 只能由 evaluator output 推導。只有 evaluator `status=PASS`、精確兩個 cycle、required policy／measurement／projection／cleanup／stop-loss fields 完整且 production boundary 為 false，才可進入簽章。
3. evaluator `BLOCKED`、例外、missing／unknown／non-finite／bool-as-int、caller-supplied verdict、cycle 數不等於 2、identity/correlation drift、capacity artifact digest drift，一律 deterministic `NO-GO`。
4. composition 不得把 historical receipt status、CLI exit 0、DSSE signature PASS 或 caller boolean 單獨當 Rule24 domain PASS。

## RULE24-COMPOSITION-02 — 同 bytes target／policy／two-measurement binding

1. producer 與 verifier 都必須接受 caller-supplied canonical absolute paths：expected target、Rule24 capacity policy、精確兩個 capacity measurement artifacts；不得自行搜尋最新檔或信任 envelope 內路徑。
2. capacity evaluator 產出的 cycle 1／cycle 2 measurement bytes必須是送入 `ResourceInput` 的同一兩個檔案；固定順序、名稱與 media type，缺／多／重／換序／tamper 都 `NO-GO`。
3. expected target name、media type、digest與 policy digest 必須由 caller-owned input 重算；receipt 內自述 identity 不得擴張 authority。
4. signed statement 只透過已整合 primitive 建立／驗證；不得自行實作 DSSE、PAE、Ed25519、canonical signing 或替代 trust store。
5. verifier 必須先取得 primitive authenticated PASS，再只用其已驗證 binding 與 caller-supplied exact measurement bytes做 domain evaluation；不得 parse 未驗 envelope payload作 application decision。

## RULE24-COMPOSITION-03 — replay、zero release、ownership

1. correlation／challenge、trust policy、pinned public key、external replay state由 verifier caller擁有；composition 不得從 receipt 自行選 key、challenge 或 replay path。
2. challenge replay、stale／mismatch、signature／digest／policy／target／measurement failure、capacity domain failure都回 stable `NO-GO`；不得回 authenticated statement digest、accepted key fingerprint、measurement digests、application payload或任何 release/adoption/canary authority。
3. PASS receipt 至少含 schema/status/mode、Rule24 domain verdict、authenticated statement digest、accepted key fingerprint、target/policy/two measurement digests、correlation/challenge digest，以及 `production_mutation=false`、`canary_created=false`、`authorization_granted=false`。
4. producer／verifier API 與 CLI 都不得執行 production、capacity install、adoption/reset、canary、deploy、tag或 push。CLI 非 PASS 使用 nonzero exit並輸出單一 machine-readable JSON。
5. 若既有 public seam 不足以安全 composition，停止並交付 `BLOCKED / EXISTING_SEAM_INSUFFICIENT` 證據；不得修改 primitive／capacity evaluator或擴 scope。

## Adversarial Tests

至少覆蓋：

1. ephemeral trusted key＋既有 evaluator PASS → produce → network-off verify PASS。
2. evaluator BLOCKED／raise、caller verdict spoof、missing／unknown／non-finite／bool-as-int、cycle count 0/1/3。
3. target、policy、cycle-1、cycle-2 任一 tamper；measurement 缺／多／重／換序／同 path。
4. forged capacity PASS、projection／host reserve／cleanup／stop-loss 欄位缺失或矛盾不得被 DSSE PASS 洗白。
5. wrong／untrusted key、keyid spoof、payload/signature/payloadType tamper。
6. correlation/challenge mismatch、stale、consumed、同 challenge replay；repo-internal replay path拒絕。
7. verifier 只對 authenticated exact bytes做 domain decision；observer／application payload ordering可證明。
8. NO-GO receipt key allowlist、exit code、零 production/canary/authorization side effects。
9. 禁止呼叫 network、package manager、production entrypoint；原未追蹤檔 before/after不變。

## Verification

- 先跑新 focused RED，再最小 GREEN。
- `.venv/bin/python -m pytest -q tests/test_pantheon_rule24_signed_capacity_evidence.py tests/test_pantheon_rule24_dsse_attestation.py tests/test_pantheon_writer_vnext_runtime_activation_capacity.py`
- `.venv/bin/python -m py_compile scripts/pantheon_rule24_signed_capacity_evidence.py`
- 對產出 JSON 全部 parse；`git diff --check`；`git status --short` 與 allowlist 對帳。
- repo 內無新增 `.pem`、`.key`、private key；`pyproject.toml`／`uv.lock` 無 diff。

## Delivery

- 單一 candidate commit；parent 精確等於 dispatch source commit。
- RESULT 列 public interface、domain/trust composition順序、正負 case count、focused suite結果、allowlist、residual risks與完整 candidate SHA。
- 執行線只交 `DELIVERED_CANDIDATE`；不整合、不 push、不 tag、不部署。

## Blocking Edges

- 本卡未獨立 Review GO並整合前：不得刷新 adoption/reset readiness。
- Composition GO後另開 bounded readiness refresh 卡；本卡不得順手產 authorization envelope。
- `READY-FOR-AUTHORIZATION` 前不得請求或執行 production mutation。

## Dispatch Prompt

工作名稱：Rule24 signed capacity evidence composition
任務簡介：組合既有 capacity evaluator 與 DSSE trust primitive。
任務卡：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0371-RULE24-SIGNED-EVIDENCE-COMPOSITION-20260824.md`
執行規範：先 CodeGraph；完整讀卡；只改 ownership；TDD；fail closed；不得讀取或整合 `0af881df`／`6de8e487`。
現在狀態：`BOOTSTRAP_ONLY`；等待主線 activation token 後才可改檔、測試、commit。
