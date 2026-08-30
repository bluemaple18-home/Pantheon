---
id: PANTHEON-NEW-LANE-CURRENT-READINESS-RCA-20260829
status: complete
type: rca
mode: readonly
---

# New lane current readiness RCA

## Root question

為何 current runtime promotion／manifest 已到 `dfcb`／`g68`，但 live `com.pantheon.agy-gemini-new` plist 仍是 `6477`／`g47`，且正式 selector 唯一 active run 會復用 2026-08-26 succeeded Writer residue，導致沒有合法 current fresh candidate？兩者誰是主因、誰是 secondary factor，正式 contract 如何取得一個 current eligible new run？

## 邊界

- 唯讀檢查既有 source、tests、artifacts、git history、live service definition 與 queue state。
- 僅可新增本卡與 `pantheon_new_lane_current_readiness_rca_20260829/` evidence artifacts。
- 禁止修改 plist、source、tests、queue、state、runtime。
- 禁止 promotion、activation、provider、reviewer、publisher、commit、push、tag、deploy。
- 禁止刪除或隔離舊 inbox。

## 必答證據

1. 最後成功 new lane production／public 版本與 runtime identity。
2. 引入 plist drift 與 active residue 的 commit／operation mechanism。
3. Durable invariants：promotion vs installed service identity、queue attempt identity、freshness／current acceptance。
4. 一個 production/provider mutations = 0 的 RED-capable plan-only／preflight fixture，能同時抓 installed identity mismatch 與 stale provider residue。

## 必須裁決

- promotion 僅更新 actor／manifest／stage 而不 install live plist 是否為設計契約。
- 是否存在正式 activation／reload seam 可收斂 7 services。
- new candidate 應由 scheduler 從 backlog create，或可 resume active。
- 舊 succeeded Writer job 能否被正式 terminalize／quarantine，或必須建立 new run。
- 單一主因、secondary factor，以及最小 bounded repair／operation frontier。
- `why_not_less`、`why_not_more`、`do_not_absorb`；若屬正常 operation gap 而非 code bug，須明確標示。

## 驗收

- `RESULT.md` 明確為 `NO-GO | PARTIAL | BLOCKED | GO`，事實與推論分離。
- machine receipts 可重跑並記錄 checked identities、run IDs、freshness 與 mutation counters。
- 不建立 registry、FSM 或第二套 runtime。
