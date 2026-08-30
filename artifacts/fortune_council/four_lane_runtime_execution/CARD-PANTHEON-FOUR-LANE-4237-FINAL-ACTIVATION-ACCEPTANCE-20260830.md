# Pantheon 四線 4237 最終 Activation Acceptance 卡

status: `READY_FOR_OWNER_AUTHORIZATION`
execution_line_id: `PANTHEON-FOUR-LANE-4237-FINAL-ACTIVATION-ACCEPTANCE`
authorized_base_sha: `4237d7c28274ea3373079f1504c3e22d400f0648`
accepted_code_review: `GO`
operation_now: `DOCUMENT_ONLY`

## 1. 任務目的

以單一、順序式、fail-closed 的 production authority envelope，將已接受的 exact revision `4237d7c28274ea3373079f1504c3e22d400f0648` 提升為目前唯一 production actor，完成唯一仍缺的 `i18n-rewrite` fresh business E2E，啟用七個正式服務，並證明四條 lane 在 current actor 下 selector、routing、idle 與 auto-stop 契約均有效。

本卡不是四條 lane 全部重跑。`new`、`rewrite`、`i18n-new` 沿用既有 production publication receipts；三線不得產生新文章、不得重新呼叫 Writer／Reviewer、不得重新發布。唯一 fresh business E2E 是：

`i18n-rewrite` → repaired EN candidate → approved revision stage → exact publisher transaction → release/tag/push → public URL HTTP 200 且 rendered body 正確。

## 2. 當前事實與根問題

### 2.1 已接受程式版本

- exact revision：`4237d7c28274ea3373079f1504c3e22d400f0648`
- parent：`e01d56e3847600fa8723a006b3f16e3757af7610`
- commit subject：`fix: publish approved locale replacements safely`
- accepted code review：`GO`
- Repair 已通過受影響測試、`py_compile` 與 `git diff --check`；本卡不得重開 Repair finding。

### 2.2 根問題

不是四線業務結果全部失效，而是：

1. `4237` 尚未取得 fresh production promotion authority；舊 `g75` manifest 屬於 `e01`，不得沿用。
2. `i18n-rewrite` 的 repaired EN candidate 已獲 Formal Reviewer 批准，但尚未在 production 完成 stage／publisher／release／public acceptance。
3. 七服務尚需以同一個 `4237 + fresh manifest + fresh generation` cohort 啟用並驗證。
4. 其他三線只需 current-actor control-plane smoke 與既有公開頁 recheck，不需 fresh 內容 E2E。

## 3. 唯一 authority envelope

本卡所有 mutation 必須在 Owner 對本卡明確授權後，依 Phase 0 → 6 順序執行。每一 Phase 的 receipt 是下一 Phase 的必要輸入；不得跳步、平行 production mutation、跨卡補洞或一邊執行一邊重新定義 target。

本卡授權時應一次鎖定以下 exact target：

- source／promotion target：`origin/main@4237d7c28274ea3373079f1504c3e22d400f0648`
- replacement run：`auto-i18n-en-aa637e1bf05d3ad21429-replacement-01`
- article identity：`ASTRO-BASE-03:en`
- source article：`ASTRO-BASE-03`
- source path：`/articles/astrology/astrology-0003`
- repaired candidate file：`artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-EN-I18N-REWRITE-CONTENT-REPAIR-20260830/candidate-repaired.json`
- repaired candidate file SHA-256：`26dd6ccf15a37a165f2ec11f9dd0220db26b9cdbc7fc8b2641b50b551e6731d1`
- Formal Reviewer job：`af0a7de946841d3e899f7b7aeb8c3993762775d3`
- Formal Reviewer verdict：`APPROVE_READY_FOR_STAGING`
- expected public URL：`https://www.mysticpantheon.com/en/articles/astrology/astrology-0003`

## 4. 可沿用 evidence

### 4.1 三條 lane 的既有 business receipts

| lane | 可沿用 production outcome | carry-forward 條件 | 本卡 fresh 內容 mutation |
|---|---|---|---:|
| `new` | run `v0391-publish-canary-20260826-02`；article `V2-TAROT-DEATH-MONEY`；Reviewer APPROVE；release `v0.3.371`；public URL `https://www.mysticpantheon.com/articles/tarot/tarot-1884` | `4237` diff 未觸及其 candidate/review/publish path；current-actor routing smoke與公開頁 identity recheck PASS | `0` |
| `rewrite` | run `legacy-auto-sweep-v1-astrology-0002-astro-base-02`；article `ASTRO-BASE-02`；Reviewer APPROVE；release `v0.3.372`；public URL `https://www.mysticpantheon.com/articles/astrology/astrology-0002` | `4237` diff 未觸及 monolingual rewrite outcome；current-actor routing smoke與公開頁 identity recheck PASS | `0` |
| `i18n-new` | run `auto-i18n-ja-1414b75a404721e95e74`；Formal Reviewer APPROVE；release `v0.3.374`；public URL `https://www.mysticpantheon.com/ja/articles/tarot/tarot-1884` | publication receipt直接 carry forward；current-actor strict brief/routing smoke與公開頁 identity recheck PASS | `0` |

### 4.2 `i18n-rewrite` 可沿用但不等於 published 的 receipts

- g75 automated replacement lifecycle已正式終止於三代 Reviewer REJECT；沒有 Gen04、沒有 publish、queue terminal state可追溯。
- bounded manual content repair已產生唯一 repaired candidate。
- Formal Reviewer已以 exactly-one provider call審查該 candidate，結果 `APPROVE_READY_FOR_STAGING`、findings `[]`。
- accepted `4237` Repair已提供 replacement attempt lifecycle、exact existing-locale in-place update、`PUSH_PREPARED`、partial remote edge convergence、ledger/evidence finalization與 idempotent replay seam。
- 以上只授權 exact candidate進正式 stage／publish transaction；不能冒充 production publication receipt。

### 4.3 不可沿用的 evidence

- `e01/g75` actor、manifest、generation、Rule24 或 Rule25 receipt 不得作為 `4237` 的 current runtime authority。
- g75 EN lifecycle的三次 REJECT不得冒充目前 repaired candidate的 APPROVE。
- public article目前存在不得冒充 `4237` replacement transaction已完成。
- 任一 isolated fixture、dry-run、test或 code-review GO不得冒充 production mutation成功。

## 5. Phase 0：Immutable current authority snapshot

### 5.1 只讀前置

在任何 production、LaunchAgent、provider、Git remote或 public content mutation前，建立 immutable snapshot，至少包含：

- `origin/main` exact SHA，必須為 `4237d7c28274ea3373079f1504c3e22d400f0648`。
- promotion source worktree exact HEAD、tracked cleanliness、canonical repo root。
- live actor SHA、runtime generation、runtime manifest digest、runtime digest、private stage/barrier identity。
- 七個 LaunchAgent 的 loaded／unloaded狀態、plist canonical path、actor root、manifest digest、selector與 model route。
- production queue四 lane的 outbox／processing／inbox摘要與 digests。
- replacement run registry、attempts `01/02/03`、repaired candidate、Formal Reviewer artifacts、stage receipt、publisher ledger、publish evidence與 unresolved `PUSH_PREPARED` 狀態。
- target public locale module的 old record/module digest與 public registry first-match owner。
- remote `origin/main`、目標 release tag namespace與既有 relevant tags。
- production content、registry、queue、ledger、manifest與 service plist protected-byte inventory。
- host free space、project bytes/file count、RSS、swap、capacity monitor狀態。

### 5.2 Phase 0 PASS

- 所有 authoritative identity唯一且可交叉驗證。
- replacement run仍為 exact source／generation／attempt lineage，沒有 attempt04、第二 replacement或其他 candidate owner。
- Formal Reviewer artifact、candidate file SHA與 run/article/source identity完全匹配。
- production queue沒有未知 active/processing job會在服務載入後被意外消耗。
- 沒有不屬於 exact transaction的 unresolved push或 partial remote state。
- `origin/main`、source HEAD或 protected bytes任一漂移即停，不得自動吸收新 SHA。

Phase 0 receipt 必須原子寫入本卡專用 evidence root；後續每個 Phase 引用該 digest，不得覆寫。

## 6. Phase 1：Fresh promotion of exact 4237

只沿既有正式 promotion `plan → apply → finalize → status` seam，將 exact `4237` 提升為新的 production actor、manifest與 generation。

硬條件：

- promotion source只能是 clean、canonical、exact `4237`。
- 新 generation名稱由正式入口形成，不在卡片預猜或手建。
- target actor、manifest digest、runtime digest、stage acknowledgements、activation barrier必須全部由同一 promotion plan導出。
- `e01/g75` manifest 只作歷史 before evidence，不得 copy、rewrite 或沿用為新 authority。
- preserved queue/run identity 必須與 Phase 0 完全一致；promotion 不授權清 queue、改 registry、改 candidate 或發布內容。
- status 必須為正式 `COMMITTED/PASS`，且 live actor、manifest、stage 與 barrier 一致，才可進 Phase 2。

## 7. Phase 2：Fresh Rule24／Rule25

### 7.1 Rule24 storage capacity safety

以 fresh `4237 + 新 manifest + 新 generation + 七服務 cohort` 重新產生 capacity receipt。至少證明：

- 所有正式寫入路徑已登記。
- `max_bytes`、`max_file_count`、增長率、尖峰視窗、回收時間、保留／輪替與 cleanup allowlist完整。
- host free space高於啟動門檻，峰值後仍保留 `max(20 GiB, 10%)`。
- 兩個代表性完整週期、回收驗證與停損演練均有 evidence。
- 啟動後監控頻率、停止指令與只停止 Pantheon肇因服務的 auto-stop path已驗證。

Rule24 唯一合法結果：`PASS`。未知欄位、未登記寫入、容量不足、RSS/swap 異常或停損未驗證均為 `NO-GO`。

### 7.2 Rule25 production canary readiness

以 current `4237` 正式入口建立 fresh capability receipt，逐步覆蓋：

`create → run → select → publish → transaction → tag → push`

每一步必須有正式入口、I/O、identity/correlation、PASS 正向 artifact 與 BLOCKED fail-closed artifact；七步 correlation 連續。receipt 產生時 `canary_created=false`。Gate 必須回 `READY`。

Rule25 READY 只證明 capability，不授權內容 mutation；Phase 3 仍以本卡 exact Owner authorization、candidate／Reviewer identity 與 publisher selector 約束。

## 8. Phase 3：Exact repaired EN replacement transaction

七服務在此 Phase開始前維持 unloaded或正式隔離，避免 scheduler消耗任何非 exact work。只允許正式 operator入口處理：

- run：`auto-i18n-en-aa637e1bf05d3ad21429-replacement-01`
- article：`ASTRO-BASE-03:en`
- candidate file SHA：`26dd6ccf15a37a165f2ec11f9dd0220db26b9cdbc7fc8b2641b50b551e6731d1`
- Formal Reviewer job：`af0a7de946841d3e899f7b7aeb8c3993762775d3`
- verdict：`APPROVE_READY_FOR_STAGING`

順序：

1. stage plan-only：write set、terminal owner=`replacement_attempt`、attempt lineage、public replacement descriptor與 old/new digests全部唯一。
2. stage execute：receipt-first；只原位替換 `ASTRO-BASE-03:en` 既有 locale record，manifest bytes、registry order、siblings與其他 locale bytes不變。
3. publisher preflight／plan-only：selector 必須 exactly one；release version/tag 由正式入口產生，禁止手猜或重用既有 tag。
4. publisher execute：沿 MutationJournal、`PUSH_PREPARED`、atomic Git commit/tag/push、existing `translation_published_runs` ledger與 atomic evidence順序完成。
5. execute後再次驗證：remote main/tag同指 target commit、ledger exactly one、publish evidence exact、PREPARED已清除。

允許的 crash recovery 僅限 `4237` accepted seam 的 closed matrix：

- PREPARED後，remote只缺 main或只缺 tag：只補 exact missing edge。
- remote兩邊皆 target但 ledger缺失：零push，只 finalize exact ledger/evidence。
- ledger exact但 evidence缺失：零 content／queue／ledger／Git／network mutation，只補 atomic evidence並清 exact control。
- ledger/evidence皆 exact：`ALREADY_PUBLISHED`，零寫。
- local commit/tag後、PREPARED前：fail closed、remote calls=0；不得自動 fetch/reconstruct。

本 Phase provider／Writer／Reviewer calls 必須全部為 `0`；不得建立 Gen04 或第二 replacement。

## 9. Phase 4：Public URL acceptance

只有 Phase 3 的 remote commit/tag、ledger與 publish evidence閉合後，才可驗收：

`https://www.mysticpantheon.com/en/articles/astrology/astrology-0003`

必須同時保存：

- HTTP status `200`、final URL、headers與 response body。
- browser rendered DOM與 screenshot。
- exact canonical URL、locale=`en`、article identity=`ASTRO-BASE-03:en`。
- rendered title／H1與 approved candidate一致。
- 至少兩個可區分新舊內容的 approved-body sentinels可見。
- public page沒有取到舊 first-match record；public bytes／record digest可回鏈 Phase 3 sealed after state。
- browser console error與與本變更相關的 network failure為 `0`。

HTTP 200 單獨不算 PASS；必須是 rendered body 與 identity 一起成立。

同時唯讀 recheck三條 carry-forward URL的 HTTP 200、canonical與既有 body sentinel。任一漂移只讓該 lane降級為 `BLOCKED_CARRY_FORWARD_DRIFT`，不得在本卡直接為該 lane產文或發布。

## 10. Phase 5：七服務 activation

以 Phase 1同一個 `4237 + fresh manifest + fresh generation` cohort啟用且只啟用以下七個正式服務：

1. coordinator
2. `new` runner
3. `rewrite` runner
4. `i18n-new` runner
5. `i18n-rewrite` runner
6. publisher
7. capacity guard

Activation PASS 必須證明：

- 每個 plist皆為 canonical regular file、owner/mode符合既有 guard。
- plist actor root、manifest digest、runtime digest、generation與 Phase 1完全一致。
- seven-service aggregate count exactly `7`，無舊 cohort、duplicate label或 mixed actor。
- capacity guard先於或與內容服務按正式安全順序生效；任一 capacity NO-GO時其餘服務不保持自動重啟。
- registry、queue與 published content不因 service install/load被改寫。
- rollback／unload只針對本 cohort，且有 dry evidence與可核對順序。

## 11. Phase 6：四 lane current-actor smoke

本 Phase只驗證控制面，不建立文章。對四條 lane各產生 current-actor receipt，證明：

- coordinator selector把 lane映射到唯一正確 runner／queue namespace。
- runner、publisher與 capacity guard都引用同一 `4237` manifest/generation。
- 空 queue 時服務保持合法 idle，不建立 candidate、Reviewer job、release 或 publication。
- exact selector沒有 cross-lane claim；不存在 ambiguous或 duplicate claim。
- provider／Writer／Reviewer／Publisher business calls均為 `0`。
- 未受影響三線的既有 run／ledger／public content bytes不變。
- capacity或 identity stop condition的正式 fail-closed smoke只停止肇因 cohort／阻止新 claim，不清資料、不碰其他專案。
- stop 後可依同一 manifest 安全回到 loaded/healthy/idle；最終七服務狀態、PID／label、last-exit 與 readiness 必須有 aggregate receipt。

不得向任一 lane 注入新的 production 文章作 smoke；Rule25 synthetic／dry capability evidence 與 current empty-queue actor smoke 足以驗控制面。

## 12. 全域 stop conditions

任一條成立立即停止當前與後續 Phase，保留原始 bytes／receipt，狀態只能報 `BLOCKED` 或 `NO-GO`：

- `origin/main`、source HEAD、accepted SHA、actor、manifest、generation、runtime digest或 protected bytes漂移。
- 需要第二個 source seam、第三個 authority owner、新 ledger／FSM／DB／overlay、public loader precedence或新的 Repair。
- 需要手改 registry、queue、manifest、plist、ledger、tag、Git refs或 production content。
- replacement identity、candidate SHA、Formal Reviewer job/verdict、attempt lineage或 public replacement owner不唯一。
- 出現第二 replacement、attempt04、Gen04、額外 lane candidate、額外 Provider／Writer／Reviewer呼叫。
- 任何 `new`、`rewrite`、`i18n-new` fresh content generation、stage、publish或 release企圖。
- Rule24 不是 `PASS`、Rule25 不是 `READY`、host 容量／增長／RSS／swap／unknown path 觸發停損。
- stage或publisher selector不是 exactly one；old/new/module/manifest/ledger/evidence digest drift。
- remote 出現第三 SHA、wrong annotated tag object、tag collision、非 closed matrix 的 partial state 或需要 force push。
- public URL不是 HTTP 200、canonical/locale/article identity不符、rendered body仍是舊內容或正文不可見。
- 七服務不是 exact one cohort、出現舊 actor/mixed generation、duplicate label、cross-lane claim或無法自動停損。
- 同一 blocker第三次失敗；不得第四次重試或另開症狀 Repair。

遇到第二個 code seam 時，本卡不得自行修。必須停止並回報 exact last-good、first-bad、durable invariant、RED-capable evidence 與 mutation count。

## 13. 明確禁止

- 不沿用或改寫 g75 manifest為 `4237` authority。
- 不重跑四線 semantic canary；不讓三條 carry-forward lane重新產文。
- 不再呼叫 automated EN Writer／Reviewer；不建立 Gen04。
- 不刪 production residue、queue、ledger、PREPARED或 quarantine。
- 不猜 Job ID、release version、tag、commit、public owner或 timestamp。
- 不改 shared security guard、capacity runtime、publisher selector語意或 public registry precedence。
- 不以 HTTP 200、tag存在、push exit 0、service loaded或 status文案單獨宣稱完成。
- 不在同一工作中順便處理其他 PR、內容或架構 P1。

## 14. Evidence output contract

唯一 evidence root：

`artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-4237-FINAL-ACTIVATION-ACCEPTANCE-20260830/`

至少交付：

- `phase-0-current-authority-snapshot.json`
- `phase-1-promotion-plan.json`
- `phase-1-promotion-apply.json`
- `phase-1-promotion-finalize.json`
- `phase-1-promotion-status.json`
- `phase-2-rule24-receipt.json`
- `phase-2-rule25-receipt.json`
- `phase-3-stage-plan.json`
- `phase-3-stage-receipt.json`
- `phase-3-publisher-plan.json`
- `phase-3-publisher-result.json`
- `phase-3-remote-ledger-evidence-closure.json`
- `phase-4-public-en-http.json`
- `phase-4-public-en-rendered-validation.json`
- `phase-4-carry-forward-public-recheck.json`
- `phase-5-seven-service-activation.json`
- `phase-6-four-lane-current-actor-smoke.json`
- `protected-bytes-before.json`
- `protected-bytes-after.json`
- `mutation-accounting.json`
- `RESULT.md`

每個 command需保存 argv、cwd、exact actor/manifest identity、return code、stdout/stderr摘要與 artifact digest。不得把 secrets、tokens或完整環境變數寫入 evidence。

`RESULT.md` 最終只能使用以下狀態之一：

- `GO_FOUR_LANE_CURRENT_ACTOR_ACCEPTED`
- `NO_GO`
- `BLOCKED`

## 15. 最終驗收條件

只有以下全部成立，主線才可宣告四線 current actor acceptance完成：

- exact `4237` fresh promotion `COMMITTED/PASS`。
- fresh Rule24=`PASS`、Rule25=`READY`。
- EN `i18n-rewrite` exact repaired candidate完成 stage、publisher transaction、release/tag/push與 exactly-one ledger/evidence。
- EN public URL HTTP 200且 approved rendered body可見。
- `new`、`rewrite`、`i18n-new` receipts正式 carry forward，public recheck PASS，fresh內容 mutation均為0。
- 七服務同 cohort loaded/healthy，capacity guard與 auto-stop有效。
- 四 lane selector/routing/idle smoke PASS，cross-lane claim=0，額外 semantic/provider/reviewer/publisher calls=0。
- protected bytes變更只包含 exact EN locale replacement、正式 release metadata與本卡 evidence所允許集合；其他 queue/registry/content不變。
- git/remote/tag、runtime、ledger、service與browser evidence可互相回鏈同一 authority envelope。

任一條缺證據就不是完成；不得以 `PARTIAL`包裝為 GO。

## 16. 本卡建立時 mutation accounting

- production mutation：`0`
- network／provider call：`0`
- service load／unload：`0`
- source／test修改：`0`
- commit／tag／push：`0`
- 新文章／publication：`0`
- 唯一修改：本卡文件

## 17. Evidence index

- carry-forward matrix：`artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-CURRENT-REVISION-CARRY-FORWARD-MATRIX-20260830/RESULT.md`
- g75 EN replacement acceptance：`artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-E01-G75-EN-REPLACEMENT-ACCEPTANCE-20260830/RESULT.md`
- repaired candidate：`artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-EN-I18N-REWRITE-CONTENT-REPAIR-20260830/candidate-repaired.json`
- Formal Reviewer result：`artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-EN-I18N-REWRITE-FORMAL-REREVIEW-20260830/RESULT.md`
- replacement Repair result：`artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-APPROVED-LOCALE-REPLACEMENT-TRANSACTION-REPAIR-20260830/RESULT.md`
- replacement Repair review：`artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-APPROVED-LOCALE-REPLACEMENT-TRANSACTION-REPAIR-REVIEW-20260830/RESULT.md`
- Rule24：`<ai-core-root>/rules/24-storage-capacity-safety.md`
- Rule25：`<ai-core-root>/rules/25-production-canary-readiness.md`

## 18. 交付裁決

`READY_FOR_OWNER_AUTHORIZATION`

本卡只將既有 acceptance證據與剩餘 production gates收斂成單一 bounded execution line；尚未取得本卡 production mutation authorization，也未執行任何 promotion、capacity、provider、stage、publisher、Git remote、service activation或 browser acceptance。
