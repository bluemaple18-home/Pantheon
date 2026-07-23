# Pantheon 產文與 Gemini V4 Transport 解耦決策

## 決策

自本決策起，受監督產文與 Gemini V4 broker 分成兩條獨立工作線：

```text
受監督產文
brief → Writer → deterministic gate → Reviewer → 人工 approval → apply
                         │
                         └─ 既有 Gemini CLI transport

V4 技術改善
合成公開 request → outbox runner → V4 broker → canary evidence
```

V4 canary 未完成不再阻擋受監督產文。V4 仍是未來無人值守大量執行的可靠性升級，在通過真實 canary、exactly-once、replay 與失敗恢復驗證前，不得成為預設 transport。

## 兩條線的邊界

### 受監督產文

- 使用 `scripts/agy_seo_copy_pipeline.py` 的既有 CLI transport。
- 明確設定 `AGY_GEMINI_TRANSPORT=cli`；不以 `AGY_GEMINI_V4_BROKER` 控制直接產文。
- 採小批次執行，每批必須產生 candidate 與獨立 Reviewer 結果。
- 未經人工 approval 不得 apply；apply 後仍須走既有驗證與發布程序。
- CLI、parse、schema 或 Reviewer 失敗時停止該批，不自動切換 V4、不自動發布。

### V4 技術改善

- 只透過 `scripts/agy_gemini_runner.py` 的 `AGY_GEMINI_V4_BROKER=1` opt-in 路徑執行。
- 使用合成公開 payload 做單次 canary；不得讀寫文章、registry 或發布資料。
- 失敗時 fail closed，不 fallback、不 retry、不影響受監督產文的狀態。
- V4 的 commit、evidence、review 與放量決策獨立於內容批次。

## V4 切換為預設前的 Gate

必須同時具備：

1. 真實 CLI canary 成功，且可重建唯一 operation、唯一 target process 與綁定結果。
2. Exactly-once、ledger、anchor、replay 與 ambiguous failure 行為通過測試及獨立 review。
3. 小批量 shadow run 證明與既有 CLI transport 的 schema／Reviewer 契約相容。
4. 另開 migration commit 切換預設；不得在 canary 或內容 commit 中順手切換。

## 回退

- 受監督產文的回退：停止該批並保留 evidence，不影響 V4 canary。
- V4 的回退：關閉 `AGY_GEMINI_V4_BROKER`，runner 回到既有 legacy callsite；不修改內容 pipeline。
