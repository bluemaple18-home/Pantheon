---
id: CARD-PANTHEON-G8-ACTIVATION-ONLY-EXIT-78-CONTRACT-CLARIFICATION-20260822-RESULT
card_id: CARD-PANTHEON-G8-ACTIVATION-ONLY-EXIT-78-CONTRACT-CLARIFICATION-20260822
status: delivered_candidate
date: 2026-08-22
---

# G8 Activation-Only Exit 78 Contract Clarification Result

## Current State

`DELIVERED_CANDIDATE / NO PRODUCTION`

## Contract Clarification

- State Contract 將 activation-only inert terminal exit 的唯一合法集合鎖定為 absent、`0`、`78`。
- `78` 只適用於 `TE-TARGET-STAGED-TO-QUIESCED` 的 old-live activation-only wrapper／barrier validation，且必須同時有 target-newer/current stage、current receipts、loaded/no-PID 與 exact live plist path。
- `child_policy=forbidden` 明確禁止 production workload child；child spawn 前的 activation wrapper validation 不屬於 production workload child。
- Edge Map 將上述條件寫入 postcondition 與 fail-closed boundary；其他 nonzero、PID、path drift、normal mode 或 generation mismatch 仍拒絕。

## Executable Evidence

- `tests/test_pantheon_content_capacity_guard.py` 的 deterministic regression 驗證 absent、`0`、`78` 接受。
- 同一 regression 驗證其他 nonzero、PID present 與 observed plist path drift 拒絕，且沒有 mutation log。
- 未修改 runtime、installer 或 Capacity implementation。

## Verification

- `.venv/bin/python -m pytest tests/test_pantheon_content_capacity_guard.py -q`：`52 passed`。
- `.venv/bin/python -m pytest tests/test_pantheon_g8_production_preactivation.py -q`：`41 passed`。
- contract/reference scoped `rg`：State Contract、Edge Map 的 exit set、production child、old-live/target-newer、PID/path fail-closed references 全部存在。
- `git diff --check`：PASS。
- tracked diff allowlist：PASS；只有本卡允許的四個檔案。

## Tooling Receipt

CodeGraph 已先查詢，但此 worktree 未初始化 index；依任務卡改採 allowlist 與直接相關 executable contract 的限域讀取。

## Remaining Risk

本 candidate 只澄清既有 normative／executable contract，不執行 Cycle 35、production、merge 或 push。後續整合仍需主線獨立 review。
