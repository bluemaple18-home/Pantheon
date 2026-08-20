---
id: CARD-PANTHEON-G8-CYCLE17-PREFLIGHT-CONTRACT-CORRECTION-20260821
chain_id: PANTHEON-G8-PRODUCTION-READINESS-20260820
parent_card_id: CARD-PANTHEON-G8-CYCLE17-PREFLIGHT-NO-GO-PARAMETER-RCA-20260821
role: repair
generation: 2
status: ready
type: contract_repair
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: production mutation順序、runtime authority與fail-closed一次性預檢契約須精確修正。
ownership:
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-REPAIRED-SOURCE-PROMOTION-STAGING-CYCLE-17-20260821.md
  - .work/CARD-PANTHEON-G8-CYCLE17-PREFLIGHT-CONTRACT-CORRECTION-20260821/**
forbidden_scope:
  - 修改source、tests、scripts、config、rules、manifest、plist、runtime、queue、state或logs
  - 執行public preflight、Gate A、push、promotion、restaging、activation或任何production動作
verification:
  - CodeGraph-first；失敗才限域source/test證據
  - Cycle 17卡鎖定bounded capacity與formal runtime identity為不同gate
  - exact TMPDIR、actor/manifest/interpreter authority與gate order明確
  - 單次、非PASS即停、無重試
  - 只改ownership、git diff --check、candidate commit
evidence_path: .work/CARD-PANTHEON-G8-CYCLE17-PREFLIGHT-CONTRACT-CORRECTION-20260821/
---

# Cycle 17 formal preflight contract correction

## 工作名稱 → 正在做什麼 → 現在狀態

修正 Cycle 17 formal preflight 契約 → 把已證實的parameter與gate-order recovery寫回原執行卡 → `READY / NO RUNTIME EXECUTION`

## Authority evidence

- NO-GO evidence commit：`ef2cdf9e47`。
- parameter RCA commit：`1f0c0f0511`。
- RCA verdict：`PARAMETER RECOVERY`。
- root cause：public installer invocation漏`TMPDIR=/private/tmp`，使`/tmp` temp plist resolve為`/private/tmp`並觸發canonical-path rejection。
- Publisher no-PID為預期preactivation transition input，不得先activation/reload。

## 修正契約

1. 在Cycle 17卡明確分離：Cycle 16 bounded capacity receipt驗證，與target formal runtime identity/capacity public preflight。
2. 移除或改寫含混的`current capacity preflight`，不得要求以target tooling venv驗current/target manifest。
3. formal public preflight只能從該時點authoritative actor root的installer執行，使用同一authoritative manifest、expected digest與manifest-bound Python。
4. argv必須含`TMPDIR=/private/tmp`；不得用`/tmp`、system Python、direct module或file-path module替代。
5. gate order需與source/tests一致：先驗Cycle16 receipt與deterministic plan；依既有authorization/Gate A/push/promotion流程materialize target tuple與preactivation stage；在capacity plist install/restage及activation前執行formal preflight。若實際promotion seam不能細分至此，必須`BLOCKED / CONTRACT-SEAM CONFLICT`，不可虛構順序。
6. 為修正後Cycle 17 execution建立全新的單次formal preflight authorization；舊invocation count不得重用。第一次非PASS立即停，不換入口、不重試。
7. 保留原卡的Gate A、push、promotion、no-canary與所有fail-closed限制；不得藉本修正增加production authority。
8. 僅修改原Cycle 17卡與本卡evidence；寫contract diff摘要、source/test evidence定位、invocation/mutation counts；`git diff --check`後candidate commit。

## 停損

- 無法由現有public installer及promotion seam表達安全順序：`BLOCKED / CONTRACT-SEAM CONFLICT`。
- 本卡runtime invocation=0、production mutation=0。
