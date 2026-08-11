# Writer vNext Runtime Activation Retention Manifest

狀態：`ACTIVE / FAIL-CLOSED`
更新日：2026-08-11
規則：本清單不授權任何 archive、remove、prune 或 delete；只有主線完成 integration、evidence、handoff、retained-ref 與 cleanup eligibility 聯合驗證後，才可另行交 recovery gate。

## NEVER_CLEAN

| 實體 | 身分 | 理由 |
|---|---|---|
| `<repo-root>` | 使用者主 checkout | 含使用者既有 dirty／untracked work；本 chain 不得清理、重設或覆寫。 |

## DO_NOT_CLEAN

| Worktree | 正式 task | HEAD | Retained ref | 理由 |
|---|---|---|---|---|
| `<codex-worktree-root>/9f02/Pantheon` | `019fef9d-d4ae-7842-93f1-53c0de2379c5` | `eaa384d309f2b77b1c664a373b5dd22ea86c1319` | `refs/archive/writer-vnext/20260811-ra-slice-002-candidate` | RA-SLICE-002 candidate 尚待 Repair／re-review／integration。 |
| `<codex-worktree-root>/99e6/Pantheon` | `019fefa0-7bc6-7dc0-b7c4-c21628feec7d` | `8fea208da48d1e92340d4e1e9c353f3bb2539e8d` | `refs/archive/writer-vnext/20260811-ra-slice-003-candidate` | RA-SLICE-003 candidate 尚待 Repair／re-review／integration。 |
| `<codex-worktree-root>/8ce1/Pantheon` | `019fefba-ffda-7560-9466-9c38ebf3d594` | `4b0516c95ae2f56c482170d6bc4dd2b186e6af0a` | `refs/archive/writer-vnext/20260811-ra-slices-002-003-review-evidence` | 唯一 Reviewer replacement 與兩張未關閉 findings 的 evidence。 |
| `<codex-worktree-root>/pantheon/pantheon-writer-vnext-repair-retry-1-source-2026-20260811-155100` | source card | 本卡 source commit | 建卡後補 `refs/archive/writer-vnext/20260811-repair-replacement-source` | 唯一 Repair replacement 建立與 handoff 尚未完成。 |

## RECOVERABLE_SOURCE_WORKTREE — 未授權回收

下列實體 clean 且已有 branch＋archive ref，可重建；它們不是 unique candidate。但本 manifest 不授權現在移除。

| Worktree | HEAD | Retained ref |
|---|---|---|
| `<codex-worktree-root>/pantheon/pantheon-writer-vnext-ra-slice-002-source-202608-20260811-145427` | `ad67e78efd14b1fd1f10edbeaa49640e5c05dcc7` | `refs/archive/writer-vnext/20260811-ra-slice-002-source` |
| `<codex-worktree-root>/pantheon/pantheon-writer-vnext-ra-slice-003-source-202608-20260811-145439` | `2971af65d49e842c81d99c4703d05ef21f13aa1d` | `refs/archive/writer-vnext/20260811-ra-slice-003-source` |
| `<codex-worktree-root>/pantheon/pantheon-writer-vnext-ra-slices-002-003-review-c-20260811-151816` | `264908fb2b757cfac12b91e61b1502428c456104` | `refs/archive/writer-vnext/20260811-reviewer-replacement-source` |

## 已保存但 worktree 已消失

| 原 task | 保存證據 | 狀態 |
|---|---|---|
| Reviewer `019fef5d-8235-7221-ae8b-ff6f07dab4c8` | `6b9df0e...`、`ec772e7...` 與 archive refs | 已由 `...PLAN-REVIEW-001-RETRY-1` supersede。 |
| Repair `019fef88-5c00-7f51-a98d-6d9c1629e889` | integrated candidate `b9719ad...` 與 archive ref | 待本卡 supersession 原子完成。 |

## Cleanup gate

任何一列若仍是 `DO_NOT_CLEAN`、thread 未 integrated、unique work 未驗證、evidence／handoff 未保存、或 retained ref 無法解析，固定結論為 `NO_CLEANUP_ACTION`。
