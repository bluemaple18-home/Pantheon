---
id: OWNER-RESCOPE-DECISION-PANTHEON-FOUR-LANE-GO-LIVE-20260902
chain_id: PANTHEON-FOUR-LANE-RESIDENT-OPERABILITY-20260902
role: owner_decision
date: 2026-09-02
status: accepted
---

# Pantheon 四線 go-live Owner 重切裁決

## 決議

```text
TERMINATE_C_C_T_ACCEPTANCE_PROGRAM
ACCEPT_HISTORICAL_PRODUCTION_PUBLICATION_PATH_EVIDENCE
DO_NOT_CLAIM_ALWAYS_ON_OPERABILITY_YET
REMAINING_BEHAVIORAL_GAPS = OPEN-1 + OPEN-2
GO_LIVE_PREFLIGHT = REQUIRED_NON_PROGRAM_GATE
```

歷史 production publication path 已證明單次 run 的 Writer → Reviewer →
publish → public URL 路徑可成立，並覆蓋四條 service lane 的 publication
identity、canonical URL 與 ledger 唯一性。因此 **per-run correctness closed**。

這些證據來自有人監督的 bounded canary／單發 transaction，不證明無人值守下
可以連續運行、失敗後必然釋放槽位，或每日產量與 provider 成本必然受控。因此
**resident operability unproven**。不得用「production operability 已結案」取代這個
邊界。

本裁決的 canonical Git 起點是 `main`／`origin/main` 的 release commit
`0f61545f8c6b561742b27792b8fef11ae8b1ccc5`；annotated tag `v0.3.375`
dereference 後指向該 commit。歷史 per-run evidence 至少包含：

| Publication class | Canonical release evidence | 解讀邊界 |
|---|---|---|
| `new` | `v0.3.365`、`v0.3.366`、`v0.3.371` | 新文單次正式發布路徑成立 |
| `rewrite` | `v0.3.367`、`v0.3.368`、`v0.3.372` | 舊文原 identity 的重寫發布路徑成立 |
| `translation`／`i18n-new` | `v0.3.369`、`v0.3.374` | 新翻譯來源形態的正式發布路徑成立 |
| `translation`／`i18n-rewrite` | `v0.3.375` | replacement 翻譯來源形態的正式發布路徑成立 |

上表不要求四條 lane 在同一 cohort 重演，也不構成連續無人值守證據。

本裁決終止 C-C/T acceptance program，因為該模擬器持續驗證的是已由歷史
production evidence 結案的 per-run 欄位。這是方向重切，不是程式品質否決；
C-C/T artifacts 與 branch 必須保留供日後 Gate D/E 或 forensic 參考，但不再是
active go-live authority。

## 剩餘 acceptance 邊界

只保留兩個 behavioral gap：

- `OPEN-1`：證明真實 failure isolation。只有同一 item 實際達既有正式上限、
  實際進入 terminal/manual、實際釋放槽位，且下一個不同 item 由既有 selector
  選出並開始執行，才可結案。讀 code、fixture 推論、Controller 指定下一篇，
  或 2026-08-26「registry 有 `failed: 2`，同 cycle 仍 seed/dispatch」案例都不夠。
- `OPEN-2`：在既有 Publisher lock 與 ledger authority 內完成每日 publication
  success quota，並另設 daily admitted-attempt 或 provider-call hard cap。成本上限
  的數值尚未裁決；數值、持久化 authority 與 fail-closed 測試任一缺失，都阻止
  activation，不得默認為 Owner 已接受風險。

`OPEN-2` 的 success quota 以 Asia/Taipei 日期計算：`new = 1`、
`rewrite = 1`、`translation = 1`、`total = 3`；`i18n-new` 與
`i18n-rewrite` 共用 translation class。quota admission 與 publication mutation
必須在同一個既有 Publisher lock transaction 內原子判定，沿用既有 ledger／
release identity，不得新增 state store。同一 `run_id` 的 crash replay 只可計數
一次，也不得因 publication 已成功而 ledger 尚未完成的當機視窗多放一篇。

quota date 在 transaction admission 時固定為 Asia/Taipei 日期；同一 `run_id`
跨午夜仍歸入原 admission date。成功只扣一次；失敗釋放 success reservation，
但仍計入成本上限。

## 後續 evidence 裁決（2026-09-02）

- `OPEN-1`：由既有真實 production chain
  `auto-new-v1-20260817-060-01 → auto-new-v1-20260817-061-01` 結案；結論只涵蓋
  Coordinator transport-failure isolation，不涵蓋 Publisher retry 或全面 resident
  operability。證據見
  `artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-OPEN1-HISTORICAL-EVIDENCE-MAPPING-20260902.md`。
- `OPEN-2` cost cap：鎖定為 Asia/Taipei 每日最多 `102` 次 provider admission。
  依現行四 lane 各一 run 的最壞既有語意預算，logical operations 為
  `8 + 8 + 9 + 9 = 34`，每個 operation 最多三個 transport jobs，故為
  `34 × 3 = 102`。不採 `75`，因其需先新增「延後其中一條 i18n lane」的 scheduler
  政策，超出本輪 minimum sufficient scope。
- `102` 是 provider-call count hard cap，不是 token 或貨幣上限；本輪不新增價格服務、
  token estimator 或第二套 budget system。

## 固定 go-live preflight

這是必要的非 program gate；清單固定只有四項，不得增加第五項：

1. 七服務 install/load 乾淨。
2. cap 設定存在，且 Publisher 實際讀到。
3. 一次 dry cycle。
4. production fingerprint 無漂移。

完成 `OPEN-2` 或上述 preflight 都不等於 activation 授權。service start、真實
`launchctl`、provider call、production/public mutation、deploy 與 Gate D/E 仍需
Owner 另行明示授權。

## 歷史文字澄清

commit `cab55f2dac675d0d5a8bc0279300b701058edf40` 的 commit subject 使用
「activation unlock decision」，但其內容只記錄**未來 activation 的授權邊界**：
Gate D/E 必須另立 Owner-authorized activation-unlock card、產生新的 exact actor
並接受 fresh independent review。它不是當下的 activation unlock，也不是本次
重切後的 active authority。保留歷史，不改寫 commit。

## 控制文件

- 任務卡：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-OWNER-RESCOPE-20260902.md`
- 剩餘缺口：`artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-RESIDENT-OPERABILITY-OPEN-ITEMS-20260902.md`
- C-C/T 封存索引：`artifacts/fortune_council/four_lane_runtime_execution/CCT-FORENSIC-ARCHIVE-INDEX-20260902.md`
