---
id: APF-004-FRESH-CAPACITY-AFTER-SWAP-REPAIR-EXECUTION-20260816
title: swap repair 後單次 fresh capacity execution
status: review_required
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: executor
cycle: 1
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
parent_candidate: a6b2334a2bff1a55c5201e26a4867c692ec45db8
---

# APF-004｜Swap repair 後 fresh capacity one-shot

## 權威與目的

- capacity guard 的 macOS swap fallback repair 已整合於 `origin/main=a6b2334a2bff1a55c5201e26a4867c692ec45db8`。
- 舊 fresh-capacity authority 與 correlation 已消耗，不得沿用。
- 本卡只鎖定新的 canonical payload；目前不授權執行 capacity preflight。
- 新 correlation：`apf004-fresh-capacity-after-swap-repair-a6b2334a2b-20260815T160546Z`。

## 已驗證 delivery

- working directory 鎖定 `<repo-root>`。
- interpreter 鎖定 `<repo-root>/.venv/bin/python`，argv 固定 `-E`。
- reviewed module SHA-256 為 `8dc8b4a00c70a0a6e18ca3255be433c8751abb128856ae509560e692f0f17916`。
- import、public `--help`、formal manifest read 與 mocked Darwin fallback seam 均 PASS。
- 上述驗證未帶 `preflight` subcommand；`capacity_preflight_calls=0`。

## 後續一次性執行契約

1. 必須先取得 Reviewer 對本卡與新 canonical payload 的明確核准。
2. clean detached checkout exact reviewed source，重新驗 cwd、interpreter、module、formal actor/manifest/barrier 與 execution evidence root absent。
3. 只可使用 `canonical-payload.json`；重算 compact canonical digest必須 exact。
4. fresh capacity `preflight` 恰好呼叫一次，禁止 retry。
5. 非零、ambiguous 或 status 非 `PASS`，立即 `STOPPED_NO_RETRY`。
6. evidence 只寫 `artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/fresh_capacity_after_swap_repair_execution_20260816/`。
7. 保存 pre/post snapshot、stdout/stderr、call trace、result、mutation summary、sanitizer 與 digests；candidate commit，不 push。

## 禁止範圍

- uv、Publisher reload、launchctl、Gate B、publication、create/run/select、business transaction、tag、push、schedule。
- 修改 runtime actor、manifest、queue、state、production config 或 Python environment。
- 第二次 capacity call、舊 authority/correlation/evidence replay。

## Verdict

- `READY_FOR_NEW_FRESH_CAPACITY_REVIEW`
- execution status：`not_executed`
- production mutation：0
