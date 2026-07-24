---
card_id: CARD-PANTHEON-PUBLISHER-DEADLOCK-REPAIR-20260724
status: RUNNING
type: implementation-repair
project: Pantheon
chain_id: pantheon-publisher-deadlock-repair-20260724
owner: implementation
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 發佈交易失敗會堵塞共享自動化，且涉及 queue、ledger、Git worktree 與 launchd 的跨模組 invariant。
created_at: 2026-07-24 20:35 CST
source_sha: 41522076fccbe0406fb4d270d138368ce5c0395f
---

# Pantheon Publisher Deadlock Repair

## Root question

修復 Pantheon 多語發佈排程，使單篇翻譯或 release gate 失敗時不會留下 dirty publisher worktree、堵住後續所有文章；並安全恢復目前卡住的 `v0.3.59` 與 queue。

## Current blocker

- 正式 publisher actor：`<repo-root>` 對應主機上的 `Pantheon-publish-actor`。
- actor HEAD 與 `origin/main`：`41522076fccbe0406fb4d270d138368ce5c0395f`（v0.3.58）。
- actor 目前有未提交的 v0.3.59 翻譯變更：
  - `CHANGELOG.md`
  - `app/web/static/article-locales.js`
  - `app/web/static/article-locale-auto-i18n-ko-4c30845dd81a6f69b994.js`
  - `package.json`
  - `pyproject.toml`
  - `tests/test_web.py`
- 首次 red-capable gate：`145` tests 中 `3 failed, 142 passed`。
- 三項失敗都指向 `ARTICLE_CACHE_TOKEN = "agy-i18n-0-3-59"`，但 `app/web/article.html` 仍引用 `static/article.js?v=agy-auto-new-v1-20260724-015-01`。
- gate 失敗後 publisher 沒有 rollback；後續每 300 秒皆被 `PublishBlocked: repo worktree is not clean` 阻擋。
- 目前正式上線為 440 篇繁中、3 筆既有多語 locale record；第 4 筆韓文候選尚未上線。
- queue snapshot：196 states，170 complete、16 failed、10 active；10 active 中約 8 筆翻譯、2 筆新文。
- publisher ledger：75 published、52 quarantined、14 rewrite released、2 translation deferred、0 auto translation published。
- coordinator 每 60 秒仍會執行，但 Gemini runner 間歇出現 `JSONDecodeError`；失敗候選必須隔離，不能堵住已通過候選。

## Candidate fork

1. 首選：把 apply + gate + commit/push 做成可回復交易；gate 失敗時還原 publisher-owned changes，但保留 queue candidate、失敗證據與 retry/defer 狀態。
2. 若既有架構無法可靠 rollback：改為乾淨 staging worktree 驗證，只有 gate 通過才把 commit fast-forward 到正式 actor。
3. 不接受只手動清掉本次 dirty state，卻保留下一次仍會 deadlock 的症狀修補。

## Ownership and allowlist

可修改：

- `scripts/agy_content_publisher.py`
- `scripts/agy_multilingual_pipeline.py`
- `scripts/agy_gemini_coordinator.py`
- `scripts/install_agy_content_publisher_launchd.sh`
- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `ops/launchd/com.pantheon.agy-content-publisher.plist.example`
- `ops/launchd/com.pantheon.agy-gemini-coordinator.plist.example`
- `tests/test_agy_content_publisher.py`
- `tests/test_agy_multilingual_pipeline.py`
- `tests/test_agy_gemini_coordinator.py`
- 必要時與 cache-token invariant 直接相關的 `tests/test_web.py`、模板生成器及最小文件
- 本卡 evidence 目錄：
  `artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-PUBLISHER-DEADLOCK-REPAIR-20260724/`

若需要修改 allowlist 外檔案，先在卡片結果中列出理由並停下，不得擴張範圍。

## Forbidden scope

- 不新增文章、不改文章正文。
- 不升級 Gemini V4 為預設；V4 保持 shadow。
- 不刪除、重建或截短 queue、ledger、run states。
- 不使用 `git reset --hard`、`git checkout --` 或未保存證據的 destructive cleanup。
- 不把失敗翻譯標成通過，不降低 deterministic/review/release gate。
- 不 push、merge、deploy production；候選只交付完整 commit SHA，由 mainline 驗收整合。
- 不修改 GSC 憑證、Cloudflare、GitHub 權限或其他外部控制面。

## Required implementation

1. 建立能重現「apply translation → release gate fail → worktree remains clean or automatically recoverable」的回歸測試。
2. 修正 cache token 更新契約，使版本、HTML 引用與測試期望由單一來源一致更新。
3. 修正 publisher 交易邊界：
   - gate fail 不污染下一輪；
   - candidate 與 failure evidence 保留；
   - 已通過候選可繼續發佈；
   - failed/deferred 候選留到最後處理。
4. 修正 coordinator/runner 的 malformed JSON 隔離或 retry 邊界，避免單筆 runner 回應使整輪失敗；不得吞掉錯誤。
5. 提供目前 v0.3.59 actor 的無資料遺失 recovery runbook；不得直接在 implementation worktree 操作正式 actor。

## Verification

至少執行：

- 新增的 deadlock regression test（修復前可紅、修復後綠）
- `.venv/bin/python -m pytest tests/test_agy_content_publisher.py tests/test_agy_multilingual_pipeline.py tests/test_agy_gemini_coordinator.py -q`
- `.venv/bin/python -m pytest tests/test_web.py -q`
- `.venv/bin/python -m pytest -q`
- `git diff --check`
- `git status --short`

驗收 invariant：

- 模擬 gate fail 後，測試 repo 不留下 publisher-owned dirty files。
- 下一個 pass candidate 能在同一測試情境繼續處理。
- failed/deferred candidate 的 queue 與證據仍存在。
- cache token 在版本檔、模板與測試間一致。
- V4 預設路徑未改變。

## Evidence and delivery

Evidence path：
`artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-PUBLISHER-DEADLOCK-REPAIR-20260724/`

交付內容：

- root cause 與被否證假說
- changed-files allowlist 對照
- 測試指令、exit code、摘要
- actor recovery runbook
- 完整 candidate commit SHA
- `DELIVERED_CANDIDATE`；不得宣稱已整合、已上線或正式排程已恢復

## Stop conditions

- 同一 blocker 失敗 3 次立即停止，不做第 4 次。
- 無法保存現有 v0.3.59 candidate 或 queue/ledger 證據時停止。
- 修復需要 allowlist 外共享生成檔、外部控制面或 destructive cleanup 時停止並回報 mainline。

## Dispatch receipt

- provisioning source SHA：`41522076fccbe0406fb4d270d138368ce5c0395f`
- source branch/ref：Pantheon project default branch
- source clean：PASS
- Git metadata：worktree gitdir 可讀，`index.lock` 不存在
- unrelated dirty paths：`[]`
- formal thread ID：`019f9420-3ece-7cf2-84ee-66ebb64e0820`
- title：`Pantheon｜修復 Publisher Deadlock｜CARD-PANTHEON-PUBLISHER-DEADLOCK-REPAIR-20260724`
- thread status：`active / inProgress`
- sidebar/list visibility：PASS
- worktree cwd：`<codex-home>/worktrees/5d1f427e-e5c9-4c99-a501-a32aad1fe502/Pantheon`
- worktree exists：PASS
- worktree clean：PASS
- worktree HEAD：`41522076fccbe0406fb4d270d138368ce5c0395f`
- worktree 與 main cwd 不同：PASS
- runtime model override：依 `create_thread` 契約，使用者未指定模型，未強制覆寫；卡片保留 strict 建議跑道與 high-risk 理由
- Gate 1 card contract：PASS
- Gate 2 visible thread：PASS
- Gate 3 candidate delivery：PENDING
- Gate 4 independent review：PENDING
- Gate 5 mainline acceptance：PENDING
- workflow：`RUNNING`
