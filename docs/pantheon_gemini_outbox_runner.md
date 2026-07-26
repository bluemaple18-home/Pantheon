# Pantheon Gemini Outbox Runner

## 狀態與邊界

本文件描述本機使用者擁有的整合。Repo 只提供 queue、coordinator 與 launchd installer；不自動安裝、不登入 Gemini，也不寫入 token。預設 CLI 路徑不讀取 API key；只有使用者明確設定 production credential pool 時，lane runner 才會從被選中的 owner-only credential file 讀取一次 API key。使用者完成一次性啟用後，coordinator 才會在本機背景處理已明確登記的 run。

內容產文與 V4 broker 的放量決策已分離，完整邊界見
[`pantheon_content_transport_decoupling.md`](pantheon_content_transport_decoupling.md)。
未設定 `AGY_GEMINI_V4_BROKER=1` 時，runner 使用既有 Gemini CLI callsite；
V4 canary 的成功或失敗不改變受監督產文狀態。

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

## Production credential pool（明確 opt-in）

四條 production lane 可共同設定 `AGY_GEMINI_CREDENTIAL_POOL_FILE`。這個 flag 與 `AGY_GEMINI_V4_CREDENTIAL_POOL_FILE` 完全分離，不啟用、不沿用也不升級 V4 broker／target／shadow transport。未設定 production flag 時，runner 維持既有 `AGY_GEMINI_CLI`。

Manifest 必須是目前使用者擁有、group/other 無權限、regular、non-symlink 的 JSON file；三個 credential file 也必須符合相同檔案安全條件。Manifest 固定只有三槽，schema 如下：

```json
{
  "schema_version": 1,
  "pool_id": "pantheon-production-v1",
  "slots": [
    {
      "slot_id": "account-1",
      "credential_file": "<user-config>/pantheon/gemini-api-key-1"
    },
    {
      "slot_id": "account-2",
      "credential_file": "<user-config>/pantheon/gemini-api-key-2"
    },
    {
      "slot_id": "account-3",
      "credential_file": "<user-config>/pantheon/gemini-api-key-3"
    }
  ]
}
```

每個 credential file 只放一個 ASCII API key，可有結尾換行。Manifest 與三個 credential file 都應設為 `0600`；credential path 必須是絕對路徑，但不得把實際本機路徑提交到 repo。

四條 lane 必須共用同一個 absolute
`AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE`。State 與其 `.lock` companion
必須是目前使用者擁有、group/other 無權限、regular、non-symlink file。
State 不存在時，第一個 allocation 會以 `0600` 安全初始化；既有 state
使用以下 closed schema：

```json
{
  "schema_version": 1,
  "pool_id": "pantheon-production-v1",
  "manifest_sha256": "<canonical-manifest-sha256>",
  "last_ordinal": 1
}
```

每個新 allocation 的選槽規則固定：

1. 對三個 slot 依 `slot_id` canonical sort。
2. 四條 lane 在同一跨程序 exclusive lock 內讀取 state，取得下一個唯一 ordinal。
3. 先 durable commit ordinal，再依 `(ordinal - 1) mod 3` 選出
   `account-1 → account-2 → account-3 → account-1`。
4. Runner 只開啟被選中的 credential file，並且只送出一次 provider POST。
5. Commit 後的 crash、`429`、其他 HTTP failure、timeout、transport error
   或 provider output invalid 都已消耗 ordinal；不回滾、不換 key、不 retry、
   不 fallback，也不重送既有 failed job。

Corrupt/truncated、symlink、wrong owner/mode、relative path、pool/manifest
mismatch 或 open-time replacement 都會在 credential value 與 provider request
前 fail closed。成功 inbox、失敗 receipt 與 runner stdout 的
`credential_pool` 仍精確只有 `pool_id`、`slot_id`、canonical manifest
SHA-256；不加入 ordinal 或 state path。它們也不得帶 credential path/value、
provider response body 或 exception detail。Queue、archive、failed、deferred、
quarantine 與既有 V4 ledger 行為不因 production pool 改寫或清除。

`AGY_GEMINI_V4_BROKER=1` 只供獨立 V4 canary／shadow 驗證。受監督產文不得
因環境中殘留該 flag 而誤入 V4；直接內容 pipeline 固定以
`AGY_GEMINI_TRANSPORT=cli` 選擇既有 CLI transport。

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

若要明確啟用三槽 production pool，先在本機準備 owner-only manifest 與 credential files，再只對這次 installer 執行提供：

```bash
AGY_GEMINI_CREDENTIAL_POOL_FILE="<user-config>/pantheon/production-gemini-pool.json" \
AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE="<private-state-root>/pantheon/production-gemini-round-robin.json" \
  bash scripts/install_agy_gemini_coordinator_launchd.sh
```

Installer 只會把 production pool manifest path 與同一個 absolute state path
加入 `new`、`rewrite`、`i18n-new`、`i18n-rewrite` 四條 lane plist；不會把
key value 加入 environment、argv 或 plist。若未明確提供 state path，
預設為 absolute queue root 下的
`production-credential-pool-state.json`。未提供 production pool flag 時，
lane plist 不會出現 pool 或 allocator state flag。

Installer 會解析並驗證以下 placeholder：

- `__REPO_ROOT__`
- `__PYTHON__`
- `__AGY_GEMINI_CLI__`
- `__LOG_DIR__`

Installer 會拒絕與舊版 standalone runner 同時啟用，避免兩個程序競爭 queue。它不修改 shell profile、Gemini 設定、OAuth、token store 或全域 ai-core。

## 回復

尚未啟用時只需不執行 installer；repo 內檔案不會啟動任何服務。若日後已安裝，先停止 `com.pantheon.agy-gemini-coordinator`，再移除使用者 LaunchAgents 內的同名 plist；`.work/gemini-runner/` 保留作稽核，不由程式自動刪除。
