# Preflight evidence

## Thread and worktree

- status: `RUNNING`
- thread_id: `019fab58-0c2f-7223-ac89-bb0adb865f54`
- thread_host_id: `slingshot:env_e_6a17b3781858832daee8697c30fc7e7c`
- thread_status: `active_in_progress`
- worktree: `<codex-worktrees>/93954b6b-3be2-487a-a673-e1fa05d2adef/Pantheon`
- worktree registered: `true`
- worktree differs from main workspace: `true`
- clean at thread creation: `true`（由主線正式 thread receipt 驗證）
- current expected dirt: 僅本卡與本卡 evidence
- branch: detached HEAD
- HEAD: `baa29d87fd472da5ceeea7b10a1eaf7311baa8b5`
- reference SHA exists: `true`
- reference SHA is current HEAD: `true`
- index lock: `absent`
- gate_1_card_contract: `passed`
- gate_2_visible_thread: `passed`

## Baseline contract

`git show --stat baa29d87fd472da5ceeea7b10a1eaf7311baa8b5`：

```text
baa29d87f fix(content): stabilize new lane quality repairs
 scripts/agy_seo_copy_pipeline.py    | 110 ++++++++++++++++++++++++-
 tests/test_agy_seo_copy_pipeline.py | 158 ++++++++++++++++++++++++++++++++++++
 2 files changed, 267 insertions(+), 1 deletion(-)
```

判定：`PASS`。目前 baseline 正好是指定 reference SHA，包含所要求的新文品質 repair 內容契約；沒有搬入主工作區 dirty state。

## Capability preflight

執行：

```bash
bash ${AI_CORE_DIR:-$HOME/ai-core}/scripts/worktree_capability_preflight.sh --check --root <repo-root>
bash ${AI_CORE_DIR:-$HOME/ai-core}/scripts/worktree_capability_preflight.sh --prepare --root <repo-root> --require-python-tests
```

`--check` 結果：

```text
worktree_registered=true
python_tests=needs_prepare
node_tests=needs_prepare
codegraph=degraded:fallback_rg
```

`--prepare` 第一次在受限 sandbox 內因共用 `uv` cache 權限與套件 registry DNS 限制失敗。依 sandbox 規範，以相同命令取得提升權限後重跑；第二次成功：

```text
worktree_registered=true
python_tests=ready
node_tests=ready
codegraph=degraded:fallback_rg
```

同一 blocker 失敗次數：`1`。未達停損門檻。

## Code intelligence

CodeGraph 對此平台 worktree 未初始化，與 capability preflight 的 `degraded:fallback_rg` 一致。未在 allowlist 外建立 `.codegraph`；後續只以 `rg` 與限定範圍讀取做 fallback。

## Preflight decision

```text
status: GO
baseline: exact reference SHA
worktree isolation: verified
git metadata: healthy
python tests: ready
production actions: none
```
