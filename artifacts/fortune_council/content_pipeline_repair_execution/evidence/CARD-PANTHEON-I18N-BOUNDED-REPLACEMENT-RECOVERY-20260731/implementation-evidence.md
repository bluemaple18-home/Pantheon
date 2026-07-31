# i18n bounded replacement｜本地實作證據

日期：2026-07-31
卡片：`CARD-PANTHEON-I18N-BOUNDED-REPLACEMENT-RECOVERY-20260731`
分支：`codex/i18n-bounded-replacement-20260731`
初始實作基底：`523ad3e4c`
最終重新驗證主線：`2066de2c2`（`v0.3.221`）
原始實作 commit：`7002e135f`
後續修補：`5386447c1`、`f00298681`
最終部署 commit：`51d6cbb5c`
狀態：`DEPLOYED_CANARY_NO_GO_QUALITY`
Production canary：`HOLD`

## 結論

本次沒有重寫 Gemini runner、transport retry、credential pool、locale gate 或
Publisher。修補只接在既有 terminal state 與 translation enqueue 之間：封閉
eligible failure 每個 base run 最多建立一個 `-replacement-01`，每個 cycle／
i18n lane 最多一筆；原 state、brief、attempt 與 receipt 保持不可變。

既有 fact coverage canonicalization、最高優先序 rewrite resolver／測試與
publisher crash cleanup 均直接沿用，未在本卡重做。

## 根因與被否證假說

- 真正缺口：terminal translation run 的 deterministic identity 永久留在
  `failed`，原 enqueue 不會再次啟用，因此 locale release 可長期停滯。
- 被否證：`NETWORK` 完全沒有 retry。Production archive 已存在 transport
  attempt `0`、`1`、`2`；既有 `OUTBOX_MAX_TRANSPORT_RETRIES = 2` 正常運作。
- 保存 response replay 仍會被原 deterministic gate 正確拒絕：一筆為 native
  locale language 不符，一筆為 source fact coverage 不符。這些 gate 沒有放寬。

## RED

1. Replacement public behavior 測試先因
   `enqueue_translation_replacement` 不存在而失敗。
2. Coordinator lane seeding 測試先因沒有 bounded replacement seam 而失敗。
3. `cycle_once(..., lane_mode=True)` 整合測試先得到 `calls == 0`。
4. Source-drift skip persistence 測試先證明第二個 cycle 會再次處理同一失敗。

上述 RED 均由同一 public behavior 的 GREEN 測試取代，沒有用 mock success
冒充 production release。

## 最小改動

- `scripts/agy_multilingual_pipeline.py`
  - 新增 closed recovery reason allowlist。
  - 新增一次性、idempotent translation replacement helper。
  - 驗證 failed terminal state、base identity、source SHA 與 replacement collision。
- `scripts/agy_gemini_coordinator.py`
  - 保存 closed external failure category 與已使用 transport attempts。
  - 每條 i18n lane／cycle 最多 seed 一個 eligible replacement。
  - `AUTH`、`QUOTA`、candidate quality failure 等維持 terminal。
  - source drift／invalid terminal state 另寫 closed decision receipt，避免每輪
    重複處理與 log loop。
- `tests/test_agy_multilingual_pipeline.py`
- `tests/test_agy_gemini_coordinator.py`

Production code 未修改其他檔案；code diff 為 4 files、681 insertions、1 deletion，
其中 430 行為回歸測試。

## GREEN 驗證

### 風險核心

```text
3 passed in 0.07s
```

覆蓋：單一 replacement、雙 i18n lane 上限、source-drift decision 不重複，並
額外證明 failed replacement 不會生成 replacement-02。

### 受影響 suites

```text
228 passed in 12.79s
```

命令範圍：

```text
tests/test_agy_multilingual_pipeline.py
tests/test_agy_gemini_coordinator.py
```

### Repository 全域回歸

```text
pytest -qq
exit 0
```

只有既有 Starlette／escape-sequence deprecation warnings，沒有 test failure。

### 最新主線重放

- 分支先後重放 v0.3.218–v0.3.221 內容 release；上游沒有修改本卡四個檔案。
- 最後一次 `git rebase origin/main`：無衝突，base `2066de2c2`。
- 重放後受影響 suites：`228 passed in 13.04s`。
- 重放後 repository 全域回歸：exit `0`。
- 修復已 fast-forward 推送為 `7002e135f`；production actor 與 Publisher
  deployment contract 已對齊同一 SHA。

### 靜態檢查

- `git diff --check`：PASS
- `[DBG-`／`TODO`／`FIXME` 掃描：無新增命中
- Code review gate：未發現阻塞問題
- Traceability preflight：critical `[]`、warnings `[]`、verdict `OK`

## 容量與外部邊界

- 驗證後資料卷可用空間：`32 GiB`，使用率 `83%`。
- 本卡沒有清除檔案；既有 publisher orphan cleanup 與容量界線直接沿用。
- 本文件前段的本地驗證階段沒有外呼或 production mutation；後續已授權的
  push、部署與 canary 結果另見 `production-canary-20260801.md`。

## 部署後保存 response 修補

正式 lite model 的 provider response 成功後，保存 bytes 重播暴露第二個
deterministic ownership conflict：模型回傳 `rebuild_outline=true`，但第一代
pipeline authority 為 `false`。該欄位不是內容判斷，與既有
`source_structure_not_copied`／fact order canonicalization 同屬 pipeline-owned
資料。

- RED：`ValueError: locale plan rebuild authority differs for article-01`
- GREEN：同一保存 response hydrate 成功，`rebuild_outline=false`、
  `coverage_count=17`
- 修補：`5386447c1`
- 契約：provider 欄位仍必須是 boolean；實際 authority 由 pipeline 寫入，
  其他 locale-plan gate 不變

日文與韓文候選接著一致出現來源繁中殘留，故以 `f00298681` 補上單一逐欄
硬約束：`title`、`description`、`answer`、`tags`、FAQ、H2、paragraphs 必須
依 `article input.locale` 完整重寫。英文 production prompt 已直接取證包含該
句；其三代 deterministic findings 均為 0，證明語言層改善，但 Reviewer 仍因
來源句法與搜尋意圖拒絕。

最終驗證：

```text
deterministic authority focused: 4 passed
multilingual + coordinator: 231 passed
provider-schema + multilingual + coordinator: 353 passed
repository-wide: exit 0
git diff --check: PASS
```

曾以 `gemini-3.5-flash` 做一個 strict、未切排程的 capability canary；大型 enum
移除後 provider enum max 為 4，仍立即 `API_HTTP_ERROR`。試驗 commit
`362e3e474` 已由 `51d6cbb5c` 撤回，production Writer 保持已證實可用的
`gemini-3.5-flash-lite`。

## 剩餘風險

1. Provider 並未全面故障；真正未通過的是母語品質。`i18n-new` 已在 ja、ko、
   en 三個獨立 bounded canary 被 Reviewer 拒絕，兩條 i18n 均沒有本卡新
   release，`production_canary_hold` 必須保持。
2. 六個 LaunchAgent 保持卸載。`i18n-rewrite` lane 尚保存一個 immutable
   `gemini-3.5-flash` transport-attempt-1 outbox job；啟動 runner 會自動外呼，
   必須先另做明確 cancellation／terminalization 決策。
3. 舊 external terminal state 若沒有 closed category／attempt metadata，保持
   fail closed；現有 locale-plan terminal state 不受此限制。
