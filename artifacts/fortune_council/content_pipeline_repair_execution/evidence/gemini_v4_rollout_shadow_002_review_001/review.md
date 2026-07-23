# Gemini V4 Shadow-002｜Independent Limited Rollout Review

## Findings

未發現阻塞問題；未識別 P0–P3 具體 finding。

## Spec axis

- 固定 identity 通過：candidate
  `2e221546b9de8dba3498201f78b86831bacffe44` 的唯一 parent 精確為
  `6706ae3a28eb601fdf4c8b97531173138f67ef37`；Review provisioning commit
  `b2d2a0457ebbbcf665dc41bedd2a146b7df4d315` 緊接 candidate。
- 啟動 worktree 獨立、clean、detached；provisioning branch 指向起始 HEAD；
  實際 gitdir 無 `index.lock`。
- `shadow-verifier.py` 不 import production broker／runner，也未呼叫外部 CLI；
  對 real bundle 的獨立執行結果為 `PASS`。
- 由 closed-schema parsed result與 `canonical-json-newline-v1` 重建 stdout：
  `59 bytes`，SHA-256
  `28c08d3d33806babce80bb457b636b41c9ab97595b7ff1c300a2a71440e152f5`，
  與 execution／control 完全一致。
- 由 `preflight.md` 固定 prompt 重算：`185 bytes`，request SHA-256
  `5317d8ebdb3e52f47924bf8bf6266163a24960317e9c8cdeb4d3f0a4cc13753a`；
  operation ID 為其前 40 hex，並與 receipt／command／inbox 綁定。
- 獨立 canonicalize 五個 ledger frame後，ledger SHA-256為
  `0d5130546f7c70f56e64c742eecb097205cdb2aae276db3865c31b5e65bc04b9`；
  event chain與 final anchor
  `03c56ce06e79c45c1e5e6a3d036ec871e8db1ee55066b62e61aadc70f875e621`
  通過。
- receipt／command／operation／item／attempt／request／model／profile／executable
  digest均一致；target invocation／process為 `1/1`，retry／fallback／automatic
  resend／second call為 `0/0/0/0`。
- Real bundle沒有 raw stdout、prompt、credential、本機路徑、完整環境或 CLI log；
  privacy flags全為 false，forbidden-value scan無命中。
- 三種 encoding `3/3 accepted`；13 mutations `13/13 rejected`。
- Regression為 `137 unique passed`：V4 focused 74、legacy publishing 57、
  coordinator 6。Targeted flag-off legacy／flag-on no-fallback另重跑6項，已包含於
  V4 74，不重複計數。

## Standards axis

- Base-to-candidate實際 changed files為13個，與 candidate `changed-files.txt`
  完全一致，且全部只在 Shadow-002卡與其 evidence allowlist內。
- Candidate沒有修改 production code、tests、其他 docs、既有 evidence、文章、
  registry、queue或automation。
- Recorder／verifier `py_compile`、candidate與Review `git diff --check`、debug
  marker與privacy scan均通過。
- Review期間外部 Gemini／agy invocation為 `0`；沒有repair、activation、merge、
  push、deploy、publish或default promotion。

## Open questions

無。

## Remaining risks

- 證據只涵蓋一次 public sanitized real canary；不能推論長時間、不同payload或批次
  行為。
- Evidence依privacy契約不保存executable path或binary。本Review可獨立核對digest在
  receipt／command／executable identity間的一致性，並核對production broker會在
  執行前hash已驗證snapshot；但無法從bundle重新hash當次binary本體。
- Provider internal model-call provenance仍為 `UNKNOWN`；process count只證明broker
  確認一個target process。
- GO只表示主線可以另開activation卡，考慮仍預設關閉、明確opt-in、極小受限範圍。
  Flag off必須維持legacy，flag on失敗不得fallback；不得直接切預設或發布文章。
