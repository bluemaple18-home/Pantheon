---
id: CARD-CONTENT-WRITER-VNEXT-RA-SLICE-006
card_id: CARD-CONTENT-WRITER-VNEXT-RA-SLICE-006
status: ready
execution_authorized: true
production_authorized: false
type: implementation
chain: PANTHEON-WRITER-VNEXT-RUNTIME-ACTIVATION
chain_id: PANTHEON-WRITER-VNEXT-RUNTIME-ACTIVATION
role: implementation
cycle: 7
strictness: strict
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: readiness package 直接位於 production authorization 前，但 capability/capacity sources 與官方 gate 已固定，屬 strict/core-bounded，使用 GPT-5.5 high，不升 Sol。
required_base_ref: main
required_base_sha: 7b3041cf4e5690ac88ded0e9895959959804d5a7
required_slice_004_review_commit: 74e2d54966ffd42a453b809245fc86252db68d0b
required_slice_005_review_commit: 965f4fdc75dec4cc92182b5ef8fd404e6cfe59e2
required_review_verdict: REVIEW_GO
slice_id: RA-SLICE-006
traces_to:
  - SC-production-canary-readiness
dependencies:
  - RA-SLICE-004
  - RA-SLICE-005
blocking_edges:
  - E2E artifacts
  - capacity PASS
ownership: 新增單一純本機 readiness packager，把已驗收七段 receipt 與兩週期 capacity proof 封裝成可攜、receipt-relative 的官方 gate 輸入；不複製官方 gate、不建立 canary。
allowlist:
  - artifacts/fortune_council/content_writer_vnext_execution/CARD-CONTENT-WRITER-VNEXT-RA-SLICE-006.md
  - scripts/pantheon_writer_vnext_runtime_activation_readiness.py
  - tests/test_pantheon_writer_vnext_runtime_activation_readiness.py
  - artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_006/**
forbidden_scope:
  - 修改 RA001–005 code/evidence、coordinator、Publisher、shared receipt validator、ai-core readiness gate/template、runner、runtime manifest、capacity guard、deployment scripts、pyproject、uv.lock 或其他 tests
  - 實作 Checkpoint B、建立 production canary、production approval 或 publication
  - 建立第二套 readiness gate、schema validator、E2E、capacity engine、Publisher、cleanup engine 或 deploy engine
  - 直接信任 caller-supplied READY/PASS/valid、Review 文案或本機絕對路徑
  - 修改 plan、registry、metadata、文章、sitemap、feed 或 redirects
  - 自行 Review、Repair、另開 task、merge、push、deploy、publication、canary、tag、network write、launchctl、服務啟停、正式產文
verification:
  - fixed RA-SLICE-004/005 REVIEW_GO lineage
  - task-semantic CodeGraph query and bounded source confirmation
  - public-behavior RED before implementation
  - portable seven-step readiness package
  - strict capability and capacity source validation
  - official production_canary_readiness_gate READY positive fixture
  - official gate BLOCKED negative fixtures
  - receipt-relative evidence existence/outcome/uniqueness audit
  - no absolute path or caller authority audit
  - RA004/RA005 regression
  - artifact JSON parse and allowlist audit
  - git diff --check
evidence_path: artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_006/
tdd: required
---

# RA-SLICE-006：Readiness Gate Packaging

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：封裝 Writer vNext Production Canary Readiness
- 正在做什麼：將七段 E2E 與兩週期 capacity proof 正規化成官方 readiness gate 可驗證的可攜 package。
- 現在狀態：`ready`；RA-SLICE-004/005 已 `REVIEW_GO` 並整合，production `NO-GO`、正式服務 `0/4`。

## Root Question

如何在不複製官方 gate、不建立 canary、不信任狀態文案的前提下，將既有七段 capability 與兩週期容量證據封裝成 receipt-relative package，使官方 `production_canary_readiness_gate.py` 對完整輸入回 `READY`、對任一缺口回 `BLOCKED`？

## 固定 Authority

1. capability schema authority：`scripts.pantheon_content_capability_receipt:validate_capability_receipt`。
2. capability source：`runtime_activation/ra_slice_004/positive-receipt.json` 與其 positive/blocked artifacts。
3. capacity source：`runtime_activation/ra_slice_005/capacity-receipt.json` 與兩份 cycle measurements/blocked proof。
4. production canary readiness authority：`<ai-core-root>/scripts/production_canary_readiness_gate.py`；專案內不得複製其判定邏輯。
5. readiness `READY` 只表示證據完整；`canary_created=false`，仍需 Checkpoint B 明確授權。
6. 官方 gate 是薄結構 gate，不驗跨 step identity、digest continuity 或 source provenance；packager 必須先以 repo canonical authority fail closed 驗證，禁止只把外觀合法欄位送 gate。

## Public Contract

新增單一公開、可測試的 bounded packager。最小 signature 由 RED tests 固定，但必須：

- caller 明示 canonical capability receipt、capability evidence root、capacity receipt、cycle measurement artifacts 與 caller-owned output package root。
- 先以 shared validator 驗 capability receipt；再自行核對每段實際 evidence file 存在、非空、outcome 正確、positive/blocked 不同且不跨 step 重用。
- 七段必須共享 execution line、correlation、actor、runtime digest；ordinal 固定 1–7；input/output digest continuity 成立；production flags 必須 false。
- capacity 必須 `status=PASS`、兩個 cycle、每個 cycle 七段 PASS、before/peak/after-cleanup measurements 齊全、reclaimed bytes/files > 0、cycle root cleanup 成功、stop-loss negative `BLOCKED`、host-free-after-projection >= reserve，且 production flags false。
- 不得把 RA005 raw `root` 或任何本機絕對路徑帶入 package；只輸出 path-free normalized capacity summary、source digest 與量測數字。
- 將每段 positive/blocked evidence 複製到 package 內唯一、receipt-relative 路徑；不得引用 package 外檔案或 symlink escape。
- 生成官方 gate 相容 `production-canary-capability-receipt.json`：steps 為 create/run/select/publish/transaction/tag/push object，inputs/outputs 對應實際 digests，identity/correlation 固定，`canary_created=false`。
- 生成 `capacity-proof-normalized.json`、`package-manifest.json`；manifest 只列 source digest、package-relative files、`production_authorized=false`，不得自填 READY。
- packager 只能輸出 package；官方 gate READY/BLOCKED 必須由外部 authority 實際執行後保存，不得由專案程式自證。

## 必做 Positive Probe

1. 從 committed RA004/RA005 artifacts 建出全新 package。
2. package 內十四份 capability evidence 全部存在、唯一、可解析、outcome 正確。
3. normalized capacity proof 無本機絕對路徑，且保留兩週期量測、回收、projection、stop-loss 結論與 source digest。
4. 官方 `<ai-core-root>/scripts/production_canary_readiness_gate.py` 對 package receipt 回 `READY`。
5. package、gate receipt、manifest 均明示 `canary_created=false`、`production_authorized=false`。

## 必做 Fail-closed Probe

官方 gate 與 packager 至少共同覆蓋：

- 缺任一 capability step、entrypoint、inputs/outputs、identity 或 correlation drift。
- positive/blocked evidence 缺檔、空檔、outcome 錯誤、同檔或跨 step 重用。
- digest continuity 斷裂、caller-supplied READY/PASS/valid、`canary_created=true`、production mutation。
- capacity 非 PASS、少於兩 cycle、缺 measurement、cleanup/reclaim 失敗、stop-loss 未 BLOCKED、host projection 低於 reserve。
- source/output symlink escape、absolute artifact path、package 外 traversal。
- 特別保存一個 adversarial RED：外觀合法但 identity drift 或 digest discontinuity 的 receipt 可能單獨通過薄 gate；repo provenance validator 必須在產生正式 package 前 BLOCKED。

每個 negative fixture 必須保存官方 gate `BLOCKED` 或 packager deterministic BLOCKED result；不得建立 canary或平行修補線。

## TDD 與 Evidence

先新增 `tests/test_pantheon_writer_vnext_runtime_activation_readiness.py` 並保存真實 RED，再做最小 GREEN。Evidence 至少：

- `red.txt`
- `green.txt`
- `package/production-canary-capability-receipt.json`
- `package/capacity-proof-normalized.json`
- `package/package-manifest.json`
- `official-gate-ready.json`
- `official-gate-blocked.json`
- `thin-gate-adversarial-red.json`
- `negative-matrix.json`
- `source-inventory.md`
- `verification-receipt.md`

至少跑：

```text
uv run pytest tests/test_pantheon_writer_vnext_runtime_activation_readiness.py
uv run pytest tests/test_pantheon_writer_vnext_runtime_activation_e2e.py tests/test_pantheon_writer_vnext_runtime_activation_capacity.py
<repo-root>/.venv/bin/python <ai-core-root>/scripts/production_canary_readiness_gate.py --receipt <repo-root>/artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_006/package/production-canary-capability-receipt.json
git diff --check
```

## Acceptance

1. package 完全由已驗收 RA004/RA005 artifacts 推導，沒有第二套 gate/E2E/capacity engine。
2. capability identity/digest/evidence 與 capacity measurements/cleanup/projection/stop-loss 全部 fail closed 驗證。
3. 官方 production canary readiness gate：完整 package `READY`，代表性負向 fixtures `BLOCKED`。
4. package 全部路徑 receipt-relative、無 symlink/traversal/本機絕對路徑；十四份 evidence 唯一存在。
5. `canary_created=false`、`production_mutation=false`、`production_authorized=false`；不宣稱 Checkpoint B 授權。
6. 受影響 regression 全綠；changed files完全落在 allowlist；`git diff --check` 通過；worktree clean；單一 candidate commit。
7. 交付只能是 `RA_SLICE_006_READY_FOR_REVIEW` 或 `BLOCKED`。

## Stop Conditions

- 必須修改 RA001–005、shared validator、ai-core official gate/template、dependency 或 production 設定才可成立。
- 無法用 receipt-relative package 保存十四份獨立 evidence，或 capacity source 缺 required proof。
- 官方 gate 對完整 package無法 READY，或代表性缺口無法 BLOCKED。
- 需要 network、credential、push、deploy、publication、tag、canary、launchctl、服務啟停或正式產文。
- 同一 blocker 第三次失敗即停止，不做第四次。
