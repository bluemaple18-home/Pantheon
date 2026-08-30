# Pantheon 四線 replacement promotion identity lifecycle RCA

## 狀態

`RCA_COMPLETE`

本卡為唯讀根因分析。未執行 code、test、production、provider、registry、queue、ledger、service、commit、tag、push 或其他 Git mutation；唯一輸出為本 RESULT。

## 唯一主裁決

`REPLACEMENT_IDENTITY_ENVELOPE_PRODUCER_OMISSION`

`auto-i18n-en-aa637e1bf05d3ad21429-replacement-01` 不是在 terminalization 時遺失 identity，也不是 fresh promotion 把合法的 complete-unpublished 狀態誤擋。它在 replacement registry entry 首次建立時就沒有 `identity_envelope`；後續 routing migration 只補 `routing_schema_version / mode / lane`，三次 Writer/Reviewer 執行結束時，generic coordinator 合法把一次 generation execution 寫成 `status=complete`、`approved_by_reviewer=0`，但沒有任何流程負責補回從未存在的 run identity。

fresh promotion 正確要求所有尚未進 publisher ledger、仍需跨 actor 保存的 complete run 必須帶 durable identity envelope，因此在第 137 筆 registry entry fail closed：

`preserved run identity envelope is missing or invalid`

這是 replacement producer 與 2026-08-26 起生效的 durable promotion identity contract 之間的單一契約缺口。

## 不成立的主因候選

| 候選 | 裁決 | 證據 |
|---|---|---|
| producer omission | **唯一主因** | `enqueue_translation_replacement` 建立 state 時從未寫 `identity_envelope`；同一 entry 從建立到 complete 都沒有 clearer |
| promotion overreach | 排除 | promotion 測試明確接受「complete + unpublished + valid envelope」；只拒絕缺失或無效 envelope |
| terminal state misuse | 排除為主因 | `complete` 表示該 generation 的 semantic execution 已終止，不表示 Reviewer APPROVE 或已 publish；publisher 本來就能以後續 formal stage seal 選用被原 Reviewer 拒絕的修訂候選 |
| missing transitional-state contract | 次要因素，不是主因 | formal approval seal、stage 與 publisher ledger 各有清楚角色；它們都不應取代 run 建立時的 immutable identity。新增一個中間 status 不能補回缺失的 identity |

## Exact production finding

目標 run：`auto-i18n-en-aa637e1bf05d3ad21429-replacement-01`

registry：production runtime `queue/runs/1bf0bbc61ff8d10e808f6923.json`

當前 shape：

- `status=complete`
- `mode=translate_existing`
- `lane=i18n-rewrite`
- `replacement_of=auto-i18n-en-aa637e1bf05d3ad21429`
- `replacement_reason=LOCALE_PLAN_VALIDATION`
- `result.status=complete`
- `result.approved_by_reviewer=0`
- candidate/review artifacts 存在
- `last_job_id` 存在
- `identity_envelope` 不存在
- publisher ledger 中沒有此 run
- 沒有 public/publish transaction receipt

這不是壞資料猜測。replacement state、brief、attempts、candidate、review、formal re-review、stage plan-only 與 promotion RED 都指向同一個 exact run。

## 時間線：第 136 筆成功 promotion 與第 137 筆形成

1. g75 transaction `pantheon-four-lane-e01-legacy-replacement-brief-promotion-20260830`：
   - 建立：`2026-08-30T04:12:46+00:00`
   - COMMITTED：`2026-08-30T04:13:15+00:00`（台北 `12:13:15+08:00`）
   - actor：`e01d56e384...`
   - manifest digest：`43e3b4...`
   - preserved registry shape：136 entries，全部通過當時 promotion identity snapshot。
2. target replacement `registered_at=2026-08-30T12:14:11+08:00`，在 g75 commit 後 56 秒成為第 137 筆。
3. attempt 01 約於 `12:14:43` 開始，`12:17:14` 結束；attempt 02 續跑至約 `12:19:32`；attempt 03 與 root candidate/review 在 `12:21:54` 結束。
4. registry 檔案 birth/mtime 為 `2026-08-30T12:21:54+08:00`，此時 generic terminalization 寫成 `status=complete`、`approved_by_reviewer=0`。沒有證據顯示該時間點曾存在後又被清除的 envelope。
5. formal re-review RESULT 於 `12:50:45+08:00` 形成，裁決 `APPROVE_READY_FOR_STAGING`。這是 candidate approval authority，不會回寫 registry identity。
6. exact stage plan-only 後仍無 publish ledger；fresh promotion plan-only 才首次跨 actor 檢查第 137 筆並正確 RED。

因此 last successful shape=136 與 current shape=137 的邊界已閉合：第 137 筆不是舊 promotion 遺留，也不是 g75 漏保存；它是在 g75 之後由 replacement 建立入口新增。

## First commit 與形成機制

### 原始 omission

`7002e135f9f057598d088db4159484ff7bbac697`（2026-07-31，`fix(content): seed bounded i18n replacements`）首次加入 `enqueue_translation_replacement`。

新 replacement state 只寫：

- `schema_version`
- `run_id`
- `run_dir`
- `status=active`
- `registered_at / updated_at`
- `replacement_of`
- `replacement_reason`

它沒有寫 `routing_schema_version / mode / lane / identity_envelope`；existing-state idempotency 也只驗證 run、run_dir、replacement lineage/reason。

### 契約變成 production blocker 的 commit chain

- `ef934239c3f6478760543c4d607950a1aaf2f52a`（2026-08-26 01:37）建立 durable publish/promotion identity lifecycle，promotion 開始要求保存中的 run 有可驗證 identity。
- `34d82a37741ebae652d587b3e24f33c840efee5d`（2026-08-26 21:48）修正常 translation seed，使其寫 identity envelope；但相鄰的 replacement producer 未同步修正，形成 producer contract divergence。
- `d7b09a99bd006544dd703a49f4ce774d32554c66`（2026-08-30 04:11）新增 exact replacement planning CLI，正式 production 入口重用既有 defective producer；其測試只鎖 replacement lineage，沒有要求 promotion-preservable identity。
- `4237d7c282...` 修改 approved replacement stage/publisher transaction；`54ad865467...` 只處理 empty continuation residue。兩者都沒有建立、清除或重建 registry identity envelope，因此不是本 finding 的 first-bad commit。

若以「第一次可產生該 shape」定義，first commit 是 `7002e135f9f...`；若以「已存在 durable identity invariant 後仍正式接受該 shape」定義，contract divergence 從 `34d82a3774...` 起可見，並由 `d7b09a99bd...` 的 exact CLI 使其正式 production 可達。

## identity_envelope producer / clearer / consumer call chain

### 正常 producer

1. `scripts/agy_gemini_coordinator.py::_build_identity_envelope`
2. coordinator `register_run` 與 reservation activation：建立 registry 時原子寫入 identity envelope。
3. `scripts/agy_multilingual_pipeline.py::translation_identity_envelope`
4. `enqueue_article_translations`：建立 normal locale run 時寫入 lane/routing 與 identity envelope。

### replacement producer

1. exact CLI `replace_failed_translation_run_exact` 或 automatic `seed_failed_translation_replacements`
2. 兩者共同呼叫 `enqueue_translation_replacement`
3. 該函式只寫 replacement lineage，省略 identity envelope
4. `_lane_for_state` 後續可從 brief 推導並補 routing tuple，但不補 identity envelope
5. `_active_run_integrity_block` 只在 envelope 已存在時驗證，沒有把缺失視為 active-run integrity error

### clearer

沒有 clearer。

repository source 沒有任何 terminalization 路徑對本欄位執行 `pop` 或設成空值。generic `_advance` 成功時只寫：

- `state.status=complete`
- `state.result=result`
- 清除 error 欄位

所以「lifecycle terminalization 清掉 identity」被反證；正確形成鏈是「producer 從未建立 → 後續也未補」。

### consumer

`scripts/pantheon_content_runtime_promotion.py::_queue_identity_snapshot`：

- complete 且已在 publisher ledger：publication ledger 是完成發布後 authority。
- failed 且沒有 envelope：可走既有 terminal/brief reconstruction 分支。
- 其他仍需 preserved 的 run（包含 complete-unpublished）：必須通過 `_validated_run_identity_envelope_value`。

target 屬第三類，缺 envelope，故 plan-only NO-GO。

## Durable authority owner：從 replacement 到 publish

| 階段 | authoritative owner | 能證明什麼 | 不能取代什麼 |
|---|---|---|---|
| replacement 建立 | registry identity envelope + normalized replacement brief/source terminal lineage | run_id、source identity、mode/lane、replacement lineage 的 immutable identity | 不能由後續 candidate approval 猜回 |
| Writer/Reviewer attempts | generation/attempt artifacts與 operation receipts | provider request/response、candidate、deterministic review、attempt terminal result | `approved_by_reviewer=0` 不等於 run identity 無效 |
| manual formal approval | isolated formal review result + exact approved candidate digest | 哪個修訂 candidate 可進 staging | 不擁有 registry lifecycle identity，也不代表 published |
| stage | approved revision stage seal | Publisher 可採用哪個 exact candidate/review revision | 不應回寫或取代 run identity |
| publish | publisher ledger + transaction/tag/push/public receipt | 已發布 run、公開 artifact 與 transaction authority | publish 前 ledger 正確地不存在 |
| promotion | queue identity snapshot + publisher ledger + manifest transaction | 跨 actor 保存目前所有 durable run/publication identities | 不應創造缺失的 producer identity或放寬 fail-closed guard |

authoritative owner 在各 boundary 是接力而非互相覆蓋：registry run identity 先存在；attempts 與 approval seal 增加 candidate authority；publisher ledger 只在 publish transaction 成功後成為 publication authority；promotion 只驗證和保存，不發明身份。

## Promotion / replacement boundary

promotion 的責任是切換 actor/manifest 並 preserved current queue/publication identities；它不負責將 replacement brief 重新註冊成 run，也不判斷 formal review 是否應回寫 registry。

replacement 的責任是在正式建立入口鎖定 immutable run identity 與 source lineage。既然 exact CLI 和 automatic seeder 都能建立 production registry entry，兩者必須在建立點符合與 normal runs 相同的 preserved identity contract。

因此不可把 repair 放在 promotion consumer：那會讓每個 future consumer 各自從 mutable brief/attempt residue 猜 identity，也會把 producer omission永久正常化。

## Production-shaped provider=0 RED

既有 acceptance 已提供 exact production-shaped RED，不需也不得重新呼叫 provider：

- exact stage plan-only：`GREEN_CONFIRMED`
- `production_mutation=false`
- provider/writer/reviewer/publisher calls：0
- stage apply：0
- fresh promotion plan invocation：1
- promotion apply/finalize：0
- return code：1
- exact error：`preserved run identity envelope is missing or invalid`
- candidate/reviewer boundary未重跑
- Gen/attempt/content未新增

這個 RED 使用 current production registry 137 entries、current ledger 與 fresh promotion planner；不是手造 forged state，也不是單元測試替代 production shape。

## Protected bytes before == after

`phase-1` evidence 的 before/after snapshots 在移除 evidence-only `snapshot_phase` 後完全相等：

- queue
- state/ledger
- runtime manifest
- stage evidence
- live plists/services configuration snapshot
- production static/content bytes

`mutation-accounting.json` 明列：

- `production_mutation=0`
- provider/writer/reviewer/publisher/service mutation=0
- commit/tag/push/public request=0
- `protected_bytes_unchanged=true`

before/after snapshot 檔本身的 raw SHA 不同，只因 snapshot metadata 的 phase 名稱不同；其 protected surface maps 逐項相等。這不構成 production drift。

## 同類 shape inventory

### Current production registry（137 entries）

共有 5 筆沒有 identity envelope：

1. target replacement：唯一 `complete + run_dir exists + unpublished + replacement_of + envelope absent`，也是唯一會撞目前 promotion preserved-run branch 的實例。
2. 其餘 4 筆為 failed missing-run tombstones，沒有 live run_dir/ledger，屬 promotion 既有 failed/terminal receipt contract，不是本 finding 的同類 shape。

所以 current production measured gap 是一筆，不是 registry-wide corruption。

### 正式可達 producer inventory

| 入口 | producer | 同類 shape 可達性 |
|---|---|---|
| coordinator normal register/reservation | coordinator identity producer | 不可達；建立時有 envelope |
| normal translation enqueue | `enqueue_article_translations` | 不可達；建立時有 envelope |
| exact failed-translation replacement CLI | `enqueue_translation_replacement` | **可達**；本次 production path |
| automatic failed-translation replacement seeder | 同一 `enqueue_translation_replacement` | **可達**；相同缺口，雖 current registry 未出現第二筆 complete-unpublished instance |
| APF/private copied-queue helpers | isolated/copied staging state | 非正式 production CLI 寫入路徑；不納入本卡 implementation scope |

不能只以 run ID 137 特判。真正 bounded population 是「由同一 replacement producer 建立、尚未 publish、需要 promotion preserved 的 entries」，涵蓋 exact CLI 與 automatic seeder，但不涵蓋所有 complete run 或所有 legacy registry entries。

## Change-impact / system view

`4237` 與 `54ad` 影響的是 approved candidate stage/publisher consumption 與 empty continuation normalization。它們沒有改動 replacement registration identity，也沒有放寬 promotion snapshot。因而：

- 不需重驗 normal `new / rewrite / i18n-new` producer identity。
- 不需重做 content、Writer、Reviewer 或 public URL。
- 不需改 publisher ledger schema。
- 不需重跑四 lane canary。
- 只需修復 replacement registration identity seam，以及對已被此正式 seam 產生的 exact current entry提供同一契約下的 bounded reconciliation。

這不是第三套 lifecycle 或新 FSM；是既有 identity invariant 漏接到 replacement producer。

## 最小 coherent implementation frontier（若開 Repair）

只能有一個 frontier：`replacement identity registration/reconciliation seam`。

其契約應是：

1. `enqueue_translation_replacement` 在建立新 entry 時，從已驗證的 normalized replacement brief、source terminal state 與 replacement lineage，使用既有 canonical identity builder，原子寫入 routing tuple + immutable identity envelope。
2. existing-state idempotency 必須驗證相同 envelope；drift、歧義、不同 source/reason 一律 fail closed。
3. 對 current 137，只能由同一 coordinator-owned exact seam 執行 plan-first、exact-run reconciliation：驗證 exact run ID/state digest、source lineage、normalized brief、attempt lineage、無 publish ledger、無第二候選身份後，確定性補上與新 producer 完全相同的 envelope。
4. reconciliation 必須 receipt-first、single-run、idempotent；不得掃描 registry 自動挑選或改 lifecycle status/result。

本次 production entry 已被 exact CLI、brief、registry timeline與 attempts 證明是正式 producer 產物，因此 bounded exact reconciliation 有正式 contract 依據；這不是 generic legacy migration。

### why_not_less

- 只修 future producer：current 137 仍永久被 fresh promotion 擋住。
- 只在 promotion 臨時 reconstruct：留下 defective producer，擴大 consumer authority，而且 automatic seeder 下一筆仍會重現。
- 只新增 transitional status：不會產生 immutable identity。

### why_not_more

不需要新 registry、ledger、FSM、database、canonical writer或新的 manual approval authority。publisher/stage/promotion guard 的責任已清楚且現有 fail-closed 行為正確。

### do_not_absorb / 防膨脹

禁止：

- 手改 production registry JSON
- generic registry-wide migration
- 依 timestamp 或掃描 residue 猜 job/run identity
- 將 `complete` 改名或新增跨系統 transitional FSM
- 放寬 promotion identity validator
- 以 formal approval seal 或 publisher ledger冒充原始 run identity
- 改 Writer/Reviewer/provider/content
- 重跑 semantic generation
- 建新 generation/replacement
- 改 publisher transaction、promotion manifest schema或四線 routing
- 為 APF/private helper 擴 scope

若實作時需要第二個 source-of-truth、第二個 identity builder或第二個 lifecycle seam，應立即 `BLOCK_SCOPE_EXPANSION`，不得逐層補洞。

## Acceptance boundary

本卡只完成 RCA，不代表 Repair、promotion、stage、publish 或四線 activation 完成。

後續若開 bounded Repair，必須先用 production-shaped provider=0 fixture證明：future exact/automatic replacement entry 皆帶 envelope；current formally-created entry可在 exact reconciliation後通過 fresh promotion plan；任一 identity drift仍 fail closed；protected bytes除授權 receipt/identity欄位外不變。再回原 Reviewer，而不是另開架構工程。

## 最終結論

第 137 筆不是在 formal approval、terminalization、stage 或 promotion 中遺失身分。它由 2026-07-31 引入、2026-08-30 exact CLI 重用的 replacement producer，以不含 identity envelope 的舊 state shape正式建立；routing migration與 generic completion只把這個缺口帶到跨 actor promotion boundary。

promotion 的 NO-GO 正確。publisher ledger 在尚未 publish 時缺席也正確。唯一錯誤是 replacement producer 未履行既有 durable identity contract；最小修復只能留在 replacement identity registration/reconciliation 的單一 coherent seam。
