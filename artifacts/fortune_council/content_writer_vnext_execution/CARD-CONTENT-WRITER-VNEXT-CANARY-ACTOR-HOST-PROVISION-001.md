---
id: CARD-CONTENT-WRITER-VNEXT-CANARY-ACTOR-HOST-PROVISION-001
status: ready
chain_id: CONTENT-WRITER-VNEXT-RUNTIME-ACTIVATION
role: implementation
cycle: 1
execution_line_id: WRITER-VNEXT-PRODUCTION-CANARY-001-RETRY-1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
depends_on:
  - CARD-CONTENT-WRITER-VNEXT-CANARY-ACTOR-REPAIR-001@752c15d241a166032338d2ca0ad962e91b51d08e
---

# Canary Actor Host Provision 001

## 目標

使用已 Review GO 的 repo-owned CLI，在本機建立隔離 Canary actor runtime；只建立 actor worktree、空 queue/state/log 與 runtime manifest，不啟動服務或執行 Canary。

## 固定輸入

- repo root：`<repo-root>`（任務 worktree）
- sandbox root：`/Users/mattkuo/Documents/Pantheon-canary-runtime`
- actor root：`/Users/mattkuo/Documents/Pantheon-canary-runtime/actor`
- queue root：`/Users/mattkuo/Documents/Pantheon-canary-runtime/queue`
- state root：`/Users/mattkuo/Documents/Pantheon-canary-runtime/state`
- log root：`/Users/mattkuo/Documents/Pantheon-canary-runtime/logs`
- manifest：`/Users/mattkuo/Documents/Pantheon-canary-runtime/runtime-manifest.json`
- Python：`/Users/mattkuo/.local/share/uv/python/cpython-3.11.14-macos-aarch64-none/bin/python3.11`
- actor SHA：`752c15d241a166032338d2ca0ad962e91b51d08e`
- remote ref：`origin/main`
- exact run：`auto-new-v1-20260812-001-01`

## 執行契約

1. 先做容量快照；host reserve、worktree count/bytes 不合格即停止。
2. sandbox root 不存在才可建立；若已存在未知資料，fail closed，不刪除、不覆寫。
3. 依序跑 `plan` → `prepare` → `preflight`；保存三份 JSON receipt。
4. actor HEAD 必須等於固定 SHA且 clean；manifest digest、actor identity、Python realpath、exact selector、`--max-runs 1` 全部一致。
5. queue/state/log 必須為空或 CLI 定義的 prepared-empty 狀態。
6. 完成後重跑 host capacity，並確認 remote refs、主 checkout、launchd 與 production roots未改。

## 禁止範圍

- 禁止 launchctl、LaunchAgents、模型呼叫、run 建立、Publisher transaction、文章、tag、push、deploy。
- 禁止修改 repo source、tests、docs、卡片或 commit。
- 禁止使用 production queue/state/log；只准固定 sandbox。
- 禁止刪除或覆寫任何既有未知資料。

## Evidence

寫入 sandbox 的 `evidence/`：`capacity-before.json`、`plan.json`、`prepare.json`、`preflight.json`、`capacity-after.json`、`host-noop.json`、`verification.md`。

## 交付

- `PROVISIONED_NOT_RUNNING` 或具證據的 `BLOCKED`。
- 回 actor root、HEAD、clean、manifest digest、exact run、Publisher plan與剩餘阻擋。
- 不得宣稱 Canary 已執行或 production 已啟動。
