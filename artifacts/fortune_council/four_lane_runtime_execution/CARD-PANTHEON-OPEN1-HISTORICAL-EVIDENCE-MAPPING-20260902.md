---
id: CARD-PANTHEON-OPEN1-HISTORICAL-EVIDENCE-MAPPING-20260902
chain_id: PANTHEON-FOUR-LANE-RESIDENT-OPERABILITY-20260902
role: research
cycle: 1
status: ready
risk: medium
---

# OPEN-1 真實歷史 failure-isolation evidence mapping

## 目標

只讀查核既有 repo evidence 與 `<production-runtime-root>` 的 registry、run state、ledger、terminal/manual receipts，判斷是否存在同一條真實可追溯鏈：

1. 同一 item 實際失敗三次，或達映射後確認的既有正式上限。
2. 同一 item 實際進入既有 terminal/manual 狀態。
3. 同一 item 實際釋放其占用槽位。
4. 下一個不同 item 由既有 selector 選出並開始執行。

## 證據門檻

- 四段必須以 exact item/run identity、時間／sequence 與 authoritative artifact 串成同一 chain。
- 先映射 transport、run/article、Publisher retry authority 與「三次」語意；不得新增 counter。
- code、tests、fixture 只能解釋 evidence，不可取代真實觀察。
- 2026-08-26 `registry failed: 2` 且同 cycle seed/dispatch 只算相近證據，不得補成第三次、terminal/manual 或 slot release。
- 不得寫 production，不得製造失敗，不得啟動服務或呼叫 provider。

## Allowlist

- 只新增本卡與：
  `artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-OPEN1-HISTORICAL-EVIDENCE-MAPPING-20260902.md`
- 可唯讀 repo、Git history、`<production-runtime-root>` 及 launchd plist 檔案；禁止 `launchctl` mutation、queue/state/ledger 寫入、service start、provider、publish、push、deploy。

## RESULT 必填

- 受查根目錄與 before/after fingerprint；不得把 secret bytes 寫入結果。
- retry authority mapping 與 total attempts/retries 語意。
- 每個候選 chain 的 exact identity、四段 evidence path／digest／sequence 與缺口。
- 結論只有：
  - `OPEN-1_PROVEN_BY_EXISTING_REAL_EVIDENCE`：四段同鏈全部成立；或
  - `OPEN-1_UNPROVEN`：任一段缺失。
- 若未證明，說明 bounded activation 後需要觀察的最小欄位，但不得擴張 preflight 四項。
- `git diff --check`、`git status --short`、production mutation/provider/launchctl：`0/NOT_RUN`。
