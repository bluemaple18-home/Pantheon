# Coordinator–Publisher 三層失敗因果 RCA

## 判定

`RCA_READY`。Coordinator ownership/root cause 信心高；Node scan 為效能 amplifier，信心中；historical recovery exit 128 為 recovery defect，信心中低。

第四線的差異不是使用不同流程，而是 `rewrite_existing_body` 進入 Publisher 隔離 transaction 後，Coordinator 下一輪仍把 queue 內所有 `active` state 視為 Coordinator-owned，並依賴可變的 `<run_dir>/brief.json` 重新推導 lane。前三線未撞上「Publisher transaction 活躍、brief 不可讀」的交疊；第四線首先暴露 ownership 契約缺口。

## 因果鏈

```text
run 註冊：state 只存 run_dir，未存 lane/mode
→ rewrite Publisher transaction 延長 active window
→ Coordinator 讀取全部 active states
→ _migrate_pending_jobs → _lane_for_state → brief 不可讀
→ ValueError，Coordinator 退出
→ capacity guard 見無 PID，正確 fail-closed 停止服務
```

另一條獨立歷史鏈：`prerender 300s timeout → recovery → git diff --binary <base_sha> exit 128`。exit 128 發生於 timeout 之後，只會遮蔽原失敗，不會造成 timeout。

## 分類

- 重複 Node corpus/inventory scan：效能缺陷／amplifier；不是 Coordinator crash 必要條件，也未證明為 300 秒 timeout 的充分條件。本 checkout 單次 `load_publication_reference_corpus` 量測為 621 筆、10.65 秒。
- Coordinator routing：本次 root cause。state 沒有 immutable routing authority，缺 brief 時讓整個 cycle crash。
- `git diff --binary` exit 128：獨立 recovery defect；歷史 transaction receipt 不足，暫不猜 object provenance。
- capacity guard：正確 fail-closed 後果，非根因，不得放寬。

## 已實跑 RED

```text
PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3 -c 'from scripts import agy_gemini_coordinator as c; c._migrate_pending_jobs(__import__("pathlib").Path("/private/tmp/rca-empty-queue"), [{"run_id":"publisher-owned-active","run_dir":"/private/tmp/rca-missing-brief"}], set())'
```

實際 exit `1`：

```text
_migrate_pending_jobs (...:1611)
→ _lane_for_state (...:1446)
→ ValueError: active run brief is unavailable
```

此重現未呼叫 Node、Publisher、prerender、launchctl、網路或 production，因此證偽 Node scan 是 Coordinator crash 的必要原因。

## 第一修復契約

1. `register_run` 原子持久化經驗證的 immutable `mode` 與 canonical `lane`。
2. 版本化 active state 的 routing 只讀 state，不再依賴 run-dir brief；mode/lane 衝突或未知值 fail-closed。
3. legacy state 缺 routing fields 時不得 crash 整個 cycle、不得猜 lane、不得移動 outbox；保留 evidence 並回傳可識別的 quarantined/unroutable outcome。只有 brief 可讀時才可一次性遷移。
4. 覆蓋 missing brief、四 lane、unknown/conflict、outbox 不被搬移的測試。

禁止以預設 rewrite、略過所有 active state、刪 queue、增加 timeout、放寬 isolation 或放寬 capacity guard 作為修法。

## 診斷副作用

唯讀 thread 未改 code/tests/config，未啟動服務，未碰 production、queue 或 transaction，未 publish/tag/push。
