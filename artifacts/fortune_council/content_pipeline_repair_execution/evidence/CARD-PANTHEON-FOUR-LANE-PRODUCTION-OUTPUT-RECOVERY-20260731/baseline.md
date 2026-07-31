# SLICE-OBSERVE-001 基線

## 觀察身分與時間窗

- card：`CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731-RETRY-1`
- dispatch：`v1:fbc0ab99ea1425b00d27b384ce04942232a2bff7fcf705a70321c19ea6952f4a`
- formal thread：`019fb598-204e-7cd0-b6b6-004b159365ba`
- timezone：`Asia/Taipei`
- fresh observation window：`2026-07-31T08:39:01+08:00` 至 `2026-07-31T08:44:59+08:00`
- source worktree HEAD：`de68b6b283493a3e9ca5f80286c682cb7846735e`
- source worktree state：clean

本文件只保存封閉 metadata、hash、狀態、計數與錯誤分類；未保存 API key、
credential value、cookie、token、prompt、文章正文或未封閉 provider output。

## Locator alias

為避免把單機絕對路徑寫進跨機 evidence，以下使用：

- `<repo-root>`：本 candidate worktree。
- `<production-root>`：安裝中 coordinator 所指向的 Pantheon production checkout。
- `<publisher-actor-root>`：六個 LaunchAgent 的 `WorkingDirectory`。
- `<queue-root>`：`<production-root>/.work/gemini-runner`。
- `<publisher-state-root>`：`<publisher-actor-root>/.work/content-publisher`。
- `<log-root>`：安裝中六個 LaunchAgent 的 stdout／stderr 目錄。

## Capability 與 source context

- `worktree_capability_preflight.sh --prepare --with-codegraph`：
  - `worktree_registered=true`
  - `provisioning=ready`
  - `codegraph=ready`
  - `codegraph_indexed_sha=de68b6b283493a3e9ca5f80286c682cb7846735e`
  - `python_tests=blocked:uv_sync_failed`
  - `node_tests=blocked:pnpm_install_failed`
- Python／Node dependency preparation受 sandbox cache 與 registry DNS 限制，但
  CodeGraph 索引成功完成（347 files、4,043 nodes、3,669 edges）。
- 實際 CodeGraph query 與原始碼確認記錄於 `observe-verification.md`。

## Source、runtime 與 Publisher actor

| 項目 | 觀察值 | 判定 |
|---|---|---|
| source worktree HEAD | `de68b6b283493a3e9ca5f80286c682cb7846735e` | required base 相符 |
| Publisher／lane actor HEAD | `dde0cd214fea9b9e6567ed5ec7b7a82113cc836d` | 與 source 不同 |
| actor local `origin/main` | `de68b6b283493a3e9ca5f80286c682cb7846735e` | source 相符 |
| actor worktree | clean | 無 actor local dirty |
| installed expected runtime SHA | `dde0cd214fea9b9e6567ed5ec7b7a82113cc836d` | actor HEAD 相符 |
| installed／actual runtime digest | `f6c18b3c91df5b393339a9342bce8893a85106e956361fb4e525ce66b8d6e439` | digest 相符 |

依本卡 stop condition，source、runtime、Publisher actor SHA 不一致構成
`BASELINE_BLOCKED_RUNTIME_SHA_MISMATCH`。本次未 reload、deploy 或 publish。
目前 actor 與安裝契約彼此一致，且 local `origin/main` 已前進到 source SHA；
這不能取代卡片要求的 exact actor SHA 一致性。

## LaunchAgent 快照

`2026-07-31T08:39:01+08:00` 的唯讀 `launchctl print`：

| actor | service state | last exit | 說明 |
|---|---:|---:|---|
| coordinator | not running | 0 | 週期型 job；不能據此判 productive |
| new | not running | 1 | 最近一次 runner 結束為 failure |
| rewrite | not running | 0 | 最近輸出為 `idle` |
| i18n-new | not running | 0 | 最近輸出為 `idle` |
| i18n-rewrite | not running | 0 | 最近輸出為 `idle` |
| Publisher | not running | 0 | 最近 aggregate 輸出為 `ok`，但各 phase 可為 idle／blocked |

coordinator stderr 仍保留一筆歷史 `node` 不在 LaunchAgent PATH 的 traceback；
fresh stdout 已能產生 lane inventory，因此不把該歷史 traceback當成本觀察窗的
主因。

## Eligible input 與累積 count

### Fresh state inventory

`2026-07-31T08:44:59+08:00` 前的 run-state 分類：

| lane | active | complete | failed | fresh eligible 判定 |
|---|---:|---:|---:|---|
| new | 1 | 225 | 449 | `processing`；active-floor seeder 持續補新 run |
| rewrite | 0 | 42 | 133 | `blocked`；存在真實 backlog，但 selector／retry gate 不放行 |
| i18n-new | 0 | 89 | 40 | `idle_no_eligible_work`；最後三個 v0.3.183 translation 已終態失敗 |
| i18n-rewrite | 0 | 3 | 0 | `idle_no_eligible_work`；最後 candidate 已終態 REJECT／deferred |

另有兩筆歷史 failed rewrite state 指向已不存在的舊 worktree run directory；
它們不是 active input，未納入 fresh eligible work。

### Queue snapshot

`2026-07-31T08:39:41+08:00` 的 lane queue 計數如下。`inbox`、`failed`、
`archive`、`production-attempts` 都是累積稽核量，不等於 backlog：

| lane | outbox | processing | inbox | failed | archive | attempts |
|---|---:|---:|---:|---:|---:|---:|
| new | 0 | 0 | 1,980 | 484 | 2,464 | 2,464 |
| rewrite | 0 | 0 | 235 | 122 | 357 | 356 |
| i18n-new | 0 | 0 | 441 | 10 | 451 | 451 |
| i18n-rewrite | 0 | 0 | 16 | 0 | 16 | 16 |

new 的瞬時 outbox／processing 為 0，但 run state 仍 active；相鄰 coordinator
snapshot 曾顯示 queued 或 processing 1，runner 很快把 job 移入
archive／inbox／failed。這個 race 不改變「有 active eligible run」的判定。

### Rewrite 真實 backlog

Publisher／coordinator summary：

- legacy total：353
- released：1
- clean approve：5
- reject：32
- active or incomplete：133
- attempted：174
- unattempted：179

179 是尚未嘗試的真實 inventory，不是目前 eligible queue。五個
clean-approved run 都有 `retry/rewrite/<run-id>.json`：

- `attempts=3`
- `max_attempts=3`
- `eligibility=exhausted`
- `error_type=CalledProcessError`
- failure command 為 Publisher release-gate pytest，exit 1
- `candidate_preserved=true`

coordinator 因 `clean_approve > 0` 回 `publish_ready_first`，Publisher
`collect_ready_rewrite_runs()` 又因 `_retry_eligible()` 為 false 跳過五筆，
形成 selector／retry head-of-line deadlock。

## 各 lane 最近可追溯結果

### new

最近完整成功鏈：

- run：`auto-new-v1-20260731-077-01`
- final job：`979c6d34181c546116e678d06c4e4197e7c0b89e`
- provider response：`2026-07-31T06:48:36+08:00`
- run complete：`2026-07-31T06:49:31+08:00`
- reviewer：`APPROVE`，finding 0
- Publisher ledger：version `0.3.183`
- publish time：`2026-07-31T07:04:29+08:00`
- commit／release SHA：`de68b6b283493a3e9ca5f80286c682cb7846735e`
- local immutable tag：`v0.3.183`

從 v0.3.183 publish time 起到觀察窗，共新增 52 筆 new-lane failed record：

- 52／52：`V4BrokerFailure`
- 52／52：`failure_category=SCHEMA_INVALID_PAYLOAD`
- 52／52：broker `outcome=SUCCESS`
- 52／52：`result_validation=SCHEMA_MISMATCH`
- closed schema diagnostics：`maxLength` 94 次、`minLength` 23 次

最近 locator：
`<queue-root>/lanes/new/failed/c570471f71d441ee2f983b71368ba31252c61939.json`；
其 provider process 為 SUCCESS，但多個 paragraph 命中 `maxLength`。
這是 deterministic schema failure，不是 credential／auth outage。

### rewrite

最近 dedicated rewrite lane 成功到 candidate：

- run：`legacy-auto-sweep-v1-interpersonal-0007-theme-interpersonal-07`
- final job：`99e382e273c10f50e287f87df1a5f7cfe53ecd27`
- provider response：`2026-07-30T04:13:25+08:00`
- run complete：`2026-07-30T04:14:09+08:00`
- reviewer：`APPROVE`，finding 0
- candidate：存在且 `candidate_preserved=true`
- Publisher retry：三次 release-gate pytest 均 exit 1，現為 exhausted

最近已發布 rewrite 成功鏈：

- run：`legacy-manual-requeue-v2-fortune-0039-expansion-50d-fortune-0039`
- version：`0.3.132`
- publish time：`2026-07-30T03:36:52+08:00`
- commit：`443dc0be0040964f70f8c0fb0b1e352bdb819f77`
- local immutable tag：`v0.3.132`

### i18n-new

v0.3.183 新文發布後 seed 三個 locale run；三筆都以 `ValueError` deferred。
ko locator：

- run：`auto-i18n-ko-d069fa6b3a94ae07bbd8`
- final job：`72760b166343c0582f708316ca9f695fc6454eac`
- provider response：`2026-07-31T07:09:27+08:00`
- runner／broker response schema：成功進 inbox
- run terminal：`failed / ValueError`，`2026-07-31T07:10:04+08:00`
- Publisher deferred：`run failed: ValueError`，`2026-07-31T07:10:43+08:00`
- red-capable replay：`locale plan coverage mapping differs for article-01`

最近 i18n-new release 成功為 version `0.3.173`：
`831df76ce97859bd92613398d9e220d72c94282f`，
`2026-07-30T11:36:22+08:00`。ledger 中 60 筆 translation publication
皆不屬於 353 個 legacy article IDs。

### i18n-rewrite

最近完整到 candidate 的 run：

- run：`auto-i18n-ko-149a513358e0e81cadcd`
- source rewrite：`legacy-manual-requeue-v2-fortune-0039-expansion-50d-fortune-0039`
- final job：`5bd9ff383544c14b11baae65e586643cdcfd350e`
- provider response：`2026-07-30T03:56:58+08:00`
- run complete／candidate persisted：`2026-07-30T03:57:30+08:00`
- reviewer：`REJECT`
- finding codes：`NON_NATIVE_SEARCH_INTENT`、`AI_TEMPLATE_STYLE`
- Publisher deferred：`translation reviewer did not cleanly approve`
- ledger 中 legacy translation published count：0

此 lane 的 gate 正確 fail-closed；不得以放寬母語品質契約修復。

## 基線結論

1. new 有已證明的 v0.3.183 成功鏈，但其後 52 次 provider SUCCESS output
   全部在 schema 層失敗；credential pool 不是本輪根因。
2. rewrite 有 179 筆真實未嘗試 inventory 與 5 筆 clean-approved candidate，
   但 coordinator `publish_ready_first` 與 Publisher exhausted filter 互鎖。
3. i18n-new 的 provider transport／response schema 成功，之後在 locale-plan
   coverage contract deterministic 失敗。
4. i18n-rewrite 能保存 candidate，但母語 reviewer 明確拒絕，Publisher 正確
   deferred；尚無 legacy translation release 成功。
5. source 與 production actor SHA 不一致，依卡片契約維持 baseline blocker；
   本 task 不發布、不 repair。
