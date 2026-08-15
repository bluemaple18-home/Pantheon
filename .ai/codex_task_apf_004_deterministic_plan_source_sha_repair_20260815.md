# APF-004 deterministic plan source SHA 修復卡

## 工作身分

- 角色：既有 APF-004 Repair thread；不得建立第二個 Repair。
- 模式：strict／read-only production observation；僅 repository evidence write。
- 基底候選：`e8308faaeadc4033ac8247fa262e00918f46c69a`。
- 權威 target/source SHA：`28b8b84b6dfa319d8151aac3bc1a6a819ae82aa1`。

## 問題

Reviewer 對基底候選回 `CHANGES_REQUIRED`：兩次 plan 與衍生 exact apply argv 錯用舊 actor SHA `0bf78f0b...`。該 SHA 早於 plan-digest binding repair；若套用會把 actor 回退到修復前版本。

## 唯一可改範圍

只可替換以下目錄內既有 10 個 JSON，不得新增第 11 個檔案：

`artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/deterministic_plan_reproduction_after_digest_repair_20260815/`

禁止修改 code、config、tests、registry、共享 metadata、生成頁、sitemap、feed、redirects 與其他 artifact root。

## 執行契約

1. 先證明 `28b8b84b6dfa319d8151aac3bc1a6a819ae82aa1` 可讀、clean、origin 正確，且含 plan-digest binding repair；目前 evidence commit 不得成為 target actor SHA。
2. 擷取 live read-only pre-snapshot。
3. 使用 public CLI，對權威 SHA 執行 `plan` 恰好兩次；兩次使用相同 correlation ID、generation、transaction root 與其他參數。
4. 任一 plan 非零、capacity／stop-loss gate 不成立、transaction root 已存在、或 deterministic 契約不一致時，立即 fail closed。
5. 重產原 10 個 JSON：兩次 plan、exact apply argv、argv source map、pre/post snapshots、production mutation summary、receipt、verification、artifact digests。
6. exact apply argv 只允許 `plan` 改成 `apply`，並追加新 `--expected-plan-digest`；只記錄，不得執行。
7. 執行過的 public subcommands 必須恰為 `plan, plan`；`production_mutation` 必須為 `0`；transaction root pre/post 均 absent。
8. 跑 JSON parse、9 個 raw-byte artifact SHA-256、sanitizer、allowlist、`git diff --check`。
9. 建立新 candidate commit；不得 amend、force、push。

## 絕對禁止

- `apply`、`rollback`、`finalize`、Gate B、publish、deploy、queue、transaction、tag、push。
- production actor／manifest／private stage／state／queue／worker／launchctl mutation。
- 未取得逐動作新授權前，不得沿用任何舊 Gate A authorization。

## 交付

- full candidate SHA 與 parent SHA。
- 新 plan digest、target manifest digest、exact apply argv digest。
- 10-file count、verification 結果、worktree clean 狀態。
- 明確回報 `production_mutation: 0`。

## 驗收

- 固定 SHA 交回既有 Reviewer thread 唯讀複審。
- Reviewer `APPROVED` 前不得整合或 push。
