# Replacement approved revision lifecycle RCA 結果

## 唯一裁決

`FORMAL_MISSING_SEAM / NO_GO_SINGLE_LIFECYCLE_ADAPTER`

這不是 5704 的 continuation staging regression，也不是 Formal Reviewer、replacement bytes 或 shared publisher security guard 壞掉。`5704fa6077` 建立的 approved-revision seal 明確只覆蓋 continuation/generations；`d7b09a99bd` 後來建立 exact failed-translation replacement/attempts lifecycle，但沒有定義其 manual approved revision 如何取得 seal。更重要的是，沿 publisher 掃到底後還有第二個獨立缺口：現有 apply primitive 是 translation-create-only，對真正的 `i18n-rewrite` 既有 locale identity 必定拒絕。因此只加 lifecycle adapter 不能形成 public E2E，現在不得開一張「只修 staging」Repair。

## Last-good、formation 與 durable invariant

### Last-good A：continuation/generations

- code seam：`5704fa6077 fix: seal approved translation revisions for publish`。
- production proof：JA run `auto-i18n-ja-1414b75a404721e95e74` 的 Gen06 manual repair 經 seal/publisher 發布為 `v0.3.374`；release commit `22d7e21b7a3da4e8afffd58a76b2746bebad8b41`，staging receipt `9544705d7d8c92b370451bf8560aa9815699bfe3f67e9fa527c5e3d7b233d1a4`。
- authoritative terminal owner：`continuation/state.json` 鎖 root terminal candidate/review digests；`generations/06` 是 immutable generation audit；root candidate/review 是 terminal mirror；queue registry 與 publisher ledger提供 lifecycle/current locks。
- 此路徑仍合法，不能放寬其 `hard_failure=true`、next-generation absence 或 generation tree locks。

### Formation B：replacement/attempts

- `d7b09a99bd fix: add exact translation replacement planning` 建立 exact replacement；它從 eligible failed source run建立唯一 `-replacement-01`，而正常 fresh semantic lifecycle仍寫 `attempts/01..03`。
- current EN replacement 的 authoritative owner 是：registry `1bf0bbc61ff8d10e808f6923.json`（complete、replacement_of、replacement_reason）＋ `attempts/03` candidate/review/tree；root candidate/review是 attempts/03 terminal mirror。
- immutable identity：run id、replacement_of、replacement_reason、brief source article/locale/source SHA、attempts 01..03 contiguous tree、root/attempt03 digests、queue-state digest、Formal Reviewer job/request/candidate digests。
- current exact digests：root candidate `b9799d...1547`；root review `43ee5f...ae3`；registry `25e084...eeef`；approved candidate file `26dd6c...31d1`；approved article `7a63cb...8314`；approved review `abae91...b1a5`；formal result `1446c1...1e2c`。
- replacement terminal root review 是 ordinary `REJECT`／`SOURCE_SYNTAX_TRANSFER`，不是 continuation 專用的 `hard_failure=true`。

### Root classification

沒有可稱為「最後成功 replacement staging」的版本；該 combination 從未有 formal contract。因此主因是 `FORMAL_MISSING_SEAM`，不是把 d7 稱為破壞既有成功行為的 first-bad regression。d7 是首次讓缺口成為 production-reachable 的形成 commit。

## Downstream seam inventory

| Consumer | Hard binding／行為 | replacement 結果 |
|---|---|---|
| Stage planner | `scripts/agy_multilingual_pipeline.py:2864-2957` 無條件要求 continuation SHA、complete state、generations tree、terminal hard failure | 首個 blocker：missing `continuation/state.json` |
| Stage seal loader | `scripts/agy_multilingual_pipeline.py:3075-3146` seal schema與 current locks再次硬綁 continuation/generation fields | 即使偽造 plan也無法 load |
| Publisher selector | general exact `--exact-run-id`／`collect_ready_translation_runs` 可選 complete replacement；只有 exact-fresh-JA 特例拒絕 replacement | 可沿用，不需新 selector |
| Publisher collection | `scripts/agy_content_publisher.py:2843-2855` 載入 stage後再次無條件讀 continuation SHA | 必須改為驗證 seal 正規化後的 owner locks |
| Staged apply | `scripts/agy_content_publisher.py:4371-4407` 可沿用 approved review、approval、transaction journal與 staging receipt | 控制流可沿用 |
| Translation apply | `scripts/agy_multilingual_pipeline.py:4215-4231` 只有同 run id 才算 owned；任何既有 `(article, locale)` 都 fail `translation already exists` | 第二個 blocker；本案 `(ASTRO-BASE-03,en)` 已存在 |
| Public registry | `getArticleLocaleRecord` 使用 first-match；只追加新 module/spread 不能覆蓋舊 record | overlay workaround 無效 |
| Release／ledger | publisher transaction、tests、version、commit/tag/push、`staging_receipt_sha256` ledger entry不硬綁 continuation | 可沿用；不是新 seam |

既有 public owner 是 `article-locale-codex-emergency-i18n-20260726-astro-base-03.js` 中 run `codex-emergency-i18n-20260726-astro-base-03` 的 EN record，舊 source SHA `5a85b2...824`；current rewrite source SHA 是 `542e71...c77`。該 module 同時擁有 EN／JA／KO，現有程式沒有 deterministic、receipt-first、只替換單一 EN record的 writer/rollback contract。

## 逐項結果

- 檢查 1 Task 邊界：`PARTIAL`
  - 證據：Writer/Reviewer、manual candidate、Formal Reviewer、stage、publisher都是獨立入口。
  - 缺口：stage入口把「approved revision」與 continuation owner形狀黏死；i18n-rewrite apply又沒有獨立入口。
  - 建議：先定義 terminal authority union 與既有 locale replacement owner，再決定一張 E2E Repair；不得只改 CLI parser。

- 檢查 2 Input / Output 契約：`PARTIAL`
  - 證據：candidate/review/formal identity、seal、receipt、ledger均為 closed JSON/digest artifacts。
  - 缺口：seal schema只有 continuation fields；public locale既有 record沒有 replacement input/output receipt。
  - 建議：沿用同一 seal contract族，加入 closed `terminal_owner_kind` 與 owner-specific immutable digests；public replacement另需 exact prior-record/module digest與after digest。

- 檢查 3 可程式化成功標準：`PARTIAL`
  - 證據：Formal Reviewer APPROVE、deterministic translation findings、source drift、transaction/release tests皆為硬 gate。
  - 缺口：沒有「replacement attempts approved revision stageable」和「只替換既有一筆 locale、其他 bytes不變」的 validator/test。
  - 建議：先補兩段 provider=0 RED；不能以 Reviewer APPROVE代替 publication authority。

- 檢查 4 獨立 SOP / Skill 規範：`PASS`
  - 證據：內容修稿、Formal Reviewer、stage與publisher規則／artifacts可分別定位；沒有 mega-prompt取代硬閘門。
  - 缺口：跨 lifecycle integration contract未寫出。
  - 建議：只補 bounded contract，不新增常駐 governance。

- 檢查 5 控制流歸屬：`PASS`
  - 證據：Reviewer verdict、stage plan digest、publisher exact selector與transaction均由 deterministic code決定。
  - 缺口：控制流會在 staging fail closed；若只補 staging，會在 apply再次 fail closed。
  - 建議：保留 fail-closed順序，implementation前先證明完整 next-seam matrix。

- 檢查 6 失敗處理與回退：`PARTIAL`
  - 證據：stage receipt-first、idempotent、rollback；publisher mutation journal可回復；本次所有 failure在 mutation前停止。
  - 缺口：replacement-attempt沒有 stage rollback identity；既有三語 module中的單筆 EN replacement沒有 receipt-first rollback owner。
  - 建議：沒有兩者前保持 NO_GO。

## 試金石結果

- 單步隔離執行：`PARTIAL`。Formal Reviewer與 continuation stage可固定 input獨立執行；exact replacement stage以同一 production-shaped inputs穩定 RED。i18n-rewrite apply也可固定 input獨立重現第二個 RED，但沒有成功 primitive。
- 憑 trace 重建流程：`PASS`。可從 replacement registry、attempts/01..03、root mirror、manual repaired candidate、formal-request identity/result重建完整 trace；缺的是 stage/public replacement transaction，而不是觀測資料。

## Exact provider=0 RED

### RED 1：production-shaped staging

以 current production run、root digests、queue state、ledger、approved candidate/review/formal result執行正式 `stage-approved-edited-candidate` plan-only：exit `1`，精確首錯為 missing `<run>/continuation/state.json`。沒有 provider client、沒有 execute、沒有 editorial-staging、沒有 generations/04、outbox/processing仍為0。

### RED 2：all-next-seams apply scan

以同一 production brief、approved candidate/review、正式 approval gate與 production existing inventory identity，在 isolated temp root呼叫現有 `apply_approved_translations`：exit `1`，精確錯誤 `translation already exists: ASTRO-BASE-03:en`。provider=0、publisher transaction=0、production write=0。

這證明 lifecycle-neutral staging adapter本身不是 sufficient repair。

## Minimum sufficient 判斷

- why_not_less：只讓 `continuation_state_sha256` optional、複製 attempts到generations、補 `hard_failure=true`、或只在 publisher跳過 continuation lock都會偽造／削弱 authority，且仍會撞既有 locale collision。
- why_not_more：不需要新 registry、FSM、DB、publisher、模型 route、Reviewer、promotion、queue或通用 JS refactor；既有 exact selector、seal payload、transaction journal、release/ledger流程可保留。
- do_not_absorb：不要支援任意 lifecycle、任意 replacement chain、跨多 article/module migration、歷史 emergency content全面正規化、overlay precedence、掃描後猜 owner。

## Implementation frontier

`NO_GO_SINGLE_LIFECYCLE_ADAPTER`。

下一張不能叫「staging parser Repair」。在開 Repair 前必須先由主線裁決一個 bounded public replacement owner contract，至少同時鎖定：

1. terminal owner union僅允許 `continuation_generation` 或 `replacement_attempt`；後者要求 exact `replacement_of`、reason、contiguous attempts 01..03、root==attempt03 candidate/review、ordinary terminal REJECT/findings、無 attempt04／generations／continuation state。
2. 同一 approved revision seal／payload／rollback／Formal Reviewer identity被沿用，seal記錄 owner kind與 owner-specific tree/state digests；原 continuation branch語意完全不變。
3. i18n-rewrite public owner必須由 exact prior `(article_id, locale, runId, sourceSha256, module path/module digest)` 識別；只替換該 EN record，JA/KO及 manifest其餘 bytes/records保持；receipt-first且可 rollback。
4. publisher collect、apply、ledger、transaction測試要在同一 repair acceptance證明從 stage到 dry-run/execute/public artifact，否則仍 NO_GO。

若無法在既有 locale module writer上證明 exact owner與可回退的單筆替換，主線應保持 `NO_GO`，不得先修 staging再現場探索下一個 blocker。

## Production mutation seal

- run tree digest before／after：`dbd15c...9a2`／相同。
- replacement registry：`25e084...eeef`／相同。
- publisher ledger：`4fa274...3f37`／相同。
- `article-locales.js`：`686e63...a3a`／相同。
- all `article-locale-*.js` aggregate：`bd4670...4600`／相同。
- outbox + processing：`0`／`0`。
- provider／publisher／stage execute／release／tag／push：全部 `0`。

## 總體判定

`部分退化`：workflow仍是可治理的拆解式流程，gate都正確 fail closed；缺口是兩個已可量測、相鄰但不同 ownership contract。現階段唯一安全主裁決是 `FORMAL_MISSING_SEAM / NO_GO_SINGLE_LIFECYCLE_ADAPTER`。
