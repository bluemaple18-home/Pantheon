---
id: CARD-PANTHEON-G8-CAPACITY-PREFLIGHT-ESERVERERROR-RCA-20260821
chain_id: PANTHEON-G8-PRODUCTION-PREACTIVATION-RECONCILIATION-20260820
parent_card_id: CARD-PANTHEON-G8-LIVE-PUBLISHER-IDENTITY-RECONCILIATION-20260821
role: repair
cycle: 3
status: ready
type: read_only_diagnosis
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
ownership:
  - .work/CARD-PANTHEON-G8-CAPACITY-PREFLIGHT-ESERVERERROR-RCA-20260821/**
forbidden_scope:
  - 重跑 capacity installer preflight 或 activation-only
  - source、plist、launchctl、queue、state、transaction、content、tag、push mutation
  - replacement Repair thread、修 code、猜測後直接 retry
evidence_path: .work/CARD-PANTHEON-G8-CAPACITY-PREFLIGHT-ESERVERERROR-RCA-20260821/
---

# G8 capacity preflight eServerError RCA

## 工作名稱 → 正在做什麼 → 現在狀態

定位 capacity preflight `eServerError` → 拆成最小唯讀 launchctl／capacity seam → `READY TO DISPATCH TO EXISTING REPAIR THREAD`

## Root Question

Cycle 19 的正式 `--preflight` 為何在零秒內 exit 70／`Operation failed with error: eServerError`；故障位於 launchd session、特定 service lookup、capacity probe、plist identity，還是 wrapper command contract？

## 已保存 RED

- evidence commit：`3c019f3a6a`
- red-capable command：正式 capacity installer `--preflight`，單次 exit 70；本卡禁止重跑。
- before/after 完全一致；七服務 loaded/no-PID；production mutation、activation、canary、retry皆 0。

## 診斷契約

1. 只在原 Repair thread `01a01e5e-025e-7721-8cc9-0c72d66dbc86` 執行。
2. 限域靜態列出正式 preflight 會呼叫的 read-only system probes；不得再讀整份 source。
3. 建立最小 probe matrix：每個唯讀 launchctl query／capacity observation各執行一次並記 exit/stdout/stderr；不得 bootout/bootstrap/kickstart/enable/disable。
4. 排序至少兩個可證偽假說，逐一用單一 probe 排除；不可用完整 installer作 probe。
5. 將 root cause 定位到具體 command＋layer；若不可重現，記錄時間、session target、UID、host與差異條件，不得宣稱已修復。
6. 交付 `probe-matrix.json`、`hypotheses.json`、`final-receipt.json`；`git diff --check`。

## 停損

- 任一 probe 需要 mutation或全流程 retry：`BLOCKED / DIAGNOSTIC_BOUNDARY`。
- 相同 read-only probe不得重跑；證據不足就回 `INCONCLUSIVE / NO MUTATION`。

## 完成定義

`ROOT_CAUSE_LOCALIZED / NO MUTATION` 或 `INCONCLUSIVE / NO MUTATION`；不得啟動下一個 production attempt。

