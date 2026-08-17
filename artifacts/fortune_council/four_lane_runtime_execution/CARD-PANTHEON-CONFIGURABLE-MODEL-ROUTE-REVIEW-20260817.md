---
id: CARD-PANTHEON-CONFIGURABLE-MODEL-ROUTE-REVIEW-20260817
chain_id: PANTHEON-NEW-FLOW-PRODUCTION-PUBLISH-RECOVERY-20260817
role: reviewer
cycle: 1
status: ready
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: production 四線模型降級、quota identity、config digest 與 installer fail-closed 最終閘。
ownership:
  - artifacts/fortune_council/four_lane_runtime_execution/configurable_model_route_review_20260817/**
forbidden_scope:
  - 修改 candidate、source、tests、route config
  - runtime queue preservation、production queue、launchd mutation、network、push、merge、tag
  - 建立第二個 Reviewer 或 Repair task
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/configurable_model_route_review_20260817/
---

# Review Configurable Model Route

工作名稱 → 審查四線可設定模型路由
正在做什麼 → 唯讀審查固定 candidate 的 ordered route、quota/cooldown、digest 與 installer 契約
現在狀態 → ready；未收到正式 thread identity 前不得開始

## Fixed candidate

- base：`b81ed94a80d8d9808356ac959aaaba387d57c19e`
- candidate：`95485ab4921991e809a5414a579de8cc8bc97e2e`
- diff：`b81ed94a80d8d9808356ac959aaaba387d57c19e..95485ab4921991e809a5414a579de8cc8bc97e2e`
- claimed config digest：`781f243c541e4829ba1e5beebc41fec78bac196d258340faf4aae384dd5d9463`

## Review axes

1. Python 行為不得 hardcode 本輪 exact model IDs 或固定單一 fallback；route order 只能來自單一 versioned config。
2. config schema／canonical digest deterministic；unsafe ID、空 route、duplicate、primary role collision、unknown field／version fail closed。
3. quota identity 維持 `(credential slot, exact model)`；同 model 三 slots 全 `API_QUOTA` 才前進；中間 model blocked 可跳過；Flash 與 Flash-Lite 不互相封鎖。
4. transient 429／503／`API_RATE_LIMITED` 只 bounded retry/cooldown，不得前進 model。
5. daily quota reset 後回 role 首順位；不得靠 process restart 假裝 reset。
6. Writer／Reviewer 同時不得相同 exact model；四 lanes 共用同一 route config path/digest，不得各自 silent override。
7. installer 不得依 source checkout 絕對路徑或 mutable config 產生 staged/live identity 漂移；config path/digest mismatch fail closed。
8. scope 必須不碰 A. queue preservation、runtime queue 或 production。
9. tests 必須針對 public behavior；特別檢查假 daily reset、環境變數 bypass、TOCTOU、route exhaustion、全部 models blocked、role collision on fallback。

## Verification

- 完整讀 fixed diff 與 implementation evidence。
- 重跑 claimed 323-test 與 23-test suites、shell syntax、`git diff --check`。
- 必要 synthetic repro 只放 `/private/tmp`。
- finding 含 severity、path:line、trigger、risk、fix、validation gap、confidence。
- 未解 P0/P1 → `FINAL_REVIEW_NO_GO`；無 P0/P1 → `FINAL_REVIEW_GO`，P2/P3 列 backlog。
- 只在唯一 evidence path 寫 review receipt 並 commit；不得修改 candidate。
