# Pantheon promotion legacy brief lane authority Repair 3

## 工作名稱

修正 current identity envelope 被 legacy translation brief 缺少 `lane` 阻塞。

## Root question

當 registry 已有合法 current `identity_envelope`，且 registry state 的 `lane` 與 envelope lane 完全一致時，legacy `translate_existing` brief 缺少 `lane` 不得否定該 current identity；若 state lane 缺失或不一致，必須 fail closed。

## 已閉合證據

- 零寫入 production plan 在 `auto-i18n-ja-4a9da72316d5d368eeb5` 失敗，錯誤為 `preserved run brief identity mismatch`；transaction root 未建立，promotion 未開始。
- 該 state 是 `failed`，current identity envelope 為 `translate_existing / i18n-rewrite / ASTRO-BASE-01`，registry state lane 也是 `i18n-rewrite`。
- canonical queue-owned `brief.json` 的 run ID、mode、article ID 全部一致，只有 legacy `lane` 為 `null`。
- `ff8d61a328b39c91de49cdc9b3c4bd9f77c08443` 曾有 `identity_envelope + state_lane` 的 bounded fallback；後續整合未保留此契約。

## Durable invariant

1. Current identity envelope 必須先完整通過 schema、lane allowlist、article IDs 與 digest 驗證。
2. `translate_existing` brief 若有 lane，必須與 envelope lane 完全一致。
3. `translate_existing` brief 若缺 lane，只能在 registry state lane 存在且與 envelope lane 完全一致時通過。
4. state lane 缺失、非法或不一致時 fail closed。
5. missing identity envelope 的 active state 仍 fail closed；Repair 2 的 terminal failed brief reconstruction 邊界不得放寬。
6. 不修改 queue、registry、brief、ledger 或 production。

## 唯一允許修改

- `scripts/pantheon_content_runtime_promotion.py`
- `tests/test_pantheon_content_runtime_promotion.py`

## 必做 RED

- 合法 current translation envelope + matching registry state lane + legacy brief lane missing：修復前 RED，修復後 plan PASS，且 queue/transaction 零變更。
- 同 fixture 的 registry state lane 缺失或 mismatch：持續 RED。
- active + missing identity envelope：既有 fail-closed regression 持續 PASS。

## 禁止範圍

- 不再清理或 quarantine production 資料。
- 不啟動七服務，不執行 promotion apply/finalize，不跑 A/B/C。
- 不新增 migration、cleanup、通用 compatibility framework。
- 不弱化 symlink、durable-root、ledger、terminal receipt 與 identity digest 防護。
- 不建立第二個 Repair task；回原 Repair task 執行。

## 驗證

- 新增 matching／missing-or-mismatch state lane regressions。
- `tests/test_pantheon_content_runtime_promotion.py` 全檔。
- `tests/test_pantheon_runtime_activation.py` 全檔。
- Python syntax check、`git diff --check`、production mutation count = 0。

## 交付

只交付 `DELIVERED_REPAIR_CANDIDATE`：candidate SHA、RED→GREEN、測試結果、clean state、production mutation count。不得 push、不得 promotion。
