---
id: CARD-PANTHEON-PUBLISHER-DEADLOCK-REPAIR-20260724-recovery
status: DELIVERED_CANDIDATE
type: recovery-runbook
---

# v0.3.59 actor 無資料遺失 recovery runbook

本 runbook 由 actor owner 在正式 actor 執行；implementation thread 不直接操作 actor。先確認修復 candidate 已由 mainline review、整合並可供 actor fast-forward。

## 0. 變數

```bash
cd <repo-root>
QUEUE_ROOT="<queue-root>"
RECOVERY_ROOT=".work/content-publisher/recovery-v0.3.59-20260724"
mkdir -p "${RECOVERY_ROOT}"
```

`<queue-root>` 必須使用 launchd 實際設定的 queue 路徑，不得猜測。

## 1. 停止兩個週期 actor

```bash
launchctl bootout "gui/$(id -u)/com.pantheon.agy-content-publisher"
launchctl bootout "gui/$(id -u)/com.pantheon.agy-gemini-coordinator"
```

若 label 不存在，只記錄結果，不要刪除任何 queue 或 ledger。

## 2. 先保存 actor、queue 與 ledger 證據

```bash
git rev-parse HEAD > "${RECOVERY_ROOT}/head-before.txt"
git status --short > "${RECOVERY_ROOT}/status-before.txt"
git diff --binary > "${RECOVERY_ROOT}/actor-v0.3.59.patch"
tar -czf "${RECOVERY_ROOT}/actor-v0.3.59-files.tgz" -- \
  CHANGELOG.md \
  app/web/static/article-locales.js \
  app/web/static/article-locale-auto-i18n-ko-4c30845dd81a6f69b994.js \
  package.json \
  pyproject.toml \
  tests/test_web.py
cp -a "${QUEUE_ROOT}" "${RECOVERY_ROOT}/queue-snapshot"
cp -a .work/content-publisher/ledger.json "${RECOVERY_ROOT}/ledger.json"
```

建立檔案清單與 hash：

```bash
find "${RECOVERY_ROOT}/queue-snapshot" -type f -print0 | sort -z | xargs -0 shasum -a 256 > "${RECOVERY_ROOT}/queue-sha256.txt"
shasum -a 256 "${RECOVERY_ROOT}/ledger.json" "${RECOVERY_ROOT}/actor-v0.3.59-files.tgz" > "${RECOVERY_ROOT}/recovery-sha256.txt"
```

若 archive、queue snapshot、ledger 或 hash 任一項無法完成，立即停止；不要清理 actor。

## 3. 以本地 rescue commit 保存 v0.3.59

確認 `status-before.txt` 只包含已知 publisher-owned 六個 tracked 檔與一個 locale module。若多出未知檔案，停止並交回 mainline。

```bash
git switch -c rescue/publisher-v0.3.59-dirty-20260724
git add -- \
  CHANGELOG.md \
  app/web/static/article-locales.js \
  app/web/static/article-locale-auto-i18n-ko-4c30845dd81a6f69b994.js \
  package.json \
  pyproject.toml \
  tests/test_web.py
git commit -m "rescue: preserve failed publisher v0.3.59"
git status --short
```

最後一行必須為空。不要 push rescue branch，也不要建立 `v0.3.59` tag。

## 4. 回到 main 並載入已整合修復

```bash
git switch main
git fetch origin main
git merge --ff-only origin/main
git status --short
```

`git status --short` 必須為空。禁止使用 `git reset --hard`、`git checkout --` 或刪除 queue/ledger。

## 5. 修復後 preflight

```bash
<repo-root>/.venv/bin/python -m pytest \
  tests/test_agy_content_publisher.py \
  tests/test_agy_multilingual_pipeline.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_web.py -q
git diff --check
git status --short
```

測試須全綠，且兩個 git 檢查須無輸出。

## 6. 重啟並觀察

使用 repository 內兩個 install scripts 重新安裝 actor：

```bash
bash scripts/install_agy_gemini_coordinator_launchd.sh
bash scripts/install_agy_content_publisher_launchd.sh
```

至少觀察一個 coordinator 週期與一個 publisher 週期。接受條件：

- gate fail 時，`.work/content-publisher/evidence/failed-*/failure.json` 顯示 `repo_recovered: true`；
- `git status --short` 為空；
- queue snapshot 原檔仍存在，failed/deferred run 未被刪除；
- 通過候選可進入 published ledger；
- `tests/test_web.py` 的 `ARTICLE_CACHE_TOKEN` 與 `app/web/article.html`、`app/web/articles.html` runtime query 一致；
- V4 預設沒有改變。

rescue branch 與 recovery archive 至少保留到 v0.3.59 或替代 release 經 mainline 驗收；不要提前刪除。
