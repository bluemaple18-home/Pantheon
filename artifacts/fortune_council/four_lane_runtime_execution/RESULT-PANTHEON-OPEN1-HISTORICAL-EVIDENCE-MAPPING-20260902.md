---
id: RESULT-PANTHEON-OPEN1-HISTORICAL-EVIDENCE-MAPPING-20260902
card_id: CARD-PANTHEON-OPEN1-HISTORICAL-EVIDENCE-MAPPING-20260902
chain_id: PANTHEON-FOUR-LANE-RESIDENT-OPERABILITY-20260902
role: research_result
date: 2026-09-02
status: OPEN-1_PROVEN_BY_EXISTING_REAL_EVIDENCE
---

# OPEN-1 真實歷史 failure-isolation evidence mapping 結果

## 結論

`OPEN-1_PROVEN_BY_EXISTING_REAL_EVIDENCE`

production runtime 已存在一條符合四段門檻的真實鏈：失敗 item F
`auto-new-v1-20260817-060-01` 在同一 run namespace 下實際完成
transport attempt `0`、`1`、`2` 的三次 retryable failure，Coordinator 隨後把
run 寫成 terminal `failed`。同一份 Coordinator cycle log 顯示 active create
由 `2` 降為 `1`，下一 cycle 以 `active_create_before=1` 補入新 run，證明工作槽位
已釋放；不同 item N `auto-new-v1-20260817-061-01` 之後由既有 lane selector／
runner 路徑進入執行，第一筆 provider outcome 時間晚於 F 的第三次 failure。

這個結論只關閉 `OPEN-1` 的真實 Coordinator transport-failure isolation。它不把
Publisher publication retry、內容 quality repair 或 resident operability 的其他欄位
一併視為完成；`OPEN-2` 與固定四項 go-live preflight 仍維持原狀。

## 查核邊界與指紋

- repo worktree：`<repo-root>` 的隔離 research branch，查核 HEAD
  `59fe3fea21d3d10aa6190086e26645df0ba47229`。
- production runtime：`<production-runtime-root>`，實體對應本機
  `Pantheon-canary-runtime-v8`；只讀 `queue/**`、`state/**`、`logs/**`、
  `actor/handoff_20260826_pantheon_automation_acceptance_dispatch.md`。
- production metadata fingerprint 算法：所有 regular file 的
  `relative_path|size|mtime_epoch` 排序後做 SHA-256；不讀入或輸出 secret bytes。
- before：`dbf12f2a537161efd2f47c033dbae55f99318a93bd4065171e6ecdd82a2b7312`，
  regular files=`26865`。
- before 分區 file count：`queue/lanes/new=1194`、`rewrite=27`、
  `i18n-new=132`、`i18n-rewrite=105`、`state/evidence=30`、
  `state/retry=3`、`logs=14`。
- after：見「唯讀與工作樹驗證」；必須與 before 完全相同。

## CodeGraph 與 retry authority mapping

先對 indexed HEAD 實際執行 CodeGraph `context`，query 為：

```text
Map existing authoritative retry, terminal/manual state, slot release, and
next-item selector seams for OPEN-1 historical failure isolation evidence.
Identify transport retry versus item/run retry versus Publisher retry owners.
```

CodeGraph 找到 Publisher gate 入口但沒有完整串出 queue lifecycle，因此再限域讀取
下列 source seams：

1. **Transport authority**：`scripts/agy_gemini_outbox.py` 的
   `OUTBOX_MAX_TRANSPORT_RETRIES=2`，`generate_json()` 執行
   `range(OUTBOX_MAX_TRANSPORT_RETRIES + 1)`；因此正式語意是最多 `2` 次 retry、
   總共 `3` 次 transport attempt，ordinal 為 `0/1/2`。
2. **Run terminal authority**：`scripts/agy_gemini_coordinator.py` 的 `_advance()`
   捕捉 `ExternalJobFailed` 後，把 run 寫成 `status=failed`，並持久化
   `transport_attempts`。`_active_states()` 只回傳 `status=active`，所以該 run
   不再具有 lane selector eligibility。
3. **Lane selector／slot authority**：同檔 `_select_lane_states()` 每 lane 選擇
   排序後最早的 active run；`seed_new_matrix_runs()` 以
   `_active_count_by_mode(..., "create")` 判斷 active floor。terminal failed run
   被排除後，active count 降低，既有 seeder 才可補入下一 item。
4. **Publisher retry authority**：`scripts/agy_content_publisher.py` 的
   `MAX_RETRY_ATTEMPTS=3`、`_record_retry_failure()` 與
   `_retry_eligibility()` 是 publication transaction 失敗的另一位 owner；
   `DEFAULT_MAX_RUNS=3` 只是單次 Publisher invocation 上限。本次找到的真實 chain
   沒有進入 Publisher retry，因此不得把兩個 `3` 混為同一 counter。

另以 production actor Git history 唯讀核對 chain 發生前最近的 repository snapshot
`ce074a9171d4657ae5ec9615d70959ace962e11e`：該版同樣已有
`OUTBOX_MAX_TRANSPORT_RETRIES=2`、三次 attempt loop、`_advance()` 將
`ExternalJobFailed` 寫成 `status=failed`、`_active_states()` 排除非 active run、
`_select_lane_states()` 每 lane 選最早 active run，以及 seeder 依 active count
補位。此 snapshot 只用於解釋歷史 artifact，不單獨當作 runtime deployment receipt。

## 候選 chain 1：真實 F060 → N061，四段成立

### Identity

- F run：`auto-new-v1-20260817-060-01`
- F namespace／registry file stem：`49f03f7ea330822b29881d43`
- N run：`auto-new-v1-20260817-061-01`
- N namespace／registry file stem：`a8a04e2371c0a802d00bb3cf`
- 後續補入的不同 run：`auto-new-v1-20260817-062-01`
- 三者 identity 均不同。

### 1. F 實際達 transport 正式上限

三筆 archived request 都綁定 F namespace，對應的 failed provider receipt 都是
真實 production credential-pool outcome。舊 artifact 缺省的
`transport_attempt` 依 request validator／consumer 契約等同 ordinal `0`。

| Attempt | Job ID | Failure time | Outcome | Request digest | Failure digest |
|---:|---|---|---|---|---|
| 0 | `2c4c12497f9338d3f37c2f8bf46f3a3336f4936a` | `2026-08-17T15:30:05+08:00` | `GeminiApiFailure / API_HTTP_ERROR / PROVIDER_UNAVAILABLE / HTTP 503` | `89df596039aadf439e78401f9832312a0e92423079abd62d57e6fa5b71f96b63` | `a5444dc85adb4cbcf77b23f46210bcb8690e031425cf57420b4aa1af3f9d0f8b` |
| 1 | `636d00c2bc48604799ea77da5ca3bd30b2e20208` | `2026-08-17T15:39:37+08:00` | `GeminiApiFailure / API_TIMEOUT / NETWORK` | `86e0c5e9889994129b5468ad255a94603688b6cbc2088271b14e73ff7a05195f` | `7579a7d82770133f0f3af29fee1e666fe4047650913b589b922a1c8a50b61165` |
| 2 | `21abef42f52c49e0c3ba7d320697fdb8ae64f511` | `2026-08-17T15:40:40+08:00` | `GeminiApiFailure / API_HTTP_ERROR / PROVIDER_UNAVAILABLE / HTTP 503` | `8bbeecfc280c9c0e3b9eb969c79e6e92a0616e914a1f08fb7985fcf034b0c043` | `0aefa0e7be4e8efa81c6ffca88b65129607e6c26132616878c57f080bd146f79` |

路徑分別為
`<production-runtime-root>/queue/lanes/new/{archive,failed}/<job_id>.json`。

### 2. F 進入 terminal state

`<production-runtime-root>/queue/runs/49f03f7ea330822b29881d43.json`
（SHA-256
`f4205ea0f21d2d465f4229ea3e2327da214624d41ba640442a54eee66340e988`）
持久化：

```text
run_id=auto-new-v1-20260817-060-01
status=failed
error_type=GeminiApiFailure
error_code=API_HTTP_ERROR
failure_category=PROVIDER_UNAVAILABLE
transport_attempts=3
last_job_id=21abef42f52c49e0c3ba7d320697fdb8ae64f511
```

依上述 Coordinator authority，`failed` 是 run selector 的 terminal state，並非
Publisher retry record 的 `exhausted`。此處沒有把「manual-review equivalent」
文案當證據；直接使用 authoritative registry terminal value。

### 3. F 釋放 resident work slot

`<production-runtime-root>/logs/agy-gemini-coordinator.stdout.log`
（SHA-256
`4c9bf20a4f0794cffe23e0b06e8b9bf0bb7d4398934a5e7793f68f80e9601b3d`）
的原始 line `1828` 記錄該 cycle：`failed=1`、`new.active=1`、
`queued=0`、`processing=0`。下一個 line `1829` 立即記錄：
`active_create_before=1`，並由正式 new-matrix seeder 建立
`auto-new-v1-20260817-062-01`，其後 `new.active=2`。

在 F 最終 failure `15:40:40` 到補位 run 062 註冊 `15:42:51` 的 new-lane
failed receipts 中，唯一完成的 failure job 就是 F 的 attempt 2；沒有第二個 failure
identity 可解釋這次 `failed=1`／active-count 下降。

這是 durable cycle sequence 對「active create slot 從已滿變成可補入」的直接
觀察；它不把匿名 Gemini credential slot 誤認成 resident item slot。

### 4. 不同 item N 被選走並開始執行

N registry
`<production-runtime-root>/queue/runs/a8a04e2371c0a802d00bb3cf.json`
（SHA-256
`6094af1adf9262d5b7ee82bb06d2d5a3070920b42a4e1150f52434853cf6eaad`）
顯示它在 `2026-08-17T15:29:04+08:00` 註冊，最終為 `complete`。
F 第三次 failure 後，Coordinator log line `1830` 顯示同一 new lane
`processing=1`。N 的第一筆 provider execution outcome：

- request：
  `<production-runtime-root>/queue/lanes/new/archive/54904a6d86aae9147561df61d33801d57b515a4e.json`
  ，namespace=`a8a04e2371c0a802d00bb3cf`，SHA-256
  `77c040d84b1f0a0856c9368b2a6c59fcab1af2c29a5c917b90f60654fd4a9df8`；
- response：
  `<production-runtime-root>/queue/lanes/new/inbox/54904a6d86aae9147561df61d33801d57b515a4e.json`
  ，`completed_at=2026-08-17T15:44:14+08:00`，SHA-256
  `646451f95dc9af6d360df51f34fa992414e29bd1804fe3abd813c09a84d8d5c4`。

時間序為 F attempt 2 `15:40:40` → slot replenishment run 062 registered
`15:42:51` → N first provider outcome `15:44:14`。同一時間窗中新補入的 run 062
第一筆 provider outcome 到 `15:49:01` 才出現，因此 `15:44:14` 的先行執行
identity 是 N，不是新補入的 run 062。這與正式 selector 每 lane 取最早 active run
的 authority 一致，且由真實 request／response identity 證明，不是只靠讀 code
推論「應該會前進」。

### Chain 判定

四段均成立，沒有用 fixture、synthetic harness、手改 registry 或 Controller
指定 exact run 補足任一段。

## 候選 chain 2：2026-08-26 `failed: 2` 案，不作結案依據

`handoff_20260826_pantheon_automation_acceptance_dispatch.md`（SHA-256
`cc6268f1961617786e4db01daa51bedefcd4285405b2a30a60b11eb073346fe8`）
與 Coordinator log line `2848` 只證明：同 cycle summary 為 `failed=2` 時，
`new_matrix_sweep` 仍 seed
`auto-new-v1-20260826-001-01`，lane 仍有 queued／processing work。

缺口：`failed=2` 是 cycle 中失敗 run 數，不是同一 item 的第三次 attempt；該行也
沒有同鏈 terminal/manual 與 slot release identity。因此本次沒有以它補足 chain 1
的任何一段。

## 候選 chain 3：2026-08-26 隔離 Acceptance C，不作真實證據

既有結果
`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-AUTOMATION-ACCEPTANCE-C-THREE-FAILURES-ADVANCE-20260826-RESULT.md`
（SHA-256
`7c7e62228860f916371ee9f54f1ecc530bbd2be9889be677c78861840e68ccfc`）
及 machine summary（SHA-256
`3734c596d966d4ccab547423ec58197867059c2cd23298609a2ed3c277ead817`）
完整示範三次失敗後前進，但明示使用 task-owned `/private/tmp` synthetic item。

缺口：不是 production 真實觀察。依本卡證據門檻，只能解釋 seam，不能用來證明
`OPEN-1`。

## 唯讀與工作樹驗證

- production mutation：`0`。
- provider call：`NOT_RUN`。
- launchctl command／service start：`NOT_RUN`。
- Publisher／publish／Git remote write：`NOT_RUN`。
- production metadata fingerprint after：
  `dbf12f2a537161efd2f47c033dbae55f99318a93bd4065171e6ecdd82a2b7312`，
  regular files=`26865`；與 before 完全相同。
- `git diff --check`：exit `0`。
- `git status --short`：只有本卡與本 RESULT 為 untracked；卡片由 Mainline 預先
  放入，本 research task 只新增 RESULT。
