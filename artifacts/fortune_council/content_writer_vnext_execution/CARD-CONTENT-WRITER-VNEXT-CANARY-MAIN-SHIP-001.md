---
id: CARD-CONTENT-WRITER-VNEXT-CANARY-MAIN-SHIP-001
status: ready
chain_id: CONTENT-WRITER-VNEXT-RUNTIME-ACTIVATION
role: ship
cycle: 1
execution_line_id: WRITER-VNEXT-PRODUCTION-CANARY-001-RETRY-1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
depends_on:
  - CARD-CONTENT-WRITER-VNEXT-CANARY-ACTOR-HOST-PROVISION-001@521e813a92f0ac51f09627869a0c18ffb01e462c
---

# Writer vNext Canary Main Ship 001

## 目標

將已 Review GO、已驗證的本機 integration branch 發布至 GitHub，建立 PR、確認檢查後合併到 `origin/main`，讓固定 actor SHA `752c15d241a166032338d2ca0ad962e91b51d08e` 成為遠端 main ancestor。

## 固定範圍

- head branch：`codex/pantheon-canary-actor-integrated-20260812`
- base branch：`main`
- remote：`origin` → `bluemaple18-home/Pantheon`
- integration head：本卡 commit
- actor SHA：`752c15d241a166032338d2ca0ad962e91b51d08e`
- 完整發布範圍：`origin/main..HEAD`；不得漏掉 actor 依賴的既有本機 mainline commits。

## 執行契約

1. 再核對 clean、remote、GitHub auth、完整 commit/file scope與 actor SHA ancestry。
2. 重跑 targeted 143 tests、shell syntax、py_compile、`git diff --check`。
3. push head branch；建立 ready PR（非 draft），PR body 列變更、根因、驗證、production 禁止範圍。
4. 檢查 PR mergeability 與 checks；紅燈先停止並回證據，不得 bypass required checks。
5. checks 通過後 squash/merge 或 merge commit依 repo policy合併；不得 force push。
6. 合併後 fetch，證明 `752c15d...` 為 `origin/main` ancestor，保存 PR URL與 merge SHA。

## 禁止範圍

- 禁止修改 source/tests/docs/evidence、重寫歷史、force push、繞過 branch protection。
- 禁止 launchctl、模型、run、Publisher transaction、文章、tag、deploy。
- 禁止碰使用者 dirty 主 checkout；只在本任務乾淨 worktree 操作。

## 交付

- `MERGED_TO_ORIGIN_MAIN` 或具證據的 `BLOCKED`。
- 回 branch、PR URL、checks、merge SHA、`origin/main` ancestry proof。
- 合併完成後不執行 Canary；主線另行重建 actor manifest與重跑 preflight。
