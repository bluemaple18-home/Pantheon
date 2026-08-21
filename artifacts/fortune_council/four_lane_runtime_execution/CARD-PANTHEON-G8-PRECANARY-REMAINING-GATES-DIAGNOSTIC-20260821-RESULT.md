---
id: CARD-PANTHEON-G8-PRECANARY-REMAINING-GATES-DIAGNOSTIC-20260821-RESULT
card_id: CARD-PANTHEON-G8-PRECANARY-REMAINING-GATES-DIAGNOSTIC-20260821
chain_id: pantheon-g8-precanary-remaining-gates-diagnostic
role: architecture-diagnostic-auditor
status: DIAGNOSIS_COMPLETE
source_sha: 1d608410cc9ee9adc6fc3bc53c515e4ecd4005d1
bootstrap_sha: 78af0a96d3e8ba4fc0057d408499465ec9cbe687
date: 2026-08-21
---

# G8 PRE-CANARY REMAINING-GATES DIAGNOSTIC RESULT

## 終局判定

`DIAGNOSIS_COMPLETE`

Cycle 32 的第一個正式 blocker 不是 staged Capacity plist，也不是 coordinator 本身必須有 PID；是 **舊 live cohort 的 Publisher 仍為 normal scheduled，而 Capacity preactivation transition 要求整個七服務舊 live cohort均為 activation-only、loaded/no-PID**。精確 mismatch 為：

- service：`com.pantheon.agy-content-publisher`
- plist：`~/Library/LaunchAgents/com.pantheon.agy-content-publisher.plist`
- 欄位：`ProgramArguments` 中 `--` 分隔符之前的 `--activation-only`
- expected：存在，亦即 `activation-only`
- actual：不存在，亦即 `normal`
- actual authority：前一次 Publisher-only canary／terminal state 留下的 live G23 Publisher plist；它不是 Cycle 32 staged G34 plist，也不是 current manifest 檔案內容。

`scripts/pantheon_content_runtime_manifest.py:319-380` 定義 activation-mode 解析與通用錯誤；`scripts/pantheon_content_capacity_guard.py:698-728` 驗證新 staged 七服務為 normal，`scripts/pantheon_content_capacity_guard.py:732-810` 另驗證舊 live 七服務為 activation-only、loaded/no-PID。由於 live loop 依 `scripts/pantheon_content_runtime_manifest.py:23-31` 的順序先檢查 Publisher，錯誤停在 Publisher。

整體判定：

- **PRIMARY：`FIX TRANSITION MODEL`**
- 同時需要：`FIX LOCAL CONTRACT`、`FIX TEST FIXTURE`
- production runtime state 確實需由既有正式 transition authority 收斂，因此也有 `FIX PRODUCTION RUNTIME STATE`，但禁止手改 plist，且它不是唯一根因。
- **`ARCHITECTURE CONTRACT MISMATCH`：YES**。Capacity raw preflight、Capacity transition、current readiness／Rule 25 對「哪個 phase、何種 loaded/no-PID 狀態算可授權」沒有共同、phase-bound 的 authority。

## Evidence identity 與方法

- formal thread：`01a0248e-9481-73e0-aa1a-c7e4ccd526d4`
- projectId：`c2xpbmdzaG90OmVudl9lXzZhMTdiMzc4MTg1ODgzMmRhZWU4Njk3YzMwZmM3ZTdjCi9Vc2Vycy9tYXR0a3VvL0RvY3Vtcy9QYW50aGVvbg==`
- worktree：`<repo-root>`，detached HEAD `78af0a96d3e8ba4fc0057d408499465ec9cbe687`，與 main 共用 bootstrap commit 是已接受前提；checkout/worktree 隔離成立。
- evidence source `1d608410cc9ee9adc6fc3bc53c515e4ecd4005d1` 可讀且為 main ancestor。
- task card blob：`b19f1564bc7ef5e8949082f11a227f14a061e644`。
- Cycle 32 RESULT SHA-256：`c8c564f59355852b4b03ffce9aef37e7d9de3720c63d73a9abc9e91a6c1d3bf5`。
- Cycle 31 RESULT SHA-256：`97af0241c468fb1b4e122b6c888b0b5497d83b869363bdae3e8103187272bf06`；本報告只作歷史比較，未用作 current-target PASS evidence。
- canonical TMPDIR review SHA-256：`f14dce6dc56f87c7ff127fcc038fcabf234da733e0de0fe1f339ed8777567cef`；repair commit `d9e21adc9eb6439307341080f39e6d044e0492e9`。
- 只執行一次 bounded CodeGraph prepare；結果為 578 files、6595 nodes、14345 edges、native backend、indexed SHA 等於 HEAD。其後執行七組 task-semantic query；語意結果不足處才限域讀 source。
- production 檢查只有 plist／manifest／stage controls／`launchctl print` 唯讀讀取；沒有 reset、install、activation、canary 或任何 state mutation。

## A. 精確 activation-mode mismatch

以下為 2026-08-21 在 Cycle 32 rollback 後的唯讀 snapshot。Cycle 32 RESULT 明載 live plist mutation count 為 0，因此 live mode 可用來重建當時比較；G34 staged bytes 已隨 rollback 移除，staged 欄以 Cycle 32 receipt 與 installer contract為 evidence，而非把 current rollback stage冒充 G34。

| service_label | live_present / loaded / PID | live mode | staged_present / mode（Cycle 32 gate 時） | expected preactivation | actual_mode_source | 判定 |
|---|---|---|---|---|---|---|
| `com.pantheon.agy-content-publisher` | yes / no / none | **normal scheduled** | yes / normal exact-run, max-runs=1 | live activation-only；stage normal exact-run | live G23 plist SHA-256 `76b67acb55c5b980ecc8376f8f882ac0c620acc56818254ef85eabfa830b9bc5`；stage由 Cycle 32 receipt | **MISMATCH（live）** |
| `com.pantheon.agy-gemini-coordinator` | yes / yes / none | activation-only | yes / normal | live activation-only；stage normal | live SHA-256 `47acc76339a33df62f8155d06a74f4f4ab4e5bb7575aa3689ef81e0bbcd42dbb` | match |
| `com.pantheon.agy-gemini-new` | yes / yes / none | activation-only | yes / normal | live activation-only；stage normal | live SHA-256 `639f0eff2ba055ef109d92da1a094023b0e7a2abb466745a002f7fcf4895f773` | match |
| `com.pantheon.agy-gemini-rewrite` | yes / yes / none | activation-only | yes / normal | live activation-only；stage normal | live SHA-256 `edd4121ff3fe26f1e0d2c67f98592806e926c7cc188bae5f9c66aac5e0ad087e` | match |
| `com.pantheon.agy-gemini-i18n-new` | yes / yes / none | activation-only | yes / normal | live activation-only；stage normal | live SHA-256 `792ff0e76e84ed078dbee7fed78f204a1272624f3cb75f508798a5bf0212ee8a` | match |
| `com.pantheon.agy-gemini-i18n-rewrite` | yes / yes / none | activation-only | yes / normal | live activation-only；stage normal | live SHA-256 `a9b4b7530dff08dfca0e8a7eb90277cdf6a912d345a8711c6f7980ce1076b9cd` | match |
| `com.pantheon.content-capacity-guard` | yes / yes / none | activation-only | candidate yes、尚未安裝 / normal | live activation-only；candidate normal | live SHA-256 `014e7161d0347e628d7d8e912400b251b12d0770d2c6d4700a352ca48a1ca450`；candidate由 Capacity installer temp plist | match |

沒有額外 runtime service參與這次 transition。Capacity RSS sampling 的 `SERVICE_LABELS` 是 Publisher、coordinator、四 lanes，Capacity Guard另列為 `CAPACITY_GUARD_LABEL`（`scripts/pantheon_content_capacity_guard.py:36-44`）；preactivation 的 live loop則使用正式 manifest 的七服務清單（`scripts/pantheon_content_capacity_guard.py:732-737`）。

red-capable 唯讀重播對 live Publisher 呼叫 `plist_receipt(..., expected_activation_mode="activation-only")`，精確在 `scripts/pantheon_content_runtime_manifest.py:376-377` 重現 `plist activation mode mismatch`。錯誤字串沒有 label/path，這是 local diagnostic contract缺口，但 mismatch 本身已由循序與單服務重播定位。

## B. Transition authority 是否錯位

### Observed contract

1. Capacity installer先產生 **normal** candidate，執行 raw preflight；若 stage controls存在，即使 raw preflight nonzero仍進入 preactivation transition（`scripts/install_pantheon_content_capacity_guard_launchd.sh:115-175`）。
2. preactivation transition將 target manifest、barrier、stage digest／generation、Publisher max-runs=1／exact-run 綁在一起（`scripts/pantheon_content_capacity_guard.py:670-702`）。
3. staged Publisher由專用 preflight驗 normal exact-run，其餘 staged services與 Capacity candidate驗 normal且對 target manifest receipt（`scripts/pantheon_content_capacity_guard.py:698-728`）。
4. live 七服務另驗 activation-only、同一個 **old-live aggregate**、loaded/no-PID與 plist path；它沒有要求 old live等於 new staged target（`scripts/pantheon_content_capacity_guard.py:732-810`）。
5. 另一個 dry reconciliation authority `scripts/pantheon_g8_production_preactivation.py:291-353` 只讀七份 live/staged JSON receipts，要求各 cohort內部一致、old live不等於new stage、staged actor head與exact-run selector正確；它不讀 plist activation mode、launchctl topology或PID。因此它可與 Capacity transition得到不同結論。

### 判定

Capacity transition **沒有**錯把新 staged cohort與舊 live cohort做 equality；其 old-live/new-stage分離本身合理。實際錯位在 orchestration authority：Publisher-only canary會把 Publisher轉成 normal one-shot並只替換 Publisher（`scripts/install_agy_gemini_coordinator_launchd.sh:658-714`），而 preactivation要求下一輪開始前七個 live services已全為 activation-only。把 Publisher收回 activation-only的唯一正式 authority是 `--reset-publisher-activation-only`（`scripts/install_agy_gemini_coordinator_launchd.sh:425-655`），但 Cycle 32 流程在 Capacity gate前沒有執行該 transition。

該 reset authority並非盲改：它要求 matching target stage、接受舊 live Publisher normal one-shot或scheduled、核對它與舊 live coordinator identity，再轉為 activation-only；其他 coordinator／lanes／Capacity必須 activation-only、同舊 identity、loaded/no-PID、path正確（`scripts/install_agy_gemini_coordinator_launchd.sh:439-578`）。因此正確修復方向不是降低 Capacity expected string或手改 live plist，而是把「terminal Publisher → old-live all activation-only」提升為下一輪 preactivation的顯式、可證明 transition。

完整目標順序應是：

`promote target → private-stage six → formal reset old live Publisher → Capacity preflight/stage seventh → activate-only target seven → restage target Publisher exact-run → phase-bound readiness + Rule25 + approvals → Publisher-only canary → post-canary terminal/reset or rollback`

`--activate-only` 會替換、bootstrap七個 live plists並刪除 stage（`scripts/install_agy_gemini_coordinator_launchd.sh:1383-1451`），所以 exact-run Publisher必須在此後重建 private stage；若沿用 activation前的 stage receipt，就是另一個可預測 blocker。

## C. coordinator loaded/no-PID 是否合法

**合法，而且此 phase 是必要狀態。** Preactivation要求七服務皆可被 `launchctl print` 找到、top-level state為 `not running` 或 `waiting`、沒有正 PID、path精確指向 live plist、exit code為 absent／0／78（`scripts/pantheon_content_capacity_guard.py:796-810`）。Publisher reset也要求其他六服務 loaded/no-PID（`scripts/install_agy_gemini_coordinator_launchd.sh:540-578`）。

Capacity raw RSS sampler有兩個合法 no-PID分類：正式 activation-only inert，或 manifest-bound normal scheduled idle；否則回 `loaded_service_pid_missing:<label>`（`scripts/pantheon_content_capacity_guard.py:254-381`）。Cycle 32 target是 config v3，但 `_activation_only_service_labels` 將合法 activation-only硬綁 `config_version == formal-runtime-v2-gate2`（`scripts/pantheon_content_capacity_guard.py:137-146`），因此沒有把 coordinator列入 expected inert，raw receipt才成為 `rss_available=false`／`rss_telemetry_unknown`。

接著 preactivation transition又把「唯一 reason為 rss unknown且 error為 loaded_service_pid_missing」當特殊可接受輸入（`scripts/pantheon_content_capacity_guard.py:645-669`），再自行證明 no-PID拓撲。這形成雙重 truth：raw Capacity／Rule 24 說 telemetry unknown必須 NO-GO，transition卻把同一 NO-GO當可繼續的 phase token。

正確 telemetry authority應在識別出可信、loaded、inert、no-PID topology後，將該服務 RSS視為已知 0（或明確的 non-running measurement），而非先產生 `rss_telemetry_unknown` 再由下游例外放行。PID只有在 CANARY 的 Publisher one-shot實際執行窗口才預期短暫存在；PREACTIVATION與 ACTIVATION-ONLY的 children均不應有 PID。

## D. Remaining Gate Dry Reconciliation

| Gate | Expected inputs | Current evidence | Missing evidence | Known mismatch | 結果 | Reason |
|---|---|---|---|---|---|---|
| 1. Capacity public preflight | raw Capacity receipt、target manifest/barrier、old-live七服務AO/no-PID、target staged七服務normal | Cycle 32正式 receipt：raw RSS unknown，transition在 Publisher mode失敗；Cycle 32 digest見上 | 無 | live Publisher normal；config-v3 inert辨識失效 | **BLOCKED** | 已有 deterministic red evidence，不需再碰 production |
| 2. Capacity staged coherence | target controls、Publisher exact-run max1、六 staged normal、Capacity candidate normal | Cycle 32六 staged與synthetic Capacity PASS；正式 run在寫入 Capacity stage前 fail closed並rollback | target G34 Capacity staged receipt不存在，且不應被偽造 | 前置 live transition未收斂 | **BLOCKED** | candidate contract可通過，但 seventh stage未被正式授權寫入 |
| 3. current synthetic readiness | current target的 capability/capacity evidence、identity/digest continuity、negative proof | Cycle 31 fixtures曾 PASS，但僅 historical；source gate可重播 | current G34 package與current target receipts | readiness不讀 live/staged mode | **BLOCKED** | current-target evidence不存在；Cycle31不可代用 |
| 4. seven-capability receipt | create→run→select→publish→transaction→tag→push，非 production mode、同 correlation/identity | focused fixture E2E PASS；`scripts/pantheon_content_capability_receipt.py:23-33,150-229` | current G34七步 receipt | receipt不含 plist/launchctl/phase | **BLOCKED** | fixture證明 schema，不證明 current target |
| 5. Rule 25 official gate | 七步 receipt、evidence path/outcome、correlation與identity | official gate focused test PASS；Rule25 source另要求 Capacity與production approvals | current G34 official receipt與獨立 approvals | thin gate不驗 artifact內容、plist phase或generation | **BLOCKED** | 即使 fixture READY也不能覆蓋 Capacity blocker |
| 6. negative fixture | identity/digest/provenance drift必須 fail closed | adversarial fixture證明 repo packager BLOCKED，但薄 official gate可仍回 READY（`tests/test_pantheon_writer_vnext_runtime_activation_readiness.py:127-158`） | current G34 negative receipt | official gate的 provenance gap已被fixture揭露 | **BLOCKED** | negative evidence揭示 gate split，不能給 current authorization |
| 7. Publisher activation-only readiness | live target七服務AO、matching aggregate/barrier；target staged Publisher normal exact-run max1 | current live Publisher normal且absent；其餘六AO/no-PID | formal reset receipt、target七服務 activation-only aggregate、activation後重建的 Publisher stage | state尚在 POST-CANARY/terminal mixed cohort | **BLOCKED** | `--activate-publisher-only` 的 live aggregate check會先拒絕（`scripts/install_agy_gemini_coordinator_launchd.sh:702-714`） |
| 8. exact-run canary prerequisites | gates 1–7、one-shot Publisher、exact-run id、transaction/tag/push capability、Capacity與production approvals | exact-run selector `auto-i18n-en-614aa4dc3542ab2c5637` 在 rollback stage controls可讀；focused selectors PASS | phase-bound current target receipts、七服務 activation-only live、重建後Publisher stage、正式 approvals | upstream transition與authority chain未閉合 | **BLOCKED** | exact-run字串存在不等於可 canary |

以上沒有以 `UNKNOWN` 代替可判定事項：所有 current gates均因可識別的缺件或 mismatch而 fail closed。未執行 production gate不是證據缺失，而是本卡明示禁止且現有 blocker已足以判定 BLOCKED。

## E. Transition state table

縮寫：`AO` = activation-only；`N-S` = normal scheduled；`N-1` = normal one-shot；`C/L` = coordinator＋four lanes；`P` = Publisher；`CG` = Capacity Guard。`—` 表示該 phase不應存在該 copy／process。

| Phase / group | plist exists | mode | RunAtLoad | StartInterval | KeepAlive | loaded | PID expected | child allowed | receipt authority | mutation authority |
|---|---|---|---|---|---|---|---|---|---|---|
| CURRENT LIVE / C/L | yes | AO（observed） | true | 60 | absent | yes | no | no | live plist receipt + launchctl identity | previous aggregate activation |
| CURRENT LIVE / P | yes | **N-S（observed）** | true | 60 | absent | no | no | no | live Publisher receipt + launchctl absence | previous Publisher-only canary/terminal state |
| CURRENT LIVE / CG | yes | AO（observed） | true | 300 | absent | yes | no | no | live plist receipt + launchctl identity | previous aggregate activation |
| PRIVATE STAGED / C/L | yes, stage only | N-S | true | 60 | absent | no | no | no | target manifest aggregate receipt | coordinator installer `--install` |
| PRIVATE STAGED / P | yes, stage only | N-S exact-run | true | 60 | absent | no | no | no | Publisher plist + max-runs/exact-run controls | Publisher installer private-stage |
| PRIVATE STAGED / CG | candidate/stage only | N-S | true | 300 | absent | no | no | no | Capacity candidate receipt | Capacity installer（只在transition PASS後寫stage） |
| PREACTIVATION / C/L | live old + staged new | live AO / stage N-S | true | live 60 / stage 60 | absent | live yes | no | no | Capacity transition old-live aggregate + target stage | no mutation；先前aggregate activation |
| PREACTIVATION / P | live old + staged new | **live須AO** / stage N-S exact | true | live可保留60 / stage60 | absent | live yes | no | no | formal reset receipt + Capacity transition | `--reset-publisher-activation-only` |
| PREACTIVATION / CG | live old + candidate new | live AO / candidate N-S | true | 300 | absent | live yes | no | no | Capacity transition | Capacity installer只可在PASS後stage candidate |
| ACTIVATION-ONLY / C/L | live target yes | AO | true | 60（保留但child由barrier抑制） | absent | yes | no | no | target live aggregate + launchctl + barrier | aggregate `--activate-only` |
| ACTIVATION-ONLY / P | live target yes | AO | true | 60（之後另建N-1 stage） | absent | yes | no | no | target live aggregate + launchctl + barrier | aggregate `--activate-only` |
| ACTIVATION-ONLY / CG | live target yes | AO | true | 300（child受抑制） | absent | yes | no | no | target live aggregate + launchctl + barrier | aggregate `--activate-only` |
| CANARY / C/L | live yes | AO | true | 60 | absent | yes | no | no | live aggregate + barrier | 不變 |
| CANARY / P | live yes | N-1 exact-run | true | absent | absent | yes during launch | transient one PID | **only exact-run child** | Publisher-only activation + run/transaction chain | `--activate-publisher-only` |
| CANARY / CG | live yes | AO | true | 300 | absent | yes | no | no | Capacity approval + live aggregate | 不變 |
| POST-CANARY / C/L | live yes | AO | true | 60 | absent | yes | no | no | launchctl + live receipt | 不變 |
| POST-CANARY / P | live yes | N-1 terminal（或既有N-S legacy terminal） | true | absent（目前實際仍60） | absent | absent或loaded/no-PID | no | no | terminal/reset receipt | reset authority待下一輪執行 |
| POST-CANARY / CG | live yes | AO | true | 300 | absent | yes | no | no | launchctl + Capacity receipt | 不變 |
| ROLLBACK / C/L | previous snapshot | snapshot-defined | snapshot | snapshot | snapshot | previous loaded state | snapshot-defined，復原後須再驗 | 只依previous barrier | rollback bundle/identity files | installer rollback trap |
| ROLLBACK / P | previous snapshot | snapshot-defined | snapshot | snapshot | snapshot | previous loaded state | snapshot-defined | 不新增child | rollback receipt | installer rollback trap |
| ROLLBACK / CG | previous snapshot | snapshot-defined | snapshot | snapshot | snapshot | previous loaded state | snapshot-defined | 不新增child | rollback receipt | installer rollback trap |

### Phase definition衝突

1. **Capacity raw preflight vs Capacity transition**：raw preflight因合法 no-PID回 RSS unknown/NO-GO；transition卻以 `preflight_pid_gap` 例外接受同 receipt。這直接違反單一 Capacity truth，並與 Rule 24「unknown RSS即NO-GO」語義衝突。
2. **Current readiness／Rule25 vs runtime transition**：capability/readiness驗七步與identity continuity，但沒有 live/staged plist、activation mode、loaded/PID、Capacity seventh stage或phase欄位；因此 synthetic READY可與 Capacity BLOCKED同時成立。readiness source自身用 adversarial fixture記錄薄 gate provenance gap。
3. **Publisher post-canary vs下一輪 preactivation**：Publisher-only authority合理產生 terminal normal Publisher；Capacity合理要求下一輪 old live全AO；但 orchestration沒有把 reset作為 promotion與Capacity間的必備、可攜 receipt edge。

因此結論為 **`ARCHITECTURE CONTRACT MISMATCH`**，不是單一 plist validation bug。

## F. Production vs fixture semantic gaps

| 面向 | 已覆蓋 | 未覆蓋的 production semantics | 可能後續 blocker |
|---|---|---|---|
| fake launchctl | loaded/absent、PID、path、exit 0/78、rollback mutation counts | 真實 `launchctl print`巢狀輸出、race、bootstrap後短暫state；parser只接受純數字 `last exit code`（`scripts/pantheon_content_capacity_guard.py:48-51`），macOS可顯示 `78: EX_CONFIG` | 真實 exit被解析成 absent；可能誤接受或誤拒絕 |
| `tmp_path` | staged/live layout與canonical reset unit tests | `tmp_path`天然canonical且同一測試filesystem，未代表 ambient TMPDIR symlink、APFS path alias、權限／owner | Capacity installer仍以 `${TMPDIR:-/tmp}` mktemp，與Publisher reset canonicalization不對稱 |
| symlink/canonical path | Publisher terminal reset有 ambient TMPDIR alias focused test（`tests/test_agy_gemini_coordinator.py:5839-5935`） | stage dir、launchctl reported path、manifest roots跨symlink/realpath組合未形成整鏈fixture | 下一個 stage/live path equality blocker |
| loaded service | fake可指定loaded/no-PID及absent | 真實 launchd demand state、waiting/not running切換、service cache與plist replacement時間窗 | transition在合法 transient state fail closed |
| PID/RSS | activation-only no-PID、normal scheduled transient recheck/persistent gap tests（`tests/test_pantheon_content_capacity_guard.py:1535-1765`） | target config版本變更時phase辨識；process exit與RSS sample競態 | raw RSS unknown再次先擋住 |
| activation mode | normal/AO receipt正反測試、unsafe live reject | 通用錯誤不含service/path/actual；未有「Publisher normal、其他六AO」production-shaped全鏈 fixture | 修一個mismatch後才看到下一個服務或stage blocker |
| staged/live transition | G5/G6 old-live/new-stage fixtures、Publisher-only與aggregate activation rollback tests | 沒有把 post-canary mixed cohort → formal reset → Capacity seventh stage → activate-only刪stage → restage exact-run串成一個fixture | stale stage、缺Capacity stage或Publisher-only aggregate fail |
| readiness/Rule25 | capability正向、fail-closed負向、adversarial thin-gate red | 不綁 phase、plist digest、launchctl topology、target generation與Capacity receipt內容 | official READY與runtime BLOCKED並存 |

Focused tests證明的是 fixture contract，不是 production readiness。特別是 Cycle 29 historical RESULT（SHA-256 `b9157f9ed53f38af3acc33f5dd89be1dd0f99d07fdf2b1c34216c23acee4d12e`）證明 G23 all-AO/no-PID phase曾可通過 Capacity；它不能證明 G34 current target。Publisher final-ship RESULT（SHA-256 `5cbf6a35d5623c1516b6137c3fa2910e76fe36ad96b8f0885fc1d5610050f8c0`）則與直接觀察一致：Publisher terminal normal、其他服務AO，是這次 mismatch的歷史來源。

## 後續 blocker預測

依目前 authority順序，若只局部繞過 Publisher mode，後續最可能依序出現：

1. config-v3 activation-only仍被 raw Capacity誤判為 RSS unknown，繼續依賴 `preflight_pid_gap`例外。
2. Capacity seventh staged receipt缺失，因正式 installer尚未通過 transition。
3. aggregate `--activate-only` 成功後會刪除 stage；若沒有重建 Publisher exact-run private stage，Publisher-only activation缺 stage controls。
4. current synthetic readiness、七步 capability與Rule25 current receipt仍缺；Cycle31不得補位。
5. official Rule25薄 gate即使READY，仍可能未綁target phase、live plist與Capacity receipt provenance。
6. 真實 launchctl `last exit code = 78: EX_CONFIG`與瞬時state可能暴露fixture parser差異。

這些是 source/receipt推論，不是已執行 production結果；沒有以推論宣稱 PASS。

## 唯一下一步 repair-card 建議範圍（只建議，不建立、不執行）

建議唯一 scope：**G8 PRE-CANARY PHASE-BOUND TRANSITION CONTRACT REPAIR**。

此卡應一次完成但仍保持一個垂直範圍：定義一份 phase-bound transition receipt，將 `post-canary mixed live → Publisher formal reset → old-live all-AO/no-PID → target seven-stage normal → target all-AO → exact-run Publisher restage` 串為同一 generation/correlation 的 authority；使 config-version-independent 的 activation-only辨識把已證明 inert no-PID計為已知零RSS，移除下游對 raw NO-GO 的 `preflight_pid_gap`語義豁免；將 per-service/path/expected/actual寫入錯誤；readiness/Rule25必須驗該 receipt digest與 phase。fixture須加入真實形狀 `launchctl` exit字串、canonical/alias TMPDIR、mixed old-live、stage deletion/restage與全鏈 fail-closed測試。該 repair card本身不得執行 production reset、activation或canary。

## 診斷命令、驗證與未執行項

執行類別：

- `worktree_capability_preflight.sh --prepare --with-codegraph`：一次，PASS；之後查詢 Capacity transition、activation authority、PID/RSS、readiness、Rule25、Publisher activation-only、exact-run prerequisites。
- 限域 `rg`／`sed`／`git show`／SHA-256：讀 task card、Cycle32/31、TMPDIR repair/review、Cycle29、Publisher final ship、Capacity/readiness/Rule25/preactivation source與tests。
- `plist_receipt(... expected_activation_mode="activation-only")` 對 live Publisher唯讀重播：FAIL as expected，`plist activation mode mismatch`。
- 唯讀 `PlistBuddy`／`launchctl print`：確認 Publisher normal且absent；coordinator、四 lanes、Capacity AO且loaded/no-PID。
- focused fixture suite：`32 passed, 346 deselected in 40.76s`。涵蓋 Capacity G5/G6 transition、PID/RSS、unsafe normal live、Publisher reset canonical TMPDIR、Publisher-only activation、readiness/Rule25 adversarial gate、capability E2E與old-live/new-stage exact selector。
- 未建立 diagnostic script。

明確未執行：public production gate重跑、production reset、Capacity install、Publisher activation、canary、launchctl mutation、live/staged plist mutation、actor/manifest/queue/state mutation、evidence deletion、tag、push、deploy、schedule。

## Commit 與 cleanliness

- 唯一 commit full SHA：commit不能在自身 tree內容內自我引用其最終SHA；authoritative full SHA由交付訊息與 commit後 `git rev-parse HEAD` 提供。
- commit內容：只含本 RESULT。
- final worktree status：commit後以 `git status --porcelain` 驗證 clean；authoritative輸出由交付訊息提供。
