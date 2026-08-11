---
id: CARD-CONTENT-WRITER-VNEXT-RA-SLICE-005
card_id: CARD-CONTENT-WRITER-VNEXT-RA-SLICE-005
status: ready
execution_authorized: true
production_authorized: false
type: implementation
chain: PANTHEON-WRITER-VNEXT-RUNTIME-ACTIVATION
chain_id: PANTHEON-WRITER-VNEXT-RUNTIME-ACTIVATION
role: implementation
cycle: 6
strictness: strict
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 容量與 stop-loss proof 直接控制 production-readiness，但 E2E 入口、容量欄位與政策已固定，屬 strict/core-bounded，使用 GPT-5.5 high，不升 Sol。
required_base_ref: main
required_base_sha: 805483a9ed08bafa87b507a0077e5b52e2ed3501
required_slice_004_review_commit: 74e2d54966ffd42a453b809245fc86252db68d0b
required_slice_004_review_verdict: REVIEW_GO
slice_id: RA-SLICE-005
traces_to:
  - SC-capacity
dependencies:
  - RA-SLICE-004
blocking_edges:
  - synthetic E2E harness
ownership: 新增單一純本機 capacity proof harness，執行兩個完整 synthetic E2E cycle、量測資源、回收自有 temp roots，並演練 fail-closed stop-loss。
allowlist:
  - artifacts/fortune_council/content_writer_vnext_execution/CARD-CONTENT-WRITER-VNEXT-RA-SLICE-005.md
  - scripts/pantheon_writer_vnext_runtime_activation_capacity.py
  - tests/test_pantheon_writer_vnext_runtime_activation_capacity.py
  - artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_005/**
forbidden_scope:
  - 修改 RA004 E2E、coordinator、Publisher、shared receipt validator、runner、probe/adapter、runtime manifest、deployment scripts、pyproject、uv.lock 或其他 tests
  - 實作 RA-SLICE-006 readiness packaging、Checkpoint B 或 production canary
  - 建立第二套 E2E、runtime、queue、Publisher、schema validator、cleanup engine 或 readiness engine
  - 修改 plan、先前 implementation/repair/review evidence、registry、metadata、文章、sitemap、feed 或 redirects
  - 清理任務 sandbox 以外的路徑，或自行 Review、Repair、另開 task、merge、push、deploy、publication、canary、tag、network write、launchctl、服務啟停、正式產文
verification:
  - fixed RA-SLICE-004 REVIEW_GO lineage
  - task-semantic CodeGraph query and bounded source confirmation
  - public-behavior RED before implementation
  - two full synthetic non-production E2E cycles
  - before/during/after resource samples for each cycle
  - explicit temp-root cleanup and reclaimed bytes proof
  - over-budget and unknown-write fail-closed probes
  - capacity receipt schema and JSON parse
  - RA004 E2E regression
  - artifact path and allowlist audits
  - git diff --check
evidence_path: artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_005/
tdd: required
---

# RA-SLICE-005：Two-cycle Capacity and Stop-loss Proof

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：驗證 Writer vNext 兩週期容量與停損
- 正在做什麼：在 caller-owned sandbox 連跑兩次 RA004 E2E，量測容量與主機資源，回收 cycle roots，並證明超額時先阻斷。
- 現在狀態：`ready`；RA-SLICE-004 已 `REVIEW_GO` 並整合，production `NO-GO`、正式服務 `0/4`。

## Root Question

如何在不啟動 production、不清理外部資料的前提下，以兩個完整 synthetic E2E cycle 證明寫入有界、temp roots 可回收、主機保留線安全，並在 bytes、file count、host reserve 或未知寫入超標時 fail closed？

## 固定來源事實

1. 唯一 workload 是 `scripts.pantheon_writer_vnext_runtime_activation_e2e:run_runtime_activation_e2e`；不得複製七段流程。
2. 固定 production gate 仍是 `NO-GO_UNTIL_TWO_CYCLE_MEASUREMENT`，本 slice 只產生 capacity proof，不授權 canary。
3. 每一 cycle 必須使用不同、caller-owned、canonical trusted sandbox strict descendant。
4. 清理只可處理本次 harness 建立且 identity 已驗證的 cycle temp roots；evidence root 必須保留。
5. host reserve 固定為 `max(20 GiB, 10% total)`；任一 required measurement 缺漏即 BLOCKED。

## Public Contract

新增單一公開、可測試的 bounded capacity proof 入口。最小 signature 由 RED tests 固定，但必須：

- caller 明示 canonical absolute capacity sandbox root、runtime receipt、identity、brief 與 finite policy object。
- policy 至少含 `max_bytes`、`max_file_count`、`normal_growth_bytes_per_hour`、`peak_window_seconds`、`recovery_deadline_seconds`、`retention_seconds`、`sampling_interval_seconds<=300`、`max_rss_growth_bytes_per_sample`、`max_swap_growth_bytes_per_sample`；拒絕 caller verdict 與無上限值。
- 執行恰好兩個完整 RA004 E2E cycle；每個 cycle 的 execution line、correlation 與 root 唯一，七段 receipt 各自 PASS，且 production flags 維持 false。
- 每 cycle 保存 before、peak、after-cleanup sample：host free、project bytes、file count、process RSS、swap used、elapsed seconds；推導 growth/hour 與 peak transaction/temp bytes。
- 在每次 workload 前後都評估 bytes、files、host reserve、RSS/swap growth、registered paths 與 cleanup deadline；超標後不得開始下一 cycle或寫 PASS receipt。
- cycle root 清理前保存 bounded measurement/evidence；清理後驗證 root 不存在、project bytes/file count 回落並計算 reclaimed bytes。
- allowed writes 僅限本次 cycle roots 與 evidence root；發現未知路徑 deterministic BLOCKED，禁止猜測性刪除。
- PASS receipt 必須包含兩個 cycle、完整 required measurements、hour/day/retention peak projection、cleanup reclaim、stop-loss negative result、`canary_created=false`、`production_mutation=false`。
- 本機採樣可用標準庫或小型 bounded adapter；測試必須支援注入 deterministic sampler，不得新增 dependency。

## 固定預設預算

- `max_bytes`: 67,108,864
- `max_file_count`: 1,024
- `normal_growth_bytes_per_hour`: 67,108,864
- `peak_window_seconds`: 1,800
- `recovery_deadline_seconds`: 300
- `retention_seconds`: 86,400
- `sampling_interval_seconds`: 300
- `max_rss_growth_bytes_per_sample`: 268,435,456
- `max_swap_growth_bytes_per_sample`: 268,435,456

固定值是 synthetic probe 上限，不覆蓋全域 host reserve，亦不得擴張 production authority。

## 必做 Positive Probe

1. 兩個獨立 cycle 都完成七段 E2E 且 receipt PASS。
2. 每 cycle 的 before/peak/after-cleanup measurements 齊全且 finite/non-negative。
3. 兩個 cycle roots 都被清理，reclaimed bytes/file count 大於零；evidence 仍存在。
4. 推估的一小時、一天與 retention peak 後，host free 仍高於固定 reserve。
5. 最終 capacity receipt PASS，但 `canary_created=false`、`production_mutation=false`。

## 必做 Fail-closed Probe

至少保存並驗證：

- `max_bytes` 或 `max_file_count` 過低時，該 cycle BLOCKED，後續 cycle 不執行。
- host free 低於 `max(20 GiB, 10%)` 時，在 workload 前拒絕。
- RSS 或 swap 單點增長超標時拒絕。
- cycle temp root 清理後仍存在時拒絕。
- sandbox 出現未登記寫入路徑時停止且不刪除該路徑。
- 缺 required measurement、無限/負數 policy 或 caller-supplied PASS/ready/valid 時拒絕。

Blocked artifact 必須保存 stable case/reason、最後安全 sample、`next_cycle_started=false`、`external_cleanup_performed=false`。

## TDD 與 Evidence

先新增 `tests/test_pantheon_writer_vnext_runtime_activation_capacity.py` 並保存真實 RED，再做最小 GREEN。Evidence 至少：

- `red.txt`
- `green.txt`
- `capacity-receipt.json`
- `blocked-capacity.json`
- `cycle-1-measurements.json`
- `cycle-2-measurements.json`
- `negative-matrix.json`
- `source-inventory.md`
- `verification-receipt.md`

至少跑：

```text
uv run pytest tests/test_pantheon_writer_vnext_runtime_activation_capacity.py
uv run pytest tests/test_pantheon_writer_vnext_runtime_activation_e2e.py
git diff --check
```

## Acceptance

1. 恰好兩個 RA004 E2E cycle 完成；沒有第二套 E2E 或 production route。
2. required measurements、growth/peak projections、host reserve 與 cleanup reclaim 全部有實測證據。
3. 只清理本次 cycle temp roots；evidence 保留；未知路徑不刪且 fail closed。
4. over-budget、host reserve、RSS/swap、cleanup failure 與 unknown-write probes deterministic BLOCKED。
5. capacity receipt PASS 仍明示 canary/production false；不宣稱 readiness 或授權。
6. 受影響 regression 全綠；changed files完全落在 allowlist；`git diff --check` 通過；worktree clean；單一 candidate commit。
7. 交付只能是 `RA_SLICE_005_READY_FOR_REVIEW` 或 `BLOCKED`。

## Stop Conditions

- 必須修改 RA004 E2E、既有 runtime、shared validator、dependency 或 production 設定才可成立。
- 無法量測 required fields，或無法將 cleanup 限定於本次 cycle roots。
- 需要 network、credential、push、deploy、publication、tag、canary、launchctl、服務啟停或正式產文。
- 同一 blocker 第三次失敗即停止，不做第四次。
