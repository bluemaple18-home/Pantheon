---
id: CARD-CONTENT-WRITER-VNEXT-CANARY-ACTOR-REPAIR-001
status: ready
chain_id: CONTENT-WRITER-VNEXT-RUNTIME-ACTIVATION
role: repair
cycle: 1
execution_line_id: WRITER-VNEXT-PRODUCTION-CANARY-001-RETRY-1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
candidate_sha: b771c0574d2779c5f3d3d6bdb36846847561ff06
review_sha: ad71809d1011b1c735566e974cdd6afc0787ea7b
depends_on:
  - CARD-CONTENT-WRITER-VNEXT-CANARY-ACTOR-REVIEW-001@ad71809d1011b1c735566e974cdd6afc0787ea7b
---

# Writer vNext Canary Actor Repair 001

## 目標

修復獨立 Review 的唯一 P1：runtime manifest 的 `actor_head` 目前只驗格式，沒有與 `actor_root` 實際 Git HEAD 比對，stale manifest 可能誤通過。

## 固定 Finding

- 位置：`scripts/pantheon_content_runtime_manifest.py:180`
- 重現：commit A 建 manifest；actor root 前進到 commit B；`load_manifest(manifest, expected_digest)` 仍 PASS。
- 風險：違反 actor HEAD drift fail-closed；削弱 exact-SHA identity。
- 同步缺口：確認 manifest `python_executable` 與部署／Publisher 實際使用的 Python 一致。

## 修復契約

1. manifest 含 `actor_head` 時，必須確認 `actor_root` 是乾淨 Git worktree，實際 `HEAD` 精確等於 manifest SHA；不符、非 repo、git 失敗皆 fail closed。
2. 保持舊 manifest 相容：沒有 `actor_head` 的既有 schema 行為不得無故破壞。
3. Canary deployment/preflight 必須確認 manifest `python_executable` 與實際執行 Python／installer 使用的 Python一致；漂移 fail closed。
4. 不得把驗證變成 production mutation；所有新測試只用 temp repo／temp executable。
5. 修復必須最小，不重構無關 actor、Publisher 或 manifest 流程。

## 可改檔案

- `scripts/pantheon_content_runtime_manifest.py`
- `scripts/install_agy_content_publisher_launchd.sh`
- `scripts/prepare_pantheon_canary_actor.py`（僅必要時）
- `tests/test_pantheon_content_runtime_manifest.py`
- `tests/test_prepare_pantheon_canary_actor.py`
- `tests/test_agy_content_publisher.py`（僅 installer／preflight 契約需要）
- `artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/canary_actor_repair_001/**`

## 禁止範圍

- 不得改 Review card、原 candidate evidence、docs 或其他 source。
- 不得建立真實 actor root、不得 `launchctl`、不得碰 production queue/state/model/run/publish/tag/push/deploy。
- 不得修改 reservation DB、Codex global state、其他 task/worktree。

## TDD／驗證

1. RED：actor manifest 建於 A、actor root 前進 B，load/preflight 必須先證明現況錯誤。
2. GREEN：A/A 通過；A/B、dirty actor、非 repo、git failure 全數 fail closed。
3. Python：manifest Python 與實際 deployment Python 相同才通過；不同、symlink/不存在/不可執行皆拒絕。
4. 重跑原 136 targeted tests，加上新負向測試；另跑 `py_compile`、shell syntax、JSON parse、`git diff --check`、allowlist。
5. 保存 RED/GREEN、negative matrix、changed files、verification receipt。

## 交付

- 單一 repair candidate commit SHA。
- 只回 `DELIVERED_REPAIR_CANDIDATE` 或具證據的 `BLOCKED`。
- 不得宣稱 Review 已 GO、production actor 已建立或 Canary 已執行。
