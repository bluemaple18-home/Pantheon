# 四線 activation active-queue preflight reconciliation

## Verdict

`NO_GO_FRESH_CANARY / GO_BOUNDED_OPERATIONAL_RECONCILIATION`

本卡全程唯讀 production root，未執行 queue／registry／runtime／LaunchAgent／provider／publisher mutation。Phase0 的唯一 blocker 需要重新分層：

- 三筆 active registry 是同一個已發布 rewrite 的三語系 fan-out，均為 **正式 pending、尚未 materialize 第一個 Writer job**；不是完成後 registry dangling，也不是可直接 terminalize 的 stale-success。
- 五個「nonempty active queue dirs」實際全部是 `inbox` response receipt surface。它們有同名 `archive` request，且目前五個 namespace 的 `outbox=0`、`processing=0`；它們不是 runner 正在消費的 active work。若 fresh canary 契約要求 inbox byte-level 為零，它們只能稱為「pre-canary retained terminal residue」，不能稱為 pending job。
- 因三筆正式 pending 尚未閉合，fresh exactly-one canary 仍是 `NO-GO`。不需要先 push；remote/source 推送不會改變 production queue lifecycle。

## Evidence boundary

必讀輸入：

- worktree 0406 的 `pantheon_four_lane_activation_acceptance_20260830/RESULT.md`
- 同目錄 `phase0-corrected-no-go-receipt.json`
- production root：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8`

唯讀重查確認：

- 三筆 registry 仍為 `status=active`；`generation=null`、`last_job_id=null`、`correlation_id=null`。
- 三個 run dir 均存在，且各只有 `brief.json`。
- 五個 queue namespace 的 `outbox=0`、`processing=0`。
- Phase0 七個正式 service labels 全部 `loaded=false`（return code 113）；本次再查五個 Gemini labels 仍全部找不到 service。受 sandbox 限制，process-list API 不可讀；因此「沒有 standalone 手動 process」不可由本卡證明，但沒有 LaunchAgent consumer，且沒有 claim 中的 `processing` job。

## 三筆 active registry immutable classification

三筆共同 identity：

- lane／mode：`i18n-rewrite`／`translate_existing`
- source：`ASTRO-BASE-03`，`/articles/astrology/astrology-0003`
- identity digest：`46ea60e7df3a0e68b65b25f318da453edb19cade9038f33e6ee2a31745bd501d`
- parent lifecycle：`legacy-auto-sweep-v1-astrology-0003-astro-base-03`
- parent release：version `0.3.368`、commit `45942c29710fc58916addb8862f92c90444b29e8`、published `2026-08-18T11:04:26+08:00`
- ledger：`translation_seed_status=seeded`、seeded `2026-08-18T11:04:27+08:00`；沒有三筆 run 的 `translation_published_runs` 或 `translation_deferred_runs`。

| registry | lane / locale | run | generation | status / last job / correlation | receipts | last mutation evidence | classification |
|---|---|---|---|---|---|---|---|
| `f2324fee6f9d81fe4febbc6e` | `i18n-rewrite` / `en` | `auto-i18n-en-aa637e1bf05d3ad21429` | `null`（legacy flat、尚無 generation dir） | `active` / `null` / `null` | 僅 `brief.json`；candidate、review、publish、terminal receipt 全無 | state `updated_at=2026-08-25T20:33:30+08:00`；registry mtime `2026-08-26T09:56:24+08:00`；brief mtime `2026-08-26T10:14:16+08:00` | `FORMAL_PENDING_PRE_WRITER` |
| `f4bf7419d5d88a55b7c068d0` | `i18n-rewrite` / `ko` | `auto-i18n-ko-bc1ce017b4ac2657a133` | `null`（legacy flat、尚無 generation dir） | `active` / `null` / `null` | 僅 `brief.json`；candidate、review、publish、terminal receipt 全無 | 同上 | `FORMAL_PENDING_PRE_WRITER` |
| `f9c50cb36f9e286a664fc9da` | `i18n-rewrite` / `ja` | `auto-i18n-ja-278fce6e38a85de996dd` | `null`（legacy flat、尚無 generation dir） | `active` / `null` / `null` | 僅 `brief.json`；candidate、review、publish、terminal receipt 全無 | 同上 | `FORMAL_PENDING_PRE_WRITER` |

Brief raw SHA256（更正）：EN `bcd31d23f5d8455ea21fea205827afd267a29f4c4533b0064a80154fbd8d12f3`；KO `ab856f9dc76c1d866714306061edee8c3c9933668d64ee6f4db179126cee923b`；JA `5e4ff036b0205b7b82d2176db50cd3667240680600559cc9c8ef3631f97557fd`。

### 2026-08-30 digest 對帳更正

原版列出的三個 digest 不是 raw SHA256，也不是 canonical JSON SHA256，而是沒有計算 receipt 支持的抄錄錯誤。原版撰寫時沒有保存能產生那三個錯值的 shell command 或 machine receipt；錯值只出現在本 RESULT，以及下游把本 RESULT 當 expected input 的 snapshot／blocker。它們各自只碰巧保留正確 digest 的前八個 hex，之後內容不等於任何本次重算結果。

本次唯讀重算命令：

```sh
shasum -a 256 <brief.json>
jq -cS . <brief.json> | shasum -a 256
stat -f 'inode=%i size=%z mtime_epoch=%m mtime=%Sm birth_epoch=%B birth=%SB' \
  -t '%Y-%m-%dT%H:%M:%S%z' <brief.json>
```

三個檔案本身已是 compact、key-sorted JSON，並帶單一尾端 newline，因此 raw SHA256 與上述 `jq -cS` canonical JSON SHA256 相同：

| locale | raw SHA256 | canonical JSON SHA256 | inode | size | mtime | birthtime |
|---|---|---|---:|---:|---|---|
| EN | `bcd31d23f5d8455ea21fea205827afd267a29f4c4533b0064a80154fbd8d12f3` | `bcd31d23f5d8455ea21fea205827afd267a29f4c4533b0064a80154fbd8d12f3` | `143752133` | `6650` | `2026-08-26T10:14:16+08:00`（snapshot 精度：`.681320`） | `2026-08-26T10:14:16+08:00` |
| KO | `ab856f9dc76c1d866714306061edee8c3c9933668d64ee6f4db179126cee923b` | `ab856f9dc76c1d866714306061edee8c3c9933668d64ee6f4db179126cee923b` | `143752134` | `6650` | `2026-08-26T10:14:16+08:00`（snapshot 精度：`.682005`） | `2026-08-26T10:14:16+08:00` |
| JA | `5e4ff036b0205b7b82d2176db50cd3667240680600559cc9c8ef3631f97557fd` | `5e4ff036b0205b7b82d2176db50cd3667240680600559cc9c8ef3631f97557fd` | `143752135` | `6650` | `2026-08-26T10:14:16+08:00`（snapshot 精度：`.682522`） | `2026-08-26T10:14:16+08:00` |

交叉 receipt：

- `pantheon_four_lane_current_acceptance_matrix_20260829/machine-receipt.json` 在本 RESULT 建立前已記錄 EN raw SHA256 為 `bcd31d23f5d8455ea21fea205827afd267a29f4c4533b0064a80154fbd8d12f3`。
- worktree 0406 的 `before-en-exact-coordinator-snapshot.json` 與 `bounded-operational-reconciliation-blocker.json` 所量到的三個 actual SHA、size、mtime，均與本次重算相同。
- 三檔 mtime／birthtime 均為 2026-08-26，早於本 RESULT 的 2026-08-30 classification；blocker 也明列 `production_mutation_executed=false`、`coordinator_executed=false`。

因此 filesystem／receipt 支持的裁決是 `REPORT_DIGEST_ERROR / NO_BRIEF_BYTE_MUTATION_EVIDENCED`。下游 `BRIEF_DIGEST_DRIFT_BEFORE_EN_EXACT_COORDINATOR` 是由本 RESULT 的錯誤 expected digest 造成，不是 production brief bytes 漂移。三筆 `FORMAL_PENDING_PRE_WRITER` classification、唯一 operational frontier 與 stop conditions 均不變。

### 為何不是另外兩類

- 不是 `COMPLETED_REGISTRY_DANGLING`：三個 canonical run dir 都存在；正式 `terminalize-dangling-active` 明確只接受 missing canonical run dir。
- 不是 `STALE_SUCCEEDED_WRITER`：沒有 Writer job、archive、inbox、production attempt、candidate 或 review，無法滿足該 seam 的 exact digests。
- 不是 `STALE_RESIDUE`：ledger 清楚記錄 parent rewrite 對三個 locale 的 seed；三筆共享 parent、article 與 identity digest，是單一 durable fan-out lifecycle。

## 五個 queue surface classification

| namespace | observed surface | files | matching archive | active transport | latest mutation mtime | classification / owner |
|---|---:|---:|---:|---|---|---|
| global | `inbox` | 6 | 6/6 | `outbox=0`, `processing=0` | `2026-08-26T10:16:14+08:00` | `TERMINAL_RESPONSE_RECEIPT_SURFACE`; runner owns transport |
| `new` | `inbox` | 93 | 93/93 | `outbox=0`, `processing=0` | `2026-08-26T10:46:45+08:00` | 同上 |
| `rewrite` | `inbox` | 8 | 8/8 | `outbox=0`, `processing=0` | `2026-08-16T20:53:56+08:00` | 同上 |
| `i18n-new` | `inbox` | 21 | 21/21 | `outbox=0`, `processing=0` | `2026-08-28T22:39:32+08:00` | 同上 |
| `i18n-rewrite` | `inbox` | 17 | 17/17 | `outbox=0`, `processing=0` | `2026-08-26T10:45:17+08:00` | 同上 |

補充不變量：

- 145 個 inbox receipt 全部沒有同名 outbox／processing／failed conflict。
- production attempt 對應為 global 5/6，其餘四 lane 均全數對應。global 缺一筆 attempt 不會把該 receipt 變成 runner pending work，但也禁止由 sanitized receipt 推論其 semantic consumption。
- inbox payload 是 sanitized completion envelope（`completed_at/job_id/model/request_sha256/result` 等）；本身沒有 lane/run/generation/correlation。因此五個 surface 不可反向綁定到上述三筆 run，也不能單靠 inbox 宣稱 candidate/review/publish 完成。
- `agy_gemini_runner` 的 durable transition 是 outbox → processing，provider 結果寫 inbox，request 移 archive；`agy_gemini_outbox.consume_external_response` 讀 inbox 但不刪 receipt。故 inbox 非 runner drain target。

依題目三分法，五個 surface 是：**已完成 transport 的 retained receipt，對 fresh-zero policy 可視為 stale residue；不是 registry dangling，也不是正式可 drain 的 pending**。不得為了「歸零」手刪。

## Authoritative owners 與資料流（拉高視角）

```text
rewrite publisher / ledger
  └─ seed translations → brief.json + queue/runs active registry（coordinator lifecycle owner）
       └─ coordinator exact cycle → Writer request / lane outbox（outbox pipeline owner）
            └─ runner → processing → inbox + archive + production attempt（transport owner）
                 └─ coordinator consumes result → candidate → Reviewer → terminal registry
                      └─ content publisher → translation publish + ledger
```

- registry lifecycle authoritative owner：`scripts/agy_gemini_coordinator.py`。
- run candidate／review authoritative owner：`scripts/agy_gemini_outbox.py` 經 coordinator tick。
- outbox／processing／inbox／archive／attempt authoritative owner：`scripts/agy_gemini_runner.py`。
- publish／ledger authoritative owner：`scripts/agy_content_publisher.py`。
- service execution authoritative owner：formal manifest/barrier + LaunchAgent control plane；目前 labels unloaded。

三筆的同一 lifecycle cause 是：rewrite `0.3.368` 發布後完成三語 seed，但沒有進入第一個 coordinator Writer tick。五個歷史 inbox retention 是另一個 transport retention invariant，不是造成三筆 brief-only pending 的證據；不得把兩者合併成新 Repair RCA。

## Existing formal operator entrypoints

適用：

- 唯讀狀態：`python -m scripts.agy_gemini_coordinator ... status <exact-run-dir>`。
- 唯一能從 brief-only pending 正常前進的正式 lifecycle 入口：以 `scripts.pantheon_content_runtime_manifest barrier-exec` 包覆 `scripts.agy_gemini_coordinator --lane-mode cycle --exact-run-id <run-id>`。`cycle_once` 的 exact selector 測試證明不推進未列入 run。
- 若 exact cycle 已 materialize 該 run 的 outbox，provider transport 可用 `scripts.agy_gemini_runner operator-exact-process-once`；它要求 current manifest digest、barrier、service label、ready root、plist 與恰好一個 exact run id，並 fail closed。

不適用：

- `runner drain`：只處理 outbox；目前所有 exact namespace outbox／processing 都是零，不會 reconcile inbox retention 或 brief-only registry。
- `terminalize-dangling-active`：run dir 存在，formal precondition 不成立。
- `terminalize-pending`：缺 exact pending job identity、request SHA、model、role、attempt。
- `terminalize-stale-succeeded-writer`：缺 Writer attempt/archive/inbox/candidate evidence。
- `resume`：三筆已是 active；只會重寫同一 registry，沒有 lifecycle 推進價值。

因此現有正式 authority 足以「完成 pending」，但沒有可合法把這三筆 brief-only active 直接 terminalize、也沒有可合法清空歷史 inbox 的 drain seam。本卡不提出新 authority 或 Repair。

## 唯一最小 operational next step

在另取得 production mutation／provider 明確授權，且 fresh Rule24、Rule25、manifest/barrier/runtime identity、capacity 與 no-drift 全部通過後，**只對最早的一筆 EN run `auto-i18n-en-aa637e1bf05d3ad21429` 執行一次 formal barrier-wrapped exact coordinator cycle，然後立即停止並唯讀重查**。不可三筆平行、不可先 load LaunchAgents、不可使用 broad drain。

該一步的成功邊界只是：只有 EN registry/run dir 改變，且最多 materialize／處理一個與 EN namespace 對應的 Writer job；它不宣稱三筆已 drain，也不授權 publish。EN 閉合或取得明確 terminal 狀態後，才可另行決定 KO、JA 是否逐筆重複。

### Stop conditions

- production root、manifest digest、actor head、generation、barrier、plist 或三筆 registry/brief digest 任一漂移。
- 任一 Gemini／coordinator LaunchAgent 意外 loaded，或任一 outbox／processing 在執行前非零。
- exact selector 回報 missing、duplicate、busy、integrity block，或推進未列入 run。
- 一次 cycle 產生第二個 job／candidate，或 job namespace、lane、run、request identity 無法 exact 對上 EN。
- operator seam 要求手改／刪除 inbox、registry、brief、candidate、attempt 或 ledger。
- provider、capacity、quota、credential、Rule24/25 任一 fail closed。
- EN 完成後 registry 未 terminal、publish ownership 不明，或公共內容驗收未另行授權；不得自動進 KO/JA。

## Mutation and push accounting

- production mutation：`0`
- provider call：`0`
- LaunchAgent mutation：`0`
- queue／registry manual edit/delete：`0`
- publish／promotion／commit／push／tag／deploy：`0`
- push required before reconciliation：`false`
