# Runtime Queue Preservation 5.6 Final Review Receipt

card_id: CARD-PANTHEON-RUNTIME-QUEUE-PRESERVATION-REVIEW-20260817
chain_id: PANTHEON-NEW-FLOW-PRODUCTION-PUBLISH-RECOVERY-20260817
dispatch_key: v1:a8561b9b13d01a1400edecae2e5576850e70610ed38af6ce140661e5d9bdb21f
activation_token_received: true
formal_thread: 01a00f1f-9be9-7370-9a67-9f6aba40627a
model: gpt-5.6-sol
reasoning: high
base_sha: 8fad3fcbc3940bfde311eac02a5f6010e10f0b41
implementation_sha: b30cf964818e823611dec26b102d4984e01e9214
reviewed_candidate_sha: c5cce3db0ae313d5dbd20192f8ffea33451c4039
prior_review_receipt_sha: 23e340d0ad95f6d579c8c5b7e955b1451b63b718
diff: 8fad3fcbc3940bfde311eac02a5f6010e10f0b41..c5cce3db0ae313d5dbd20192f8ffea33451c4039

## Scope

- 獨立重讀固定 candidate diff、promotion source、targeted tests、Repair receipt 與 5.5 review receipt。
- current HEAD 相對 candidate 只多出 review evidence；candidate 的 source 與 tests bytes 未變。
- 未修改 candidate、source、tests、production runtime、production queue、launchd、network、remote、tag 或 merge state。
- synthetic repro 全部位於暫存目錄，使用測試 fixture；未讀寫 production。

## CodeGraph

- index ready：570 files、6321 nodes、13643 edges。
- `codegraph_context` 未直接命中本次新增的 queue preservation symbols；依規則改用固定 SHA 的限域 diff、candidate source 與 tests 讀取。

## Verification

Command:

```text
uv run --frozen --group dev pytest tests/test_pantheon_content_runtime_manifest.py tests/test_pantheon_content_runtime_promotion.py -q
```

Result:

```text
73 passed in 12.56s
```

Command:

```text
git diff --check 8fad3fcbc3940bfde311eac02a5f6010e10f0b41..c5cce3db0ae313d5dbd20192f8ffea33451c4039
```

Result: passed.

Candidate parity check:

```text
git diff --quiet c5cce3db0ae313d5dbd20192f8ffea33451c4039..HEAD -- scripts/pantheon_content_runtime_promotion.py tests/test_pantheon_content_runtime_promotion.py tests/test_pantheon_content_runtime_manifest.py
```

Result: passed；review worktree 的 source/tests 與固定 candidate 相同。

## Independent Reproduction

在 synthetic fixture 先產生 plan，接著才新增空目錄，再呼叫正式 `apply_promotion()`：

1. `queue/outbox/empty-drift`：queue 已有 `outbox/retry.json`，新增空目錄後 plan digest 仍相同。
2. `queue/gsc-copy` root：plan 時 root 不存在；已保存一筆 failed run，plan 後建立空 `gsc-copy` root，plan digest 仍相同。

Command:

```text
uv run --frozen --group dev python <scratch-root>/pantheon_queue_dir_drift_repro_56.py
```

Result:

```json
{
  "gsc_copy_root_drift": {
    "apply_status": "POSTCHECK_PASSED",
    "drift_directory_exists": true,
    "existing_queue_bytes_unchanged": true,
    "plan_digest_stable_after_drift": true,
    "receipt_state": "POSTCHECK_PASSED"
  },
  "queue_directory_drift": {
    "apply_status": "POSTCHECK_PASSED",
    "drift_directory_exists": true,
    "existing_queue_bytes_unchanged": true,
    "plan_digest_stable_after_drift": true,
    "receipt_state": "POSTCHECK_PASSED"
  }
}
```

## Findings

- [P1] Queue 與 gsc-copy root 的空目錄 drift 未綁入 plan/postcheck - `scripts/pantheon_content_runtime_promotion.py:145`
  - Category: correctness / production recovery safety。
  - Trigger: plan 後新增任意 queue 空目錄，或把不存在的 `gsc-copy` 建成空 root，再執行 apply。
  - Evidence: 兩個獨立案例的 replan digest 均與原 plan 相同，apply 與 receipt 均為 `POSTCHECK_PASSED`，drift 目錄仍存在。
  - Root cause: `tree_digest()` 在 line 151 只列入 files；`_queue_snapshot_digest()` 在 line 319 直接沿用該 digest。`_queue_identity_snapshot()` 不記錄完整 queue directory set；`_gsc_copy_identity_snapshot()` 在 line 244 只記錄 root 之下的 entries，因此 root absent 與 empty root 都序列化為空 list。
  - Risk: transaction 可在未規劃的 queue filesystem identity 上完成 actor／manifest／stage promotion，違反任何 plan-to-apply queue/gsc-copy drift 都必須 fail closed 的契約。既有 queue bytes 雖未被改寫，runtime 也沒有 rollback，因為 drift 完全沒有被偵測。
  - Fix: 以單一 deterministic whole-queue snapshot 記錄每個相對 path 的 `type`，包含 `gsc-copy`、`outbox` 等 directory entries，並為 regular files 記錄 digest；plan、apply replan 與 postcheck 比較同一份 canonical snapshot。保留 symlink／special-file fail-closed。
  - Validation gap: 新增兩組回歸測試。外部 plan 與 apply 間的空目錄 drift 應在 runtime mutation 前拒絕；internal replan 後、postcheck 前的同類 drift 應觸發 `ROLLBACK_COMPLETE`，receipt 為 `ROLLED_BACK`，且既有 queue bytes 不變。
  - Confidence: high；固定 candidate 上可重現。

## Residual P2/P3

- [P2] 現有 tests 只證明 gsc-copy file drift；未覆蓋 whole-queue directory identity、`gsc-copy` root absent/empty identity，以及相應的 pre-mutation rejection／runtime rollback。
- [P2] Snapshot 仍有 TOCTOU 視窗：`_gsc_copy_identity_snapshot()` 依序做 symlink/type check、JSON parse、再次 `read_bytes()`；full queue symlink scan 與 `tree_digest()` 也是兩次 traversal。併發替換 path 時，驗證與實際 digest 並非同一 file descriptor。建議使用 queue writer lock，或以 `lstat/openat(O_NOFOLLOW)/fstat` 對同一 descriptor 驗證與 digest，並補 concurrent replacement 測試。Confidence: medium。
- [P3] 一次 plan/apply 會重複全量掃描與讀取 gsc-copy／queue files；目前 82 entries 尚屬 bounded，但缺少規模上限或掃描成本量測。修正 directory identity 時可合併 traversal，避免額外 I/O。

## Axes Result

- failed run 僅作 identity preservation：pass；promotion code 沒有 execute／publish／queue write 路徑。
- duplicate／unexpected／missing run identity 與不允許 status：pass，均 fail closed。
- gsc-copy nested entry path/type/file digest、invalid JSON、symlink、special residue、sorting：pass。
- arbitrary non-JSON file bytes：pass；以原始 bytes digest 綁定。
- path traversal：run ID 不允許 slash，gsc-copy traversal 侷限於 root 且 symlink 在穩定 filesystem 狀態下 fail closed；TOCTOU 列 P2。
- empty preserve list 對非空 `runs`／`gsc-copy`：pass；空 root 的 identity drift 仍落入 P1。
- plan-to-apply directory drift rollback：fail。
- tests 實證：正負向主路徑通過，但缺 P1 directory identity regression。

## Final Verdict

FINAL_REVIEW_NO_GO

Reason: 固定 candidate 仍有一項未解 P1；queue 空目錄與 `gsc-copy` root identity drift 可在 plan 後通過 apply/postcheck，runtime 不會 rollback。
