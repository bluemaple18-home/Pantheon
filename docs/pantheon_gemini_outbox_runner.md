# Pantheon Gemini Outbox Runner

## 狀態與邊界

本文件描述本機使用者擁有的整合。Repo 只提供 queue、coordinator 與 launchd installer；不自動安裝、不登入 Gemini、不讀取或寫入 token。使用者完成一次性啟用後，coordinator 才會在本機背景處理已明確登記的 run。

```text
Pantheon private run
→ sanitized outbox request
→ user-owned Gemini runner
→ SHA-bound inbox response
→ Pantheon deterministic gate / Reviewer gate
→ candidate.json / review.json / review.md
→ 既有 approval / apply
```

外部工具閘門：

- tool/service：既有 Antigravity 或 Gemini CLI。
- operation level：`external_generation`。
- connection status：由使用者啟用 runner 時自行確認；bridge 不碰憑證。
- schema checked：request 與 response envelope 都採 strict 契約；模型 result 由既有 pipeline schema 與業務 gate 驗證。
- execution status：程式、coordinator 與範本已建立；launchd 是否啟用由本機使用者控制。
- remaining risk：外部模型仍會收到 outbox 中明列的公開文字；啟用前必須由使用者確認服務帳號與資料政策。

## 資料契約

私密資料留在 `.work/gsc-copy/<run-id>/`。Outbox 只允許：

- opaque namespace，不包含 run ID。
- `writer` 或 `reviewer` role。
- 模型名稱與 `LOW` thinking level。
- 由 `public_model_brief()` 產生的公開 prompt。
- response JSON schema。
- prompt、schema 與整份 request 的 SHA-256。

Bridge 會拒絕以下內容：

- `/Users/`、`/home/`、`/private/`、`/var/`、`/tmp/` 等本機絕對路徑。
- `.work/` 路徑。
- Gemini API key、Google API key、Bearer token、GitHub token與 private key 標記。
- 超過 256 KB 的 prompt 或超過 64 KB 的 schema。

Runner 只讀 `.work/gemini-runner/outbox/`，完成後：

- request 移到 `archive/`。
- 成功或格式錯誤的模型 JSON 都寫入 `inbox/`，並綁定 request SHA；格式錯誤由既有 Reviewer gate 產生正式 REJECT。
- 失敗只在 `failed/` 留下 job ID、request SHA 與錯誤類型，不保存 CLI stderr 或憑證內容。

## 手動 dry-run 流程

以下指令只說明介面；是否執行外部 runner 由使用者自行決定。

```bash
<repo-root>/.venv/bin/python -m scripts.agy_gemini_outbox tick \
  .work/gsc-copy/<run-id> \
  --queue-root .work/gemini-runner
```

第一次 tick 會建立 Writer job，並以 exit code `75` 表示等待外部結果。使用者啟用的 runner 可處理一筆：

```bash
<repo-root>/.venv/bin/python -m scripts.agy_gemini_runner \
  --queue-root .work/gemini-runner \
  process-once
```

再次 tick 會驗證 Writer response、執行 deterministic gate，並建立全新 Reviewer job。Reviewer 完成後再 tick 一次，既有 pipeline 會產生：

```text
.work/gsc-copy/<run-id>/candidate.json
.work/gsc-copy/<run-id>/review.json
.work/gsc-copy/<run-id>/review.md
```

Reviewer JSON 格式錯誤仍依既有規則退件。完成後仍須走既有 `approve` 與 `apply`；runner 不核准、不修改文章來源、不 commit、不 push、不部署。

## Coordinator

Coordinator 只處理明確登記的 run，不會掃描並啟動所有 `.work/gsc-copy/` 目錄。Codex 建立 brief 後可在本機登記：

```bash
<repo-root>/.venv/bin/python -m scripts.agy_gemini_coordinator \
  --queue-root .work/gemini-runner \
  register .work/gsc-copy/<run-id>
```

背景 cycle 每次最多執行一個外部 job，完成後再 tick 一次，讓 Writer、獨立 Reviewer 與有上限的退修流程逐輪前進。它使用 lock 防止重疊執行，每輪最多查看 5 個 active run。狀態保存在 `.work/gemini-runner/runs/`，不會送往外部。

```bash
<repo-root>/.venv/bin/python -m scripts.agy_gemini_coordinator \
  --queue-root .work/gemini-runner \
  status .work/gsc-copy/<run-id>
```

Coordinator 的完成條件只代表已產生 candidate 與 review；它不建立 `approval.json`，也不 apply、commit、push 或部署。

## 一次性 launchd 啟用

正式背景範本位於 `ops/launchd/com.pantheon.agy-gemini-coordinator.plist.example`。它每 60 秒執行一次 cycle，且每個 cycle 最多對外處理一個 job。`RunAtLoad=true`，啟用後會立即接續已登記的 run。

使用者只需在本機執行一次：

```bash
bash scripts/install_agy_gemini_coordinator_launchd.sh
```

Installer 會解析並驗證以下 placeholder：

- `__REPO_ROOT__`
- `__PYTHON__`
- `__AGY_GEMINI_CLI__`
- `__LOG_DIR__`

Installer 會拒絕與舊版 standalone runner 同時啟用，避免兩個程序競爭 queue。它不修改 shell profile、Gemini 設定、OAuth、token store 或全域 ai-core。

## 回復

尚未啟用時只需不執行 installer；repo 內檔案不會啟動任何服務。若日後已安裝，先停止 `com.pantheon.agy-gemini-coordinator`，再移除使用者 LaunchAgents 內的同名 plist；`.work/gemini-runner/` 保留作稽核，不由程式自動刪除。
