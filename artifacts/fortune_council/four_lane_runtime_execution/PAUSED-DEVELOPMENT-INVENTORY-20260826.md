# Pantheon 暫停開發封存清單（2026-08-26）

## 現階段唯一活躍目標

發文流程穩定：依 `handoff_20260826_pantheon_automation_acceptance_dispatch.md`，只驗收舊文原網址、翻譯公開網址、單篇失敗三次後前進。

## 保留中的主線

- `main`：`6477ab815e8aecca7d1e8e1588e6e5eba0fab001`
- 七個自動服務維持停止；本次整理不變更 production runtime、queue、ledger、plist 或網站。
- 後續三張驗收卡應從當時最新 `main` 建立新的獨立 clean worktree；不得復用下列暫停現場。

## 已建立封存保留點

下列 detached HEAD 含尚未成為 `main` ancestor 的 commit。已建立本機 `archive/...` branch 後才移除 worktree，因此成果仍可由 branch 恢復。

| 封存 branch | 保留 SHA | 原工作內容 | 狀態 |
|---|---|---|---|
| `archive/pantheon-paused-capacity-guard-repair-20260826` | `1d2e6bc48bfa39b77156dcff106f299a2fe490e1` | capacity guard normal activation policy | 暫停，不納入目前發文驗收 |
| `archive/pantheon-paused-publisher-reset-parser-20260826` | `6b93ea6484d6a3b0baf13a0efbb0fced0bc81719` | publisher reset launchctl identity parser | 暫停，不納入目前發文驗收 |
| `archive/pantheon-paused-v0391-terminal-continuation-20260826` | `f31e12fbd8650c95820012019c9d59ce16c38783` | V0391 terminal continuation evidence | 暫停；新文 canary 已另有成功證據 |

## 已移除的乾淨 worktree

- `/private/tmp/pantheon-normal-activation-capacity-guard-repair`
- local-only Codex worktree `216b/Pantheon`
- local-only Codex worktree `32ca/Pantheon`
- local-only Codex worktree `9faa/Pantheon`
- local-only Codex worktree `ce282b02-d544-44a3-acc7-0dccffb13a51/Pantheon`

其中 `216b` 與 `ce282b02...` 的 HEAD 已是 `main` ancestor；其餘三個由上節 archive branch 保留。移除前五者皆為 clean worktree。

## 保留現場、未移除的 worktree

以下 worktree 含未提交內容。為避免遺失或錯收使用者/舊 thread 的成果，本次只記錄，不 commit、不 stash、不 force remove。

| local-only worktree | HEAD | 未提交內容 | 處置 |
|---|---|---|---|
| `/private/tmp/pantheon-normal-policy-red` | `00c46a8aba7ffbb39a9eef901b407bf4fe23ded9` | `tests/test_pantheon_content_capacity_guard.py` | 暫停保留 |
| `/private/tmp/pantheon-v0393-missing-brief-repair` | `00c46a8aba7ffbb39a9eef901b407bf4fe23ded9` | `scripts/agy_gemini_coordinator.py`、`tests/test_agy_gemini_coordinator.py` | 暫停保留 |
| Codex worktree `4eda/Pantheon` | `de13ef0de5d122cbe66831ede20b4a62cc6e37a1` | 6 個 `.ai/` 未追蹤 task/evidence 檔 | 暫停保留 |
| Codex worktree `8899eaac-97c5-4bf6-83bb-7a378ad1b6db/Pantheon` | `9e619b588da5286d1f6104d8c663075e4fee9290` | V0391 RESULT 未追蹤檔 | 暫停保留 |
| Codex worktree `d296da6f-e38f-407e-bc3b-06c6bc652bc0/Pantheon` | `d0e2bba7d1c34096c9ca643a591465c128bf7c5b` | coordinator source/test 修改 | 暫停保留 |

## 其他既有 branches

- 既有 `codex/*`、`review/*`、`integration/*`、`handoff/*` 與舊 `archive/*` branch 全部視為 frozen historical refs。
- 本次不刪、不 rename、不 push，避免破壞既有 thread、review lineage 或未來恢復入口。
- 它們不屬於目前「發文流程穩定」活躍範圍；若未來要重啟，先另開明確目標並從本清單或原卡片恢復，不得順手混入三張驗收卡。

## 恢復規則

1. 使用者明確指定要恢復的功能或 branch。
2. 先以新 worktree 唯讀核對 branch SHA、與當時 `main` 的差異及是否已 patch-equivalent。
3. 有未提交現場者先回原 worktree 判斷 ownership，不得從本清單推定可直接丟棄。
4. 恢復工作必須另立範圍，不得改變目前三張發文驗收卡的完成條件。
