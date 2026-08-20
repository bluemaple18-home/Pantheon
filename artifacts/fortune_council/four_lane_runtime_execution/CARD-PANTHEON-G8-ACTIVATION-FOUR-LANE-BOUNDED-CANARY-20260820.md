---
id: CARD-PANTHEON-G8-ACTIVATION-FOUR-LANE-BOUNDED-CANARY-20260820
chain_id: PANTHEON-FOUR-LANE-PRODUCTION-RECOVERY-20260818
parent_card_id: CARD-PANTHEON-G8-MAIN-PUSH-RUNTIME-PROMOTION-STAGING-RETRY-2-20260820
role: implementation
cycle: 12
status: ready
type: production_activation_bounded_lane_canary
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
production_authority_sha: 88c6c0a95a013d0e9e8ab84c1a0f75a58ada1ff5
model_reason: production activation與四條lane有限寫入屬固定契約、高回退成本操作。
ownership:
  - .work/CARD-PANTHEON-G8-ACTIVATION-FOUR-LANE-BOUNDED-CANARY-20260820/**
  - 已 staged generation g14-88c6c0a95a-20260820T181900Z 的正式 activation
  - new、rewrite、i18n-new、i18n-rewrite各一筆 bounded run
forbidden_scope:
  - runtime repromotion、origin push、Publisher normal activation或transaction
  - publish、content commit、tag、public artifact、第二筆同lane run
  - 修改source、queue/state/plist/barrier/manifest、force/retry繞過gate
verification:
  - origin/main、actor、manifest、stage精確等於production authority
  - current capability READY、capacity PASS、preactivation transition PASS
  - aggregate activation-only先證明7/7 matching與zero child I/O
  - bounded lane入口各恰好一筆且shared correlation可追溯
  - Publisher transaction/tag/push/public content delta為零
  - rollback/stop-loss receipt、git diff --check、完整evidence
evidence_path: .work/CARD-PANTHEON-G8-ACTIVATION-FOUR-LANE-BOUNDED-CANARY-20260820/
---

# G8 activation與四線 bounded canary

## 工作名稱 → 正在做什麼 → 現在狀態

G8 production activation → 啟用已 staged七服務並讓四條lane各跑一筆bounded canary → `READY / USER AUTHORIZED`

## Root Question

能否只用既有正式入口，將 `88c6c0a95a013d0e9e8ab84c1a0f75a58ada1ff5` staged aggregate安全切為live，再讓四條lane各完成一筆run並停在Publisher邊界？

## 使用者授權與authority

- 使用者於2026-08-20明確授權 production activation＋四線 bounded canary。
- 不授權Publisher transaction、tag、push、公開發文、repromotion或source修補。
- 本卡文件commit僅為dispatch控制文件；production authority固定為`88c6c0a95a013d0e9e8ab84c1a0f75a58ada1ff5`。不得拿dispatch HEAD取代runtime source。
- 已完成：origin/main、actor、manifest、private stage收斂至authority；promotion COMMITTED；staged plist/readiness各7份；preactivation transition PASS；無activation/canary/publish/tag。

## 執行

1. 唯讀重驗origin/main、actor HEAD、manifest digest `db6cc697831947734c86b76e3e0054309d0854aacb7d55044cc559e02f1e24bb`、generation `g14-88c6c0a95a-20260820T181900Z`、staged/live seven、barrier、queue/transaction/tag/content基線。
2. current capability receipt、兩週期capacity與preactivation transition任一非READY/PASS即零mutation停止。
3. 只用正式aggregate activation-only入口切換staged seven；驗7/7同identity、matching barrier、loaded/no-PID、zero child I/O。失敗走正式rollback並停止。
4. 在任何lane I/O前鎖shared correlation與四個互異exact run IDs；使用正式bounded入口，順序執行new→rewrite→i18n-new→i18n-rewrite，每lane max-runs=1。
5. 每lane完成後立即核對ownership、run state、duplicate claim與其他lane delta；任一lane出現第二筆、identity drift、unknown outcome即停止後續lane，不重試。
6. Publisher保持activation-only／不可消費run；不得normal activate Publisher。最終四筆run停在可供後續精確select的合法狀態。
7. 核對transaction、tag、remote main、public content/sitemap均無本卡mutation；保存activation、四lane與stop-loss證據。

## 停損與交付

- 每個production write入口各一次；不盲retry。同blocker第三次停止。
- 四lane總新增run必須恰為4且每lane=1；否則`BLOCKED / PUBLISH NOT AUTHORIZED`。
- 最終只能是`FOUR LANE READY / PUBLISH NOT AUTHORIZED`或附唯一blocker的`BLOCKED / PUBLISH NOT AUTHORIZED`。
