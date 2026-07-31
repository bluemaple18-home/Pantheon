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
