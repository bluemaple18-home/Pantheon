---
id: CARD-PANTHEON-SWAP-TELEMETRY-CAPACITY-RCA-20260818
chain_id: PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-20260818
parent_card_id: CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-PRODUCTION-CANARY-20260818
role: diagnostic
cycle: 1
status: ready
type: readonly_diagnostic
thickness: minimal
risk: medium
model: gpt-5.6-luna
reasoning: medium
model_reason: blocker 已固定為 swap telemetry unavailable；只需 bounded 環境對照與正式 capacity exercise，不做架構或 production 決策，使用 Luna medium 節省。
blocked_canary_evidence_sha: 92e79845c748c467cf22368dcfad556381dd7c26
ownership:
  - .work/CARD-PANTHEON-SWAP-TELEMETRY-CAPACITY-RCA-20260818/**
forbidden_scope:
  - 修改 source、tests、rules、capacity policy、receipt schema 或降低 PASS 門檻
  - push、runtime promotion、LaunchAgent mutation、發布、tag、transaction 或 queue/state/plist/barrier 變更
  - 另開 canary／Repair／Reviewer task、手寫 PASS receipt、重用舊 source receipt 冒充 current evidence
verification:
  - 同一 host、同一 source、同一正式 capacity exercise，在 sandbox 與獲准 read-only host telemetry 邊界各跑一次
  - 保存 sysctl vm.swapusage、memory pressure/host free、兩週期 capacity receipt與 exit status
  - 若 host telemetry 可讀且正式 exercise PASS，判 SANDBOX_FALSE_NEGATIVE；否則 REAL_NO_GO
  - git diff --check、production mutation=0、evidence commit、worktree clean
evidence_path: .work/CARD-PANTHEON-SWAP-TELEMETRY-CAPACITY-RCA-20260818/
---

# Swap telemetry capacity blocker RCA

## 工作名稱 → 正在做什麼 → 現在狀態

判定 swap telemetry blocker → 對照 sandbox 與 host read-only telemetry → `READY / READ-ONLY`

## Root Question

Publisher-only canary 的 capacity `NO-GO` 是 sandbox 無法讀 `vm.swapusage` 的假陰性，還是 host/正式 capacity exercise 真正缺少必要 telemetry？

## 已知失敗

- Canary task `01a013e9-9c66-7133-99e6-6d1694cb4dca` 在 production mutation 前停止。
- Blocked evidence commit：`92e79845c748c467cf22368dcfad556381dd7c26`。
- 兩個 capacity cycle 都回 swap telemetry unavailable；actor 未變、transaction/tag/push/activation 都是 0。

## 執行步驟

1. 唯讀讀 blocked receipt、capacity receipt、正式 capacity command、source SHA與環境錯誤。
2. 建立單一 red-capable loop：同一正式 capacity exercise 在 sandbox 回 `NO-GO / swap unavailable`。
3. 只改一個變數：以獲准的 read-only host boundary 讀 `sysctl vm.swapusage`，並用全新 evidence root重跑同一正式 capacity exercise。
4. 比較 command、source、inputs、兩週期、host free/RSS/swap、cleanup與 stop-loss；除執行權限邊界外不得不同。
5. 結論：
   - `SANDBOX_FALSE_NEGATIVE`：host telemetry 可讀且正式 exercise `PASS`；交 current receipt path/digest與原 canary resume 條件。
   - `REAL_NO_GO`：host telemetry仍不可讀或 exercise非 PASS；交 exact root cause與唯一下一步，不修改 gate。
6. 只提交 evidence；不得直接 resume canary或做 production mutation。

## 停損

- 同一 blocker最多三次；第三次停止。
- 不得用手工填 swap 數字、舊 receipt、mock 或省略 telemetry 取得 PASS。
- 若正式 exercise 本身需要 source repair，回 `REAL_NO_GO / SOURCE_REPAIR_REQUIRED`，不在本卡修。

## 交付

- verdict
- sandbox/host commands and outputs
- current capacity receipt path/digest/status
- canary resume conditions
- production mutation=`0`
- evidence commit SHA
