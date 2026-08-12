---
id: CARD-PANTHEON-FOUR-LANE-PRODUCTION-RECOVERY-20260810
status: in_progress
type: implementation
---

# 四軌內容發布恢復

## 目標

從 `origin/main@d5027d0ea4a3b989b9be098978356f4da7716230` 修復正式發布 actor、容量 guard 與四軌 launchd 契約，先完成本機 RED→GREEN 與 production gates 證據，再等待 control-plane、canary、tag、push 的個別核准。

## 邊界

- 可改：任務指定的 publisher、coordinator、runner、outbox、capacity guard、對應 installer／plist／tests，以及本 workspace。
- 不碰：`prototypes/pantheon-motion-demo/**`、來源主工作區 dirty/untracked 檔、credential、private prompt、既有 queue job/state/backlog。
- 未授權：production installer 執行、`launchctl` mutation、production canary、tag、push、merge。

## 已確認事實

- 獨立 worktree 起點與 `origin/main` 同為 `d5027d0ea4a3b989b9be098978356f4da7716230`，開始時乾淨。
- 七個 production label 目前皆未載入。
- 已安裝 plist 全部指向已不存在的 local-only actor root；Python、正式模組與 working directory 因而不存在。
- capacity guard 最後持久狀態為 2026-08-07 `PASS`，但後續 stderr 可重現 `_measure_tree` 在 transaction 目錄並行消失時拋出 `FileNotFoundError`。
- CodeGraph 已於同一 HEAD 建索引；正式入口候選為 coordinator／lane runner／publisher CLI，publisher transaction seam 為 `_stage_commit_tag_push`。

## 可證偽假說

1. 若 guard crash 是並行交易目錄消失造成，讓 `_measure_tree` 忽略掃描期間的 `ENOENT` 後，相同 synthetic race 會由 RED 轉 GREEN，其他 I/O 錯誤仍會上拋。
2. 若 actor 無法恢復是 installer 只能安裝「呼叫它的 repo root」造成，加入正式 actor provisioning／read-only preflight 契約後，缺 actor 時可在不碰 production control plane 的測試環境建立乾淨 actor，並鎖定 source SHA／runtime SHA／digest。
3. 若四軌仍可能被 new-only 關閉，正式 installer 必須在 production preflight 拒絕 `NEW_ONLY=1`，且四個 lane plist 要各自保有唯一 queue root 與 lane identity。

## 驗證計畫

1. 新增 race 回歸測試 → 該測試先 RED，最小修復後 GREEN。
2. 新增 actor provisioning 與 production-mode fail-closed installer 測試 → 先 RED，再以最小 installer 修復轉 GREEN。
3. 跑受影響 pytest、所有 installer `bash -n`、plist lint、`git diff --check`。
4. 建立 capacity receipt 與七步 capability receipt；gate 結果只接受 `PASS`／`READY`，且 `canary_created=false`。
5. 未取得 production 核准時不執行 installer／canary／tag／push，最終狀態不得高於 `DELIVERED_CANDIDATE`。
