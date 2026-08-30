---
id: PANTHEON-NEW-LANE-CURRENT-READINESS-RCA-20260829
status: complete
type: rca
acceptance: NO-GO
operation: read_only
---

# RESULT：New lane current readiness RCA

## 裁決

`new` 目前仍是 `NO-GO`，而且不是先 push。

單一主因是：**最老的 active `new` run 持有一筆已 succeeded、但尚未被 coordinator 消耗的歷史 Writer response；現有正式操作 seam 又不允許安全放棄這種 provider outcome。** 正式 lane selector 固定選每條 lane 最早註冊的 active run，因此它會先選 `auto-new-v1-20260826-001-01`。該 run 若 resume，只能消耗 2026-08-26 的 job `6972e806...`，不能算 current fresh Writer call。

Secondary factor 是：**dfcb／g68 promotion 後沒有執行 live 七服務 activation。** live `com.pantheon.agy-gemini-new.plist` 仍是 `6477`／g47；即使已有 fresh run，目前 provider entrypoint 也會因 identity mismatch fail closed。

兩者皆是獨立 blocker，但屬性不同：

- plist drift 是正常 operation gap，並非 promotion code bug。promotion 的設計契約只切 actor、runtime manifest、readiness acknowledgements 與 barrier；不 install、不 bootstrap live plist。
- stale response 是 crash-safe／resume-safe durability 的正常中間狀態；但「current acceptance 必須是新 Writer call」新增了 freshness 條件，而現有 operator lifecycle 沒有可安全放棄 succeeded-unconsumed response 的窄 seam。這是已量測的 lifecycle contract gap，不可用手改 state 解決。

## 四項證據

### 1. 最後成功的 `new` production/public

- run：`v0391-publish-canary-20260826-02`
- article：`V2-TAROT-DEATH-MONEY`
- URL：`https://www.mysticpantheon.com/articles/tarot/tarot-1884`
- version：`0.3.371`
- publish commit：`0257bd5213eed0d0df10661a54f6215901a54997`
- published at：`2026-08-26T10:31:43+08:00`
- runtime actor：`6477ab815e8aecca7d1e8e1588e6e5eba0fab001`

現有 evidence 沒有把該 publish transaction 精確綁到一個 installed new-service generation；g47 plist 的檔案時間是 `10:45:12`，晚於 `10:31:43` publish，因此本 RCA 不把 g47 冒充該次 publish runtime generation。

### 2. plist drift 與 active residue 的形成機制

g47 live plist 最後修改於 `2026-08-26T10:45:12+08:00`。其後第一筆 actor/manifest promotion 是 `v0404-gsc-json-shape-e5c0743f-20260826`，於 `19:43:53` COMMITTED；promotion receipt 的狀態機只有 `ACTOR_PROMOTED → MANIFEST_WRITTEN → STAGE_INSTALLED → POSTCHECK_PASSED → COMMITTED`。source 中 `STAGE_INSTALLED` 實際只建立 readiness ack 與 barrier，不寫 live plist。這是從 g47 開始出現 installed identity drift 的第一筆 operation，不是 e5c commit 新增的 regression；promotion 自 `11e6c4c1056` 起即是這個邊界。

active residue 的 formation chain 是：

1. `10:45:19` run 登記 active。
2. `10:45:20` coordinator 將 Writer operation 記為 `pending`，job=`6972e806...`。
3. `10:46:45` runner 將 production attempt 記為 `succeeded`，相同 response 同時持久化在 inbox／archive。
4. 沒有下一次 coordinator consumption 把 run 推進成 candidate／failed／complete；後續 promotions 依 preservation contract 持續保留此 active identity。

所以 residue 不是某次 migration commit 亂造資料，而是非同步 handoff 在「provider 已完成、coordinator 尚未消耗」的 durable 邊界停住。

### 3. Durable invariants

- promotion identity 與 installed-service identity 必須分開驗收。只有兩者 actor／manifest digest／generation 同 tuple 時，provider entrypoint 才可執行。
- response 永遠屬於 immutable `job_id + request_sha256 + production attempt`。resume 可以消耗歷史 attempt，但不得把它改名成 current call。
- current acceptance 的 fresh run 必須在 current acceptance window 由 current actor 建立，且此前不存在 succeeded provider outcome；後續 candidate、review、publish、public URL 必須沿同一 correlation closure。
- 舊 inbox／archive 是不可刪的歷史證據。terminalization 只能新增 hash-bound receipt 與 terminal state，不能刪除或假裝未發生。

### 4. RED-capable plan-only preflight

已實際執行 `current_readiness_preflight.py`，exit code `1`，同一次唯讀檢查精確抓到：

- `INSTALLED_SERVICE_IDENTITY_MISMATCH`
- `STALE_SUCCEEDED_PROVIDER_RESIDUE`

receipt 同時記錄 `production=0`、provider/reviewer/publisher calls=`0`、Git writes=`0`。修復後，只有 current manifest 與 installed plist 完全一致，且 selected run 沒有 succeeded historical attempt，這條命令才會轉綠。

## 正式 contract 判定

### promotion 是否應自動 install live plist

不應。現行 separation 是明示設計：

- `--install` 只把 plist 寫入 private stage，輸出也明說「尚未 activation」。
- `--activate` 才 snapshot 舊狀態、replace 七份 live plist、bootout／bootstrap 七服務、做 live aggregate validation 與 rollback。

因此不可把 activation 偷塞進 promotion；應由 production operation 明確執行並保留獨立授權與 rollback。

### 是否已有七服務 activation/reload seam

有：`scripts/install_agy_gemini_coordinator_launchd.sh --install` 後接 `--activate`。它涵蓋 coordinator、四 lane、publisher、capacity guard 共七服務。當前唯讀 `launchctl print` 七個 label 全部回 113，亦即現在沒有服務 loaded；這提供安全的收斂窗口，但本 RCA 沒有執行 activation。

### fresh new run 應 create 還是 resume

必須由正式 new-matrix scheduler／backlog create；不得 resume `auto-new-v1-20260826-001-01` 作為 current acceptance candidate。

scheduler 本身在 active create count 低於 floor 時，每 cycle 最多建立一個未登記 matrix item；但 selector 固定先推進最早註冊 active run。因此在舊 run 未合法 terminalize 前，直接 create 第二個 run 仍不夠，selector 仍會先取舊 run。

### 舊 succeeded Writer job 能否用既有 seam terminalize/quarantine

不能：

- `terminalize-pending` 明確拒絕任何 inbox／failed provider outcome，也拒絕已存在 production-attempt evidence。
- `terminalize-dangling-active` 僅適用 run directory 已遺失；本案 run directory 存在。
- 舊 inbox／archive 不應 quarantine 或刪除。

所以不能假裝這只是已有 CLI 可處理的 operation。必須先補一個非常窄的 operator seam。

## 唯一 bounded frontier

1. 新增一個 hash-bound `plan-only / execute` terminalization seam，只接受以下完整形狀：run active、Writer operation pending、attempt succeeded、inbox/archive 與 job/request hash 全相符、candidate/review 都不存在。
2. execute 只可把 exact run 寫成 terminal failed/superseded 並新增 immutable receipt；不得刪除、搬移或 quarantine inbox/archive。
3. 將這個最小 Repair 形成新的 current actor，照既有 promotion 邊界 promotion；不要把 activation 併入 promotion。
4. 七服務仍停止時完成 exact stale run terminalization，再做 current manifest 的 `--preflight → --install → --activate`。
5. 讓正式 new-matrix scheduler 從 backlog 建立一個新的 current run，並驗證 selector exactly one；之後才進 Writer 1 次的 production acceptance。

`why_not_less`：只 activation，舊 run 仍優先；只 create 新 run，舊 run 仍優先；resume 則會消耗歷史 response。

`why_not_more`：不需要新 registry、FSM、scheduler、queue rewrite、bulk cleanup 或 Publisher 變更。

`do_not_absorb`：第二套 runtime／queue、泛用 state editor、舊 evidence 刪除／隔離、自動 promotion→activation、provider/reviewer/publisher retry loop。

## Evidence index

- `machine-receipt.json`
- `formation-timeline.json`
- `red-preflight-receipt.json`
- `current_readiness_preflight.py`
- 上游 acceptance：`../CARD-PANTHEON-NEW-LANE-CURRENT-PRODUCTION-ACCEPTANCE-20260829/RESULT.md`

## Not claimed

- 沒有 terminalize／resume／create run。
- 沒有 install、activation、reload、promotion 或 service mutation。
- 沒有 provider、Reviewer、Publisher、commit、push、tag、deploy。
- 沒有刪除或隔離舊 inbox／archive。
