---
id: CARD-CONTENT-WRITER-VNEXT-RA-SLICE-001-REPAIR-001-RETRY-1
card_id: CARD-CONTENT-WRITER-VNEXT-RA-SLICE-001-REPAIR-001-RETRY-1
status: ready
execution_authorized: true
production_authorized: false
type: repair
chain: PANTHEON-WRITER-VNEXT-RUNTIME-ACTIVATION
chain_id: PANTHEON-WRITER-VNEXT-RUNTIME-ACTIVATION
role: repair
role_slot: repair
cycle: 2
strictness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定候選與固定 findings 的核心 runtime receipt Repair，規格已封閉，使用 GPT-5.5 high。
replacement_of_thread_id: 019fef88-5c00-7f51-a98d-6d9c1629e889
replacement_reason: AUTO_ARCHIVE_REMOVED_WORKTREE
unsaved_unique_work: false
preserved_repair_candidate: b9719ad5d6b409d91b8f188d8bdfab28f8d9e08a
target_slice: RA-SLICE-002
candidate_base_sha: eaa384d309f2b77b1c664a373b5dd22ea86c1319
review_evidence_sha: 0895268067c97ca3e1eec1d99f54083df1ecf160
allowlist:
  - scripts/agy_gemini_coordinator.py
  - tests/test_agy_gemini_coordinator_capability_receipt.py
  - tests/test_agy_gemini_coordinator.py
  - artifacts/fortune_council/content_writer_vnext_execution/CARD-CONTENT-WRITER-VNEXT-RA-SLICE-001-REPAIR-001-RETRY-1.md
  - artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_002_repair/**
  - artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/repair_replacement/**
  - artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/retention/**
forbidden_scope:
  - 修改 implementation/review evidence、Publisher、其他 slice 或共享整合檔
  - 自行 Review、另開 task、建立 replacement、merge、push、deploy、production、canary、publication、tag、network write或服務啟停
evidence_path: artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_002_repair/
supersession_receipt_path: artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/repair_replacement/supersession-receipt.json
retention_manifest_path: artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/retention/DO_NOT_CLEAN.md
---

# Writer vNext 唯一 Repair Replacement：RA-SLICE-002

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：修復 Coordinator Create/Run Receipt
- 正在做什麼：針對固定 review findings 做 public-behavior TDD 與最小 Repair。
- 現在狀態：`READY_FOR_REPAIR`；production `NO-GO`、正式服務 `0/4`。

## Supersession handoff

- 原正式 Repair task：`019fef88-5c00-7f51-a98d-6d9c1629e889`
- 原 worktree `<codex-worktree-root>/db89/Pantheon` 已因平台自動封存消失。
- 原 Repair candidate `b9719ad5d6b409d91b8f188d8bdfab28f8d9e08a` 已整合並由 archive ref 保存；原 task 在結束時 clean，沒有未保存 unique work。
- 使用者已明確授權建立唯一 Repair replacement；本卡只替換執行容器，不重置 Repair generation 或既有 chain ledger。
- 本 replacement 完成 RA-SLICE-002 後停止。RA-SLICE-003 若需 Repair，必須回同一正式 task 接續，不得建立第二個 Repair。

## 固定 lineage

- Candidate base：`eaa384d309f2b77b1c664a373b5dd22ea86c1319`
- Review evidence：`0895268067c97ca3e1eec1d99f54083df1ecf160`
- Repair parent 必須是包含本卡的 source HEAD；candidate code 相對 `eaa384d...` 僅能有本卡 allowlist 內的最小變更。

## 必修 findings

1. `P1 / scripts/agy_gemini_coordinator.py:596`：positive preflight 不得直接合成 `blocked-create.json`／`blocked-run.json`。Blocked evidence 必須由實際 rejected calls 產生。
2. `P1 / scripts/agy_gemini_coordinator.py:575`：canonical create/run output digests 不得包含 absolute sandbox path；相同語意輸入跨兩個 canonical roots 必須穩定。
3. `P1 / scripts/agy_gemini_coordinator.py:636`：不得用 broad `except Exception` 把非預期 `RuntimeError` 改寫為 `CoordinatorReceiptBlocked`；只轉譯已知 boundary rejection。
4. `P2 / scripts/agy_gemini_coordinator.py:50`：receipt evidence identifiers 必須由 caller-authorized `evidence_root` 與實際 artifacts 推導，不得硬編固定 RA-SLICE-002 repo path。

## TDD 與驗證

1. 先新增四組 public regressions：真實 blocked probe、cross-sandbox digest、unexpected exception propagation、caller evidence-root binding。
2. 修 code 前跑新 regressions，保存真實 RED；若任一新測試未 RED，停止並說明測試未命中契約。
3. 只做最小修復，不重寫 coordinator 狀態機，不複製 `register_run`／`cycle_once` seam。
4. GREEN 必須包含：

```text
uv run --frozen pytest tests/test_agy_gemini_coordinator_capability_receipt.py tests/test_agy_gemini_coordinator.py tests/test_pantheon_content_capability_receipt.py tests/test_pantheon_content_capability_probe.py
git diff --check
```

5. 另跑兩個不同 absolute canonical sandbox roots、injected `RuntimeError`、actual blocked calls、caller evidence-root resolve 與 JSON/allowlist audit。
6. 只建立單一 Repair candidate commit，最後 worktree clean。

## 交付

只可回：

- `RA_SLICE_002_REPAIR_READY_FOR_REVIEW`：附 candidate SHA、parent SHA、changed files、RED/GREEN、四項 finding 對應 regression、retention manifest 未變更聲明。
- `BLOCKED`：附可重現 blocker；不得擴 scope 或自行 Review。

