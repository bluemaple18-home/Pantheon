# Integration v2.1 verification

## Required tests

工作目錄：`<integration-worktree>`

| 命令 | Exit code | 摘要 |
|---|---:|---|
| `.venv/bin/pytest tests/test_agy_seo_copy_pipeline.py -k 'standalone_answer or false_social_origin or repair_fields or bounded_create_repair or run_writer_reviewer'` | 0 | `10 passed, 88 deselected in 0.14s`。 |
| `.venv/bin/pytest tests/test_agy_seo_copy_pipeline.py tests/test_agy_gemini_coordinator.py tests/test_agy_content_publisher.py` | 0 | `192 passed in 71.20s`。 |
| `.venv/bin/pytest tests/test_web.py` | 0 | `71 passed, 2 warnings in 27.03s`；warnings 為既有 invalid escape 與 Starlette/httpx deprecation。 |
| `bash -n scripts/install_agy_content_publisher_launchd.sh` | 0 | shell syntax 通過。 |
| `plutil -lint ops/launchd/com.pantheon.agy-content-publisher.plist.example` | 0 | `OK`。 |
| `git diff --check baa29d87fd472da5ceeea7b10a1eaf7311baa8b5 HEAD` | 0 | Finalization 前發現 card EOF blank-line 並在 current card allowlist 內修正；final rerun 通過。 |

## Provenance and equivalence checks

| 檢查 | Exit code | 摘要 |
|---|---:|---|
| `git rev-list --count baa29d87...39a3a9f...` | 0 | 3 commits。 |
| candidate delta path count | 0 | 精確 27 paths。 |
| candidate 27-path blob equivalence：`39a3a9f...` vs final tip | 0 | 無差異。 |
| `git diff --quiet 39a3a9f... HEAD -- uv.lock` | 0 | 無差異。 |
| `git merge-base --is-ancestor baa29d87... HEAD` | 0 | verified remote main 是 final tip ancestor。 |
| `git merge-base --is-ancestor 39a3a9f... HEAD` | 0 | reviewed candidate 是 final tip ancestor。 |
| `git merge-base --is-ancestor f432f078... HEAD` | 1 | 預期結果；excluded local fork 不是 final tip ancestor。 |
| `git diff --name-only 39a3a9f... HEAD` allowlist | 0 | 只含 current Integration card 與四份 current evidence。 |
| final branch tip | 0 | branch tip 等於 final `HEAD`。 |
| final full status / index lock | 0 | clean；lock absent。 |

## Candidate protection

- Candidate code、tests、docs、plist、installer與舊 evidence 未修改。
- Candidate 既有 27-path delta完整存在且 blob-equivalent。
- 未執行 formatter、uv、Node install或 lockfile update。
- Local `f432f078...` 未成為 ancestor、parent或patch source。

## Verification decision

全部 required verification 與 provenance checks 通過。結果只支持
`DELIVERED_INTEGRATION_CANDIDATE`，不支持已整合或 production fixed。
