---
id: CARD-PANTHEON-LEGACY-REWRITE-SEMANTIC-BOUNDARY-INTEGRATION-20260730-EVIDENCE
status: ACTIVE
type: integration-evidence
formal_thread_id: 019faf6d-7764-7e02-922c-a78361e8c143
dispatch_key: v1:0d1cce445cbbf3f24c3e8e83f41023fd8a00c5719323fb4b79e906bb98c79453
---

# Legacy rewrite semantic boundary integration evidence

## Root question

已核准的 rewrite semantic/objective boundary 是否存在於最新 main，並能在不遺失
後續內容 release、不放寬 fail-closed 邊界、且不觸發 publish 的前提下完成 production
runtime 驗收。

## Mainline snapshot

- Blocker：目前無阻斷；push 前 fresh gates 尚未執行。
- Fork：無。
- Current state：ACTIVE；已完成唯讀 lineage、remote 與 graph preflight。
- Next step：執行 fresh verification，通過後才建立 integration evidence commit。
- Waiting condition：所有 push 前 gate 必須全綠。
- Limits：不得手改 runtime 資料，不得 publish，不得建立 replacement 或 sub-agent。

## Strict fact gate

- 使用者授權範圍：核准 candidate／review evidence 整合、fresh verification、
  `HEAD:main` push、production actor 對齊、既有 LaunchAgent 重裝，以及一次
  non-publishing rewrite provider retry。
- 核心 production seam：
  `hydrate_rewrite_review()` →
  `reconcile_external_review_with_machine_gate(..., exact_codes=True)`。
- 受影響 public boundary：rewrite reviewer hydration；既有 create lane 預設
  case-normalized reconciliation 不變。
- 核心資料欄位：
  `semantic_verdict`、`semantic_findings`、`objective_observations`、
  canonical machine-owned finding code。
- Fail-closed 邊界：真正 semantic、未知、大小寫變體與 malformed finding 不得被
  machine-owned reconciliation 猜測放行。
- 禁止修改：policy 閾值、禁詞、registry、shared metadata、生成頁、sitemap、
  feed、redirects、queue、receipt、approval、ledger、文章內容與 provider 回覆。
- 回復策略：push 後若需撤回，以新的 revert commit 回復；actor 可回到同步前
  `443dc0be0040964f70f8c0fb0b1e352bdb819f77`，不得改寫 main 歷史。

## Preflight facts

- Bootstrap HEAD 與 dispatch base 均為
  `9a853081c66769234871f1821c4e5e89ac76855b`，啟動時 clean、無 `index.lock`。
- Formal thread 的 app metadata `projectId=null`，與卡片 expected project id 不同；
  activation 明確要求沿用本 formal thread 與 clean worktree，不建立 replacement。
- Physical card 在 bootstrap base 與當時 remote main 均缺失；本 integration 依收到的
  完整正式契約補回實體卡。
- 2026-07-30 preflight 時，GitHub `refs/heads/main` 與本機 `origin/main` 同為
  `37583b3f72ab012363635ddf32ce1ecc14a7817c`，比 dispatch base 多 20 個 content
  release commits；dispatch base 是最新 main 的 ancestor。
- `9a853081...37583b3f` 沒有修改
  `scripts/agy_seo_copy_pipeline.py` 或 `tests/test_agy_seo_copy_pipeline.py`。
- Candidate direct parent：
  `3ee7b2d3becb8c07f7c62726d14412964739f628`。
- Candidate：
  `6235afea4a22153cc1f436a3143557086d64d377`。
- Review evidence：
  `15e3e718d0db31cfd00a15ef14055a69e66f2fb3`，為 candidate direct child。
- 最新 main 已含 candidate 的等價 integration commit
  `a823658631e6debc225e317171ef04526e75ca30`；production/test patch-id 與 candidate
  同為 `0293540980a1138dcc7d0d944715801593fba6f2`。
- 最新 main 已含等價 review evidence commit
  `c411c0f786d35cb462161b4e8c720e85036dbd89`；implementation/review evidence
  blob 與核准 commits 完全一致。
- 因等價 commits 已在 main，禁止再次 cherry-pick 造成重複變更；本卡只新增實體
  integration card／evidence，並執行 fresh runtime 驗收。
- CodeGraph 在最新 main 重新索引 317 files、3,822 nodes、3,478 edges；語意 query
  確認中央 seam 與 unknown／malformed fail-closed tests。worktree-local `uv sync`
  因 sandbox cache 權限失敗；不影響使用既有 production actor interpreter 驗證。
- 啟動 memory recall 無命中；依規則不重試，非阻斷。

## External tool gate

- GitHub push：`write_action`；使用者已明確授權工具 `git`、目標
  `refs/heads/main`、payload `fresh-gate 後的 HEAD` 與影響「新增 integration
  card/evidence commit」。
- Push 前置：以 `git ls-remote` 確認 remote main；若 remote 漂移，重新對齊並重跑
  受影響 gate，不使用 force push。
- Production actor／LaunchAgents：local control-plane write；使用者已明確授權
  目標 actor 與 coordinator／lane／publisher，實際命令須先從 repo 既有 scripts
  解析，不猜測服務名或參數。
- Provider retry：production write，但限單次 non-publishing retry；只能由既有命令
  消化既有 receipt，不得修改 queue／receipt／approval／ledger 或 provider 回覆。

## Evidence ledger

- `git worktree list --porcelain`：目前 worktree registered、detached。
- `memory_recall.sh`：無命中，exit 1。
- `worktree_capability_preflight.sh --prepare --with-codegraph`：provisioning ready；
  CodeGraph ready；Python local env 因 sandbox cache 權限而 blocked；Node local
  environment ready。
- `codegraph_context`／`codegraph_explore`：最新 main 的中央 hydration seam、
  caller 與 hostile/malformed tests 已確認。
- `git ls-remote origin refs/heads/main`：remote main =
  `37583b3f72ab012363635ddf32ce1ecc14a7817c`。

## Fresh push-before gates

Fresh gates 最後一次執行於 pre-commit base
`72bf6163976c7c3e65641177b43e5ce17d48be62`。該 SHA 比 bootstrap base 多 21 個
content release commits，且 `9a853081...72bf6163` 沒有修改 production pipeline
或其測試。

| Gate | Result |
|---|---|
| Semantic boundary targeted set | `10 passed in 0.04s` |
| Complete SEO copy pipeline | `121 passed in 59.55s` |
| SEO publish gate、competitor SEO、coordinator、publisher、multilingual | `162 passed in 15.82s` |
| Non-duplicate suite total | `283 passed` |
| `git diff --check` | PASS |

唯一 warning 為既有
`tests/test_agy_content_publisher.py::test_preflight_test_command_selectors_resolve_to_top_level_tests`
觸發的 `DeprecationWarning: invalid escape sequence '\/'`；本卡未修改該來源。

Targeted set 明確覆蓋：

- 純 machine-owned semantic false reject 清除並轉回 `APPROVE`。
- mixed machine／semantic findings 只清除 machine-owned code。
- 真 semantic、unknown、大小寫 hostile label 與 malformed payload fail closed。
- objective observation 只接受 exact canonical code。

## Non-publishing retry target

- 既有 run：
  `legacy-auto-sweep-v1-fortune-0026-chart-bazi-05`。
- Queue state：`complete`；`approved_by_reviewer=0`；updated at
  `2026-07-30T00:21:15+08:00`。
- 既有 candidate SHA-256：
  `be0b3a952c66e74b38b3c692f47df56064d12a2b818d09f8b67cc4be77b08e1d`。
- 既有 canonical review SHA-256：
  `2cb0a0b3bd70d77c5e879cfc20a0e1c209eea0097f0ea06b7698b581fcd99bbd`。
- 既有 provider external-review receipt SHA-256：
  `7b0404cffdb5aaa62c034620e35579de5bc38d2bbb561b9df203c35008d21fc5`。
- 既有 Reviewer operation receipt SHA-256：
  `edf92d4aa6d334bcf5f694f31b30b394bb361d93f7b5426d85f9faacd37f0b1f`。
- 舊 receipt 為四欄 payload，但 `semantic_verdict=APPROVE` 同時帶正面
  `semantic_findings`，且 objective codes 不是 canonical enum，因 strict hydration
  產生 `invalid_reviewer_json:ValueError`。這正是本卡要以 fresh prompt/schema
  non-publishing retry 驗證的既有 run。
- 核准命令邊界：production actor runtime 執行
  `scripts.agy_seo_copy_pipeline review-existing <run-dir>`；它只重跑 Reviewer、
  更新 review／operation receipt，不呼叫 apply、approval 或 publisher。
