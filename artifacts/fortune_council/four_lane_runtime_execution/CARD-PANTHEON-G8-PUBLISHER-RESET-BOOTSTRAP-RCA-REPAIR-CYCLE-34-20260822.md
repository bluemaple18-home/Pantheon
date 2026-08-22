---
id: CARD-PANTHEON-G8-PUBLISHER-RESET-BOOTSTRAP-RCA-REPAIR-CYCLE-34-20260822
chain_id: PANTHEON-G8-PUBLISHER-RESET-BOOTSTRAP-REPAIR-20260822
role: repair
cycle: 34
priority: P0
status: ready
model_lane: gpt-5.6-terra
thinking: medium
source_authority: f2de899b1f
---

# G8 Publisher reset bootstrap RCA／Repair Cycle 34

## 工作名稱 → 正在做什麼 → 現在狀態

G8 Publisher reset bootstrap RCA／Repair → 對 Cycle 33 的 `publisher_reset_bootstrap` exit `1` 建立離線可重現訊號、定位根因，再做 bounded repair → `RCA_ONLY / AWAITING IMPLEMENT`

## Root question

為何在 target G34 stage、Publisher 未 loaded、其餘六服務 activation-only loaded/no-PID 的合法 `ST-TARGET-STAGED` 現場，`--reset-publisher-activation-only` 通過所有 precheck，卻在 `launchctl bootstrap gui/<uid> <publisher-live-plist>` 回 exit `1`；如何在不放寬 identity、PID、selector、ordering 或 rollback 契約下修正？

## 已知不可改寫事實

- Cycle 33 RESULT：`BLOCKED / NO CANARY`，合法終態 `ST-TARGET-STAGED`。
- current actor／manifest：`db9fb4343df212fd3b65546b017aba159620a058`／`g34-db9fb434-20260822T041850Z`／manifest digest `d067358d4d6228483484cdd984f25963ccbe131e8250e4a131ea10a6e6d6e08e`。
- formal reset唯一 invocation：correlation `G8-CYCLE33-PUBLISHER-RESET`、phase `publisher_reset_bootstrap`、exit `1`。
- rollback receipt：`ROLLBACK_COMPLETE`；七份 live plist byte-identical；六份 target stage與 selector不變；Publisher absent；其餘六服務 loaded/no-PID。
- 本卡不得把 production 再試一次當作 reproduction。

## 第一拍：RCA_ONLY

1. 驗正式 thread、獨立 clean worktree、HEAD／卡片可讀。
2. 先 CodeGraph task-semantic query；不足才限域讀取：
   - `scripts/install_agy_gemini_coordinator_launchd.sh`
   - `tests/test_agy_gemini_coordinator.py`
   - Cycle 33 RESULT
   - Cycle 33 failure receipt、edge2 pre/post snapshots、相關 launchd unified log（唯讀）
3. 建立一個不碰 production 的 red-capable command，必須命中同一個 `publisher_reset_bootstrap` 症狀；import／fixture／環境錯誤不算 RED。
4. 提出少量排序且可證偽假說，至少 falsify 一項；定位至 script／plist／launchd runtime／test-fixture 其中一層。
5. 輸出 `RCA_READY` 或 `BLOCKED`；`RCA_READY` 必須包含 root cause、RED command、最小 repair seam、預計修改檔與 regression matrix。
6. 未收到本 thread 由主線送出的精確 `IMPLEMENT` 前，不得修改 tracked files。

## IMPLEMENT 後允許範圍

- 可改：
  - `scripts/install_agy_gemini_coordinator_launchd.sh`
  - `tests/test_agy_gemini_coordinator.py`
  - 本卡唯一 RESULT：
    `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-PUBLISHER-RESET-BOOTSTRAP-RCA-REPAIR-CYCLE-34-20260822-RESULT.md`
- 只有 RED 證明必需且先回報主線，才能申請增加一個直接相關檔案；未獲允許不得擴張。
- 修復必須維持：
  - transition ordering與 `PANTHEON_RELEASE_NEXT_EDGE` fail-closed
  - current manifest／stage identity驗證
  - other-service loaded/no-PID與 launchctl path驗證
  - Publisher running／path drift拒絕
  - exact-run／max-runs selector保存
  - rollback `ROLLBACK_COMPLETE／FAILED` 語意
  - 每個 production mutation package最多一次；但本卡本身禁止 production mutation

## 絕對禁止

- production reset重試、Capacity、aggregate activation、readiness、Rule 24／25、canary。
- Publisher child、release transaction、tag、push、deploy、schedule、steady autonomy。
- 修改 live plist、private stage、runtime actor／manifest、queue、state、transaction、barrier、launchctl domain。
- 刪除／覆寫 Cycle 33 evidence。
- 修改其他 source／tests／config、共用 registry／metadata。
- 用 mock-only GREEN 取代能捕捉本次真實 bootstrap failure mechanism 的 regression。

## 驗收

- 一條已執行、可重跑、命中目標症狀的 RED command。
- root cause以證據成立，至少一個 competing hypothesis 已 falsified。
- minimal fix後同一命令 GREEN。
- focused reset tests涵蓋：Publisher absent、loaded/no-PID、bootstrap failure rollback、postcheck failure rollback、identity/path/PID drift、selector preservation。
- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh` PASS。
- 受影響 pytest PASS、`git diff --check` PASS、`rg '\[DBG-' scripts tests` 無殘留。
- tracked diff只含允許檔案；不 commit、不 push。
- 最終只可 `REPAIR_READY_FOR_REVIEW` 或 `BLOCKED`，主線負責獨立 Review、整合與任何後續 production 授權。

## Stop-loss

- 同一 blocker三次即停；不得把 production 重試作為除錯手段。
- 無法建立合格 RED 時停在 `BLOCKED`，列明已嘗試方法與缺少證據。
- 任何 scope／authority／runtime identity歧義立即停止。
