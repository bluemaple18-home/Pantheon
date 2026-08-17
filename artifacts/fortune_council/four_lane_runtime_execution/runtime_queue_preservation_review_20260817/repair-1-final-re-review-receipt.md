# Queue Preservation Repair-1 Final Re-review Receipt

card_id: CARD-PANTHEON-RUNTIME-QUEUE-PRESERVATION-REVIEW-20260817
chain_id: PANTHEON-NEW-FLOW-PRODUCTION-PUBLISH-RECOVERY-20260817
formal_thread: 01a00f1f-9be9-7370-9a67-9f6aba40627a
model: gpt-5.6-sol
reasoning: high
parent_candidate_sha: c5cce3db0ae313d5dbd20192f8ffea33451c4039
repair_candidate_sha: 00ed59c52ec202c2ecb2616563cce7ce89c98852
provided_prior_receipt_sha: 267d26f9505b8977c554a4a346e4b87901158c6a5
canonical_prior_receipt_sha: 267d26f9505b8977c554a4a346e4b87901158c6a
diff: c5cce3db0ae313d5dbd20192f8ffea33451c4039..00ed59c52ec202c2ecb2616563cce7ce89c98852

## Identity And Scope

- `00ed59c52ec202c2ecb2616563cce7ce89c98852` 存在，且 `c5cce3db0ae313d5dbd20192f8ffea33451c4039` 是其 ancestor。
- 使用者提供的 prior receipt SHA 有 41 個 hex 字元，git object 不存在；本 Reviewer worktree 的有效 prior receipt commit 是 `267d26f9505b8977c554a4a346e4b87901158c6a`。
- 完整讀取 fixed diff、Repair-1 source/tests、repair receipt、原 review card 與 prior final NO-GO receipt。
- Candidate 內新增的 review card 與本 Reviewer worktree 既有卡片 bytes 相同。
- 未修改 source、tests、candidate、production runtime、production queue、launchd、network、remote、tag 或 merge state。
- 測試與 synthetic repro 只在由 `git archive 00ed59...` 建立的 `<scratch-root>/tree` 執行。

## CodeGraph

- index ready：570 files、6321 nodes、13643 edges。
- Reviewer HEAD 的 index 未包含 Repair-1 candidate symbols；`codegraph_context` 未直接命中 `_queue_snapshot_digest`，因此依規則使用 fixed commit diff 與 candidate source/test 限域讀取。

## Fixed Diff

Repair-1 將 `_queue_snapshot_digest()` 改為 deterministic canonical digest：

- root missing 與 root directory 使用不同 identity。
- root directory 以 `{"path": ".", "type": "dir"}` 綁定。
- 所有 nested directories 以 relative POSIX path 與 `type=dir` 綁定。
- 所有 regular files 以 relative POSIX path、`type=file` 與 byte SHA-256 綁定。
- entries 依 relative POSIX path 排序，再以 canonical JSON digest 綁入 plan。
- symlink 與 special residue 維持 fail closed；read race 的 `OSError` 轉為 `PromotionError`。

## Verification

Command:

```text
uv run --frozen --group dev pytest tests/test_pantheon_content_runtime_manifest.py tests/test_pantheon_content_runtime_promotion.py -q
```

Result on fixed candidate tree:

```text
75 passed in 13.85s
```

Command:

```text
git diff --check c5cce3db0ae313d5dbd20192f8ffea33451c4039..00ed59c52ec202c2ecb2616563cce7ce89c98852
```

Result: passed.

## Synthetic Reproduction

Command:

```text
uv run --frozen --group dev python <scratch-root>/repair1_repro.py
```

Results:

| Case | Detection | Transaction / receipt | Existing queue bytes | Runtime |
|---|---|---|---|---|
| external queue empty-directory drift | plan digest changed；`plan digest mismatch` | transaction 未建立 | unchanged | unchanged |
| external gsc-copy root-existence drift | plan digest changed；`plan digest mismatch` | transaction 未建立 | unchanged | unchanged |
| internal queue empty-directory drift | `queue changed during promotion` | `ROLLED_BACK` / `ROLLBACK_COMPLETE`；state before rollback=`STAGE_INSTALLED` | unchanged | rolled back |
| internal gsc-copy root-existence drift | `queue changed during promotion` | `ROLLED_BACK` / `ROLLBACK_COMPLETE`；state before rollback=`STAGE_INSTALLED` | unchanged | rolled back |

四個案例中的 drift directory 均保留，證明 rollback 只回復 runtime write set，沒有刪除、搬移或改寫 queue producer 的變更。

## Prior Finding Disposition

- [RESOLVED P1] Queue 與 gsc-copy root 的空目錄 drift 未綁入 plan/postcheck - `scripts/pantheon_content_runtime_promotion.py:319`
  - Trigger: external plan 後新增 `queue/outbox/empty-drift` 或建立原本不存在的空 `queue/gsc-copy`；以及 internal replan 後、postcheck 前注入同類 drift。
  - Evidence: external cases 在 runtime mutation 前 fail closed；internal cases 實際進入 rollback，receipt 與 runtime snapshot 均證明 rollback 完成。
  - Risk status: closed。未規劃 directory identity 不再能到達 `POSTCHECK_PASSED`。
  - Validation: committed tests `tests/test_pantheon_content_runtime_promotion.py:484` 與 line 519 加上本次 independent synthetic repro。
  - Confidence: high。

- [RESOLVED P2] 缺少 whole-queue directory identity 與 gsc-copy root drift tests。
  - Candidate 新增兩個 behavioral tests，驗證 error、receipt state、rollback state、runtime snapshot 與既有 queue bytes；不是只驗狀態文案。

## Blocking Findings

未發現未解 P0/P1。

## Residual P2/P3

- [P2] Snapshot 的 concurrent TOCTOU 視窗仍存在 - `scripts/pantheon_content_runtime_promotion.py:325`
  - Trigger: queue producer 在 `rglob`、type check 與 `read_bytes` 之間替換 path。
  - Risk: 驗證與 digest 不是同一 file descriptor；高度競態下可能得到非原子的混合 snapshot。
  - Fix: queue writer lock，或以 `lstat/openat(O_NOFOLLOW)/fstat` 對同一 descriptor 驗證與 digest。
  - Validation gap: 尚無 concurrent path replacement harness。
  - Confidence: medium。這是 prior residual risk，Repair-1 沒有擴大，也不屬本輪 P1 closure blocker。

- [P3] Full queue 與 gsc-copy snapshot 仍會重複 traversal/read；目前 82 entries 為 bounded，沒有觀察到 test slowdown blocker，但正式規模仍宜量測。

- [P3] Repair evidence 的 prior Reviewer SHA 多一個尾碼 `5` - `artifacts/fortune_council/four_lane_runtime_execution/runtime_queue_preservation_repair_20260817/repair-receipt.md:84`
  - Risk: audit consumer 直接驗證該欄位會得到 invalid object。
  - Fix: 後續 evidence metadata 使用 canonical 40-char SHA `267d26f9505b8977c554a4a346e4b87901158c6a`。
  - Confidence: high；`git cat-file` 已反證 41-char value 不存在。此 evidence typo 不影響 source behavior 或 final GO。

## Regression Axes

- failed run save-not-revive：pass；Repair-1 未新增 execute、publish 或 queue write 路徑。
- active／complete／failed exact identity、duplicate／unexpected／missing／unsupported status：pass。
- gsc-copy JSON、non-JSON bytes、symlink、special residue、path/type/digest 與 sorting：pass。
- empty preserve list 不繞過非空 runs/gsc-copy：pass。
- queue producer bytes 不變：pass；committed tests 與 independent repro 均驗證。
- directory-only drift pre-mutation fail-closed 與 post-mutation runtime rollback：pass。

## Final Verdict

FINAL_REVIEW_GO

Reason: 先前唯一阻塞 P1 已由 deterministic whole-queue directory identity digest 關閉，fixed candidate 無未解 P0/P1；P2/P3 保留為非阻塞 residual risk。
