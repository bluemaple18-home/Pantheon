---
id: CARD-PANTHEON-CAPACITY-GUARD-PREACTIVATION-TRANSITION-REVIEW-20260818
chain_id: PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-20260818
parent_card_id: CARD-PANTHEON-CAPACITY-GUARD-PREACTIVATION-TRANSITION-REPAIR-20260818
role: reviewer
status: ready
type: review
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
candidate_sha: bac5eacb6e49d02e626333574bc81361ed2a42e9
base_sha: 227c07179d66f01675b043f30a9b904c61cb0b2f
review_scope:
  - scripts/install_pantheon_content_capacity_guard_launchd.sh
  - scripts/pantheon_content_capacity_guard.py
  - tests/test_pantheon_content_capacity_guard.py
  - .work/CARD-PANTHEON-CAPACITY-GUARD-PREACTIVATION-TRANSITION-REPAIR-20260818/evidence.md
forbidden_scope:
  - 修改 candidate、production、LaunchAgent、runtime manifest、文章、transaction、tag、push
  - 用單次 GREEN 取代 fail-closed contract review
verification:
  - transition fallback 只在精確 loaded/no-PID RSS unknown 症狀觸發
  - stage contract 綁 manifest/generation/digest/barrier/live activation-only plist/control identity
  - normal、unknown、malformed、stale 全部 NO-GO
  - stage success 無 bootout/bootstrap/kickstart
  - 一般 capacity preflight 未放寬
  - scope/複雜度合理，測試非自我實現
---

# Review：Capacity Guard preactivation transition

## 工作名稱 → 正在做什麼 → 現在狀態

審查 `bac5eacb6e` → 驗證 transition contract、安全邊界與測試可信度 → `READY / REVIEW`

## Root Question

此 candidate 是否以 fail-closed、可重現且不放寬一般容量閘門的方式，解除 promoted manifest 與舊 activation-only live plist 之間的純 staging 循環鎖死？

## Review 契約

1. 唯讀檢查 `base..candidate`，不得修改。
2. 先看 source decision、trigger 精確性、TOCTOU、plist/barrier/manifest identity 綁定。
3. 確認 fallback 不接受任意 no-PID、其他 preflight error、缺 identity 或非 activation-only live shape。
4. 確認 installer 成功只 stage，無 launchctl mutation。
5. 獨立重跑正向、六類負向、capacity 全檔、runtime manifest/promotion、bash-n、diff check。
6. 審查新增約 450 行是否存在可導致錯誤的重複/過度複雜；只有實質風險列 finding。
7. 輸出 `GO` 或 `NO-GO`；finding 必須含 ID、P0/P1/P2、檔案/行、repro、修復邊界。
8. 不得整合、不得 production mutation。

## 停損

- P0/P1 → `NO-GO`，回同 Repair thread。
- 無 P0/P1 → `GO`，主線才可整合；production canary 仍需另行續跑。
