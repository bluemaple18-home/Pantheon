# Publisher 磁碟與 Lane 契約修復

- 日期：2026-07-31
- production Gemini calls：0（本修補與測試未呼叫外部模型）
- production Publisher：修補期間已停止，避免每分鐘繼續累積 orphan

## Root cause

1. Publisher 在 transaction worktree 建立後，才於內層 publish function 取得
   transaction lock。程序被重置、kill 或因磁碟不足退出時，Python `finally`
   未必完成；後續每輪會再建立約 90 MiB worktree，且沒有啟動時 scavenger。
2. expansion-50 web test 永久比對
   `REWRITE_RELEASE_001_BODY_OVERRIDES` 與初始 `updated` 日期，會把後續正式
   rewrite 的最高優先序 body／policy 當成回歸。
3. i18n locale plan 的 provider response 可完整回傳 fact 集合、唯一性與
   safety flag，但 Gemini 不保證陣列順序；本機 validator 卻要求與 hash 排序
   完全相同，形成 deterministic contract collision。

## RED

```text
orphan cleanup: transaction-orphan / transaction-incomplete remained
lifecycle lock: helper missing
log cap: helper missing
rewrite tests: getActiveArticleBodyOverride export missing
i18n: ValueError: locale plan coverage mapping order differs for article-01
```

## GREEN

- transaction 建立、執行與回收全程由 Git common-dir lifecycle lock 序列化。
- 每次取得 lifecycle lock 後，先精準回收專用 state root 的
  `transaction-*` orphan，再建立新 worktree。
- Publisher stdout/stderr 超過 32 MiB 時，同 inode 保留最後 4 MiB，避免
  launchd descriptor 失效。
- article runtime 匯出最高優先序 body resolver；rewrite test 驗證 active
  override 與 registry `updated`，不再鎖死第一版 release。
- i18n hydration 先驗證 exact fact set、唯一性、欄位與 safety flag，再依
  expected fact ID 順序 canonicalize；原本 internal validator 照常執行。
- 缺漏、重複 fact、錯誤 safety flag、非法 H2 slot 仍 fail closed。

## 實際容量回收

```text
registered orphan worktrees: 14
incomplete transaction dirs: 1
cleaned transactions: 15
publisher state: 1.3 GiB -> 44 MiB
publisher stdout: 59 MiB -> 4.0 MiB
Data available: 21 GiB -> 23 GiB
active Codex session: retained; not a cleanup target
```

## 驗證

```text
publisher + multilingual: 254 passed
web: 72 passed
full suite: 827 passed, 2 existing warnings
git diff --check: PASS
```

## Agentic workflow audit

- 檢查 1 Task 邊界：PASS
  - 四條 lane、Publisher 與 deterministic validators 有獨立入口與測試。
- 檢查 2 Input / Output 契約：PASS
  - brief、locale plan、candidate、review 與 evidence 均為結構化 artifact。
- 檢查 3 可程式化成功標準：PASS（本輪修復前為 PARTIAL）
  - stale rewrite expectation 與 provider-order collision 已改成可持續的
    deterministic 契約，未把 LLM 自評當硬閘門。
- 檢查 4 獨立 SOP / Skill 規範：PASS
  - 生成、Reviewer、Publisher 與 release gate 職責分離。
- 檢查 5 控制流歸屬：PASS
  - lane state、retry cap、Publisher selection 與 rollback 皆由程式控制。
- 檢查 6 失敗處理與回退：PASS（本輪修復前為 PARTIAL）
  - 既有 candidate rollback 保留；新增 crash orphan recovery 與容量界線。

## 試金石結果

- 單步隔離執行：locale plan hydration、rewrite resolver、transaction cleanup
  與 log trim 均可用固定 fixture 單獨執行。
- 憑 trace 重建流程：run state、candidate、review、Publisher evidence 與
  release commit 可重建流程；production 四 lane 再驗收仍待部署後觀察。

## 總體判定

真・拆解式 workflow；本輪消除兩個 deterministic contract collision 與一個
crash cleanup 缺口。

## 最高風險項

- P1：尚未部署前，production actor 仍是舊 runtime。
- P2：部署後必須確認排程不再留下 transaction orphan。
- P2：四條 lane 必須以真實 production output 驗收，不能用 idle 或 fixture。

## 下一步

- 提交、推送、同步 Publisher actor，重新安裝 launchd。
- 觀察至少一輪 Publisher 與四條 lane，補上 production 結果。

## Production follow-up：rewrite policy resolver

- `v0.3.194` 已由 production Publisher 發布 1 篇新文章，公開文章總數
  由 506 增至 507。
- 後續 rewrite production batch 通過 body override 與 preflight，但完整
  web suite 揭露 registry 清單與單篇 lookup 使用不同 policy resolver：
  清單為 `updated=2026-07-31`，實際渲染仍保留舊日期。
- Publisher 已安全回滾，3 個 rewrite candidate 均保留，沒有把不一致內容
  推上線；transaction 結束後 state root 回到約 45 MiB，未再留下 orphan。
- 修復後 `listArticleRecords()`、`getArticleRecord()` 與
  `buildArticleContent()` 共用中央 resolver；Publisher 產生下一版 rewrite
  時也只 prepend 該 resolver。
- 新增 regression 直接驗證 registry、lookup、rendered content 的
  `updated` 與 `publicationPolicy.modified` 一致。

```text
focused publisher + multilingual + web: 327 passed, 2 existing warnings
full suite: 828 passed, 2 existing warnings
```

## Production follow-up：source acronym 語言判定

- `v0.3.196` 已由 production Publisher 發布 1 篇新文章，公開文章總數
  由 507 增至 508；`v0.3.197` 已發布 3 篇 rewrite。
- `i18n-new` 英文 run `auto-i18n-en-9460ffe098eab088250f` 已完成 candidate，
  Reviewer 因 `MIRRORED_STRUCTURE` 與 `LITERAL_TRANSLATION` 拒絕；這是內容
  品質閘門正常運作，不冒充 production output。
- 同源日文與韓文 plan 的 22 個 facts 完整、唯一、順序與 safety flag
  正確；失敗點是 `ENTJ ENTP` 佔多數拉丁字母，讓合法的日／韓搜尋 query
  被語言閘門誤判。
- 修復只豁免「來源文章實際出現」的全大寫 acronym；來源沒有的
  `ZXCV QWER` 仍拒絕，正文、H2、coverage note 的目標語言檢查不移除。
- 兩份原始 production external plan 重播均通過 22/22 facts。

```text
publisher + multilingual focused suite: 258 passed, 1 existing warning
production plan replay: ja PASS 22/22; ko PASS 22/22
publisher cleanup: exit 0; transaction 0; state root 45 MiB
full suite after acronym repair: 832 passed, 3 existing warnings
```

## Production follow-up：rewrite release ID 碰撞

- 失敗 batch 只有 1 個 run；舊程式以 `len(run_ids)` 產生
  `agy-rewrite-20260731-01`，因此覆寫同日既有 `-01` 模組，把
  `THEME-LIFE-01` 的 body／policy 換成 `THEME-LIFE-08`。中央 resolver
  正常讀取最高優先序，但舊文章的正式 override 已被寫入端移除，完整 web
  suite 因此正確阻擋並回滾。
- release ID 現改為掃描 repo 當日既有 rewrite 模組，取最大序號加一；
  production repo 已有 `-01/-02/-03` 時實際配置探針為 `-04`。
- `apply_rewrite_release()` 另加不可覆寫閘門；即使 allocator 日後退化或
  收到重複 ID，也會在寫檔前 `PublishBlocked`，舊模組內容保持不變。
- 舊 runtime 最後一輪因累積 2 個合格 run，使用尚未占用的 `-02`：
  `v0.3.200` 已真實發布 `THEME-LIFE-10`、`THEME-LIFE-08`。同輪先發布
  `v0.3.199` 新文 `V2-MBTI-PAIR-ENTJ-INFP-LOVE`；公開文章總數 509。
- 該輪 transaction 執行中 94 MiB，退出後自動刪除；Publisher state root
  回到 45 MiB，沒有 orphan。這證明容量上升是受控的單一 active
  transaction，不再是每輪永久累積。
- translation ledger 目前仍為 0 個正式 release；i18n candidates 的
  Reviewer APPROVE／REJECT 均不冒充上線產出。

```text
production releases: v0.3.199 new 1; v0.3.200 rewrite 2
rewrite allocator probe: agy-rewrite-20260731-04
publisher cleanup: transaction 0; state root 45 MiB
full suite after collision repair: 833 passed, 3 existing warnings
git diff --check: PASS
```
