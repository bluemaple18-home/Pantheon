---
id: APF-004-FRESH-CAPACITY-DIRECT-VENV-EXECUTION-20260815
title: 以既有 venv 執行單次 fresh capacity
status: review_required
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: implementation
cycle: 1
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
parent_candidate: e07b064659
---

# APF-004｜Fresh capacity direct venv execution

## 根因與權威

- 前次 Publisher reload 已成功，正式 identity 已對齊；不得再次 reload。
- uv `0.9.25` 在 macOS system-configuration dynamic store 初始化時 panic，兩次都發生於 Python/module 啟動前。
- `capacity_preflight_calls=0`；因此尚未消耗一次正式 fresh capacity 呼叫，但本卡本身不授權執行。
- Publisher reload blocker evidence 已整合於 `origin/main=e07b06465909bac587ac2d26de29895d1eacf59d`。

## 已驗 delivery seam

- 既有 `<repo-root>/.venv/bin/python` 可直接啟動 Python `3.12.12`。
- 可 import `scripts.pantheon_content_capacity_guard`，並可由 public module `--help` 正常解析 CLI；兩項皆未呼叫 `preflight()`。
- 在完整 formal runtime env 下，可唯讀載入 exact manifest並核對 actor、manifest、runtime identity；production state 未寫入。
- `scripts/pantheon_content_capacity_guard.py` 與 runtime manifest validator 自 formal actor `a6c4b798...` 以來無 source diff。

## 後續單次執行契約

1. 必須先取得 Reviewer `READY_FOR_ONE_FRESH_CAPACITY`。
2. clean detached checkout 當時 exact `origin/main`；重新驗 Publisher identity、formal actor/manifest/barrier、queue/state 與 future evidence root 未漂移。
3. exact payload 取自 `fresh_capacity_delivery_repair_plan_20260815/exact-next-command.json`，digest 必須為 `0c9ef41831eea98fccd7570534fe9bdaa0ad0ebe6847276cb7a03c2c9bb3957e`。
4. 不得呼叫 uv；直接使用既有 `<repo-root>/.venv/bin/python` public module入口。
5. fresh capacity `preflight` 恰好呼叫一次；非零、ambiguous 或非 `PASS` 即停止，不得 retry。
6. 唯一 evidence root：
   `artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/publisher_fresh_capacity_direct_venv_20260815/`
7. 保存 pre/post snapshot、stdout/stderr、capacity payload、call trace、mutation summary、sanitizer與 digests；candidate commit，不 push。

## 嚴格禁止

- Publisher install/reload、launchctl mutation、kickstart、rollback。
- uv invocation、第二次 capacity call、舊 Gate B command/evidence replay。
- Gate B、publication、create/run/select/business transaction/tag/push/schedule。
- 修改 production config、Python environment、runtime actor、manifest、queue或state。

## Verdict

- 本卡 readiness：`READY_FOR_ONE_FRESH_CAPACITY_REVIEW`。
- 本卡執行狀態：`not_executed`。
