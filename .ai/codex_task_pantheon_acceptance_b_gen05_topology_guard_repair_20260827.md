---
id: CARD-PANTHEON-ACCEPTANCE-B-GEN05-TOPOLOGY-GUARD-REPAIR-20260827
title: 修補 gen05 topology guard authority
status: ready
chain_id: PANTHEON-ACCEPTANCE-B-GEN05-OUTLINE-TOPOLOGY
role: repair
cycle: 1
thickness: standard
risk: medium
model: gpt-5.6-terra
reasoning: medium
model_reason: 單一 validator seam 與固定正反向 regression，authority 裁決已由 exact production artifacts 閉合
parent_candidate: 6766fff999de7af09efc227230e69efd25795108
---

# Pantheon Acceptance B：gen05 topology guard authority bounded Repair

## 已核准 finding

- Owner 已接受 RCA 唯一主裁決：`TOPOLOGY_GUARD_OVERREACH`。
- gen05 persisted external plan 是 20:13:32 的正式 provider output；本次 continuation provider calls=0，只重新驗證既存 bytes。
- gen05 的 22 個 external `source_ref` 逐項對應同代 current `source-ref-map.json`，不是舊 generation allocation。
- prior authority 是 `attempts/03/locale-plan.json`。prior 與 gen05 normalized H2 wording 相同，但 authoritative item topology digest 不同：prior `ed536081443ad9b51237cce9c8f4d6dff93533f124f20a0926e255dfd98f2b0b`，gen05 `6cee3544f340cb4c5d62077d04bf375b2d6b42f3f8dd14693de6f133515c2a11`。
- prior headings 在 provider-time payload 明列為 `non_authoritative_hints`；structured topology authority 是 item/source identity 到 planned H2 slot 的 allocation。
- 現行 guard 單因 normalized heading equality 拒絕，將合法 semantic hint equality 誤判成 identity reuse。
- RCA：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN05-OUTLINE-TOPOLOGY-RCA-20260827-RESULT.md`。

## 目標

- topology rebuild guard 只拒絕 authoritative item mapping 重用，不得因 non-authoritative H2 wording／section hint 相同而拒絕。
- current mapping 不同但 H2 wording 相同時通過 topology guard；authoritative item allocation 相同時仍 fail closed。
- 讓既存 production-shaped gen05 artifact 可在 provider=0 fixture 通過這一道 guard；不得以改字、刪 artifact或重新呼叫 provider規避。

## 可改檔案

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- 唯一交付 receipt：`artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-ACCEPTANCE-B-GEN05-TOPOLOGY-GUARD-REPAIR-20260827.md`

## 禁止範圍

- 不修改 prompt、provider schema、source-ref-map authority、safety authority、semantic budget、continuation lifecycle、publisher、promotion、replacement、queue/state 或 runtime manifest。
- 不把 lifecycle replay secondary factor納入本 Repair；不得新增 terminalization、FSM、registry、database或通用 error taxonomy。
- 不刪改 production gen05 artifacts，不呼叫 planning/article/Reviewer/publisher provider，不建立 gen06，不 publish/tag/push/deploy。
- 不處理 forged gen07，不重裁 gen04 lifecycle 或 gen05 safety authority。

## 實作契約

1. 先新增 RED：prior/current H2 wording相同，但 authoritative item-to-H2 mapping不同時，現行 guard錯誤拒絕。
2. 最小修正 topology predicate：移除 heading wording equality 作為單獨 blocking authority；保留 authoritative item mapping equality 的 fail-closed判斷。
3. 負向 regression：當 authoritative item mapping相同，即使 wording不同或相同，仍須拒絕 rebuild reuse。
4. 使用 exact gen05 copied fixture 驗證 provider=0：通過原 topology guard；不得聲稱整條 generation完成，也不得觸發 article/reviewer/publish。
5. 不以變更 exception 文案、改幾個 H2 字、覆寫 persisted plan或 mock 掉 validator 使測試通過。

## 驗收

- source decision 前 CodeGraph task-semantic query；無結果或失敗才限域 `rg`。
- targeted RED→GREEN 與既有 topology/safety/continuation regression 全部通過。
- 完整 `tests/test_agy_multilingual_pipeline.py` 通過；若合理再跑完整 pytest，並記錄數量。
- exact fixture 證明：planning/article/reviewer/publish calls=0、semantic budget不變、production bytes before==after、gen06不存在。
- `git diff --check` 通過；實際 changed files 必須等於 allowlist。
- 建立單一 candidate commit，不 amend、不 push；回傳完整 SHA、parent、diff、測試與 residual risk。

## 停損

- 若修正必須改動 authoritative mapping定義、provider contract、lifecycle或 production state，立即停止並回主線；不得擴 scope。
- 若 exact fixture 通過 topology guard後暴露下一個 failure，只記錄 evidence 並停止，不得把下一個 finding吞入本 Repair。
