# Pantheon Gemini Outbox Runner

## 狀態與邊界

本文件描述尚未啟用的本機整合候選。程式碼可建立與驗證 queue，但不安裝 launchd、不登入 Gemini、不讀取或寫入 token，也不自動送出外部請求。

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
- execution status：程式與範本已建立；launchd 維持未啟用。
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

## launchd 採用候選

範本位於 `ops/launchd/com.pantheon.agy-gemini-runner.plist.example`。它每 60 秒最多處理 5 個既有 outbox jobs，但預設 `RunAtLoad=false`，而且保留以下 placeholder：

- `__REPO_ROOT__`
- `__PYTHON__`
- `__AGY_GEMINI_CLI__`
- `__LOG_DIR__`

啟用屬於本機背景服務與外部資料傳輸變更，必須在另一個明確授權步驟中完成。不得由 installer 自動修改 shell profile、Gemini 設定、OAuth、token store 或全域 ai-core。

## 回復

尚未啟用時只需不安裝 plist；repo 內檔案不會啟動任何服務。若日後已由使用者安裝，回復順序是先停止對應 user LaunchAgent，再移除使用者安裝的 plist；`.work/gemini-runner/` 保留作稽核，不由程式自動刪除。
