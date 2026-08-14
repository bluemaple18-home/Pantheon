---
id: APF-004-AGGREGATE-RUNTIME-PROMOTION-PLAN-PREFLIGHT
title: 鎖定 aggregate runtime promotion plan payload
status: ready
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: implementation
cycle: 1
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
model_reason: aggregate promotion 契約已固定；本卡只做 production payload 的 read-only plan preflight
parent_candidate: 0bf78f0b0cac6743fef4dae4aa76e21ebbaffe35
traces_to:
  - FR-AGG-PROMOTE-PLAN-001
  - SC-AGG-PROMOTE-PLAN-001
  - SC-AGG-PROMOTE-PLAN-002
---

# APF-004｜aggregate runtime promotion plan preflight

## 任務五行卡

- 目標：以已核准 public CLI 對目前 production actor／manifest／private stage 執行一次 `plan`，鎖定唯一 promotion payload 與 plan digest。
- 可寫：`artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/aggregate_runtime_promotion_plan_preflight_20260815/**`。
- 禁止：不得執行 `apply/rollback/finalize`；不得 mkdir/write transaction root；不得 deploy/install/copy、寫 actor/manifest/plist/stage、launchctl、create-run、外部模型、select/publish/transaction/tag/push/schedule；不得改 code/config/tests。
- 驗收：輸出 `PLAN_READY | BLOCKED`；證明 `plan` deterministic、production mutation=0、exact source/current/target identity、capacity receipt、write/backup/rollback/postcheck set 全部閉合。
- 交付：單一 evidence candidate commit；不 amend、不 push。回 SHA、verdict、plan digest、mutation summary 與下一個所需核准。

## 固定 authority

1. runtime source authority 固定為本卡 parent `0bf78f0b0cac6743fef4dae4aa76e21ebbaffe35`；`origin/main` 必須是其 clean descendant，且兩者 net diff 只能包含本張 `.ai/` 任務卡，不得有任何 runtime/code/config/test 差異。actor target 仍鎖 `0bf78f0b0cac6743fef4dae4aa76e21ebbaffe35`。
2. 只使用 `python -m scripts.pantheon_content_runtime_promotion plan`；不得用 internal function、ad-hoc `cp`、手改 JSON 或自造 receipt 代替 public CLI。
3. capacity receipt 必須來自既有 `pantheon_content_capacity_guard` raw receipt contract，驗實際 artifact SHA-256、`status=PASS` 與 stop-loss closed；不得只傳 digest-shaped sentinel。
4. current actor SHA、manifest digest、stage digest、target runtime digest、authorization digest、generation、identity、Python executable 與 correlation 都必須由實際 artifacts 重算；禁止沿用舊 snapshot 的值。
5. transaction root 只可作為 plan 中的未建立目標；plan 前後均須證明不存在或 byte-for-byte unchanged。

## 執行與證據

1. 先做唯讀 snapshot：source/actor HEAD-clean-origin、manifest、private stage、queue/state/run/gsc-copy、worker labels、transaction root、capacity receipt、host free/RSS/swap。
2. 保存 pre-plan digests/counts；執行一次 public `plan`，保存 stdout/stderr/exit code。
3. 以完全相同輸入再執行一次；兩次 plan digest 與 ordered stages/write set/backup set/rollback order/postchecks 必須一致。
4. 保存 post-plan digests/counts；production actor、manifest、stage、queue/state/run、worker labels 與 transaction root 必須零變化。
5. `PLAN_READY` 必須同時成立：source/current/target identity 唯一、capacity receipt PASS、plan deterministic、transaction root 零寫入、write/backup/rollback/postcheck 完整、所有禁止 mutation 為 0。
6. 任一 identity 漂移、receipt 不符、plan 建檔、輸出不 deterministic、或 exact payload 缺欄位，立即 `BLOCKED`；不得修 production state。
7. artifact 只記 `<repo-root>`／`<repo-parent>`／`<runtime-root>` 等可攜 placeholder；不得落盤本機絕對路徑、使用者名稱、`file://` 或秘密。

## 下一閘門

- 本卡不授權 production promotion。
- `PLAN_READY` 經獨立 Reviewer 核准並整合後，才可向使用者請求一次明確的 Gate A `apply` 授權。
- Gate B single plan-only 與任何發文仍不在本卡範圍。
