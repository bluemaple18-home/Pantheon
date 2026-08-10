---
id: CARD-PANTHEON-FOUR-LANE-PRODUCTION-RECOVERY-20260810
status: delivered_candidate
type: evidence_index
---

# 證據索引

## 根因與修復

- worktree preflight：起點為乾淨 `origin/main@d5027d0ea4a3b989b9be098978356f4da7716230`；CodeGraph indexed HEAD 一致，正式入口已由原始碼確認。
- runtime control plane：七個 label 皆未載入；已安裝 plist 的 Python、working directory 與 module root 指向已不存在的 local-only publisher actor。
- capacity crash：歷史 stderr 顯示 transaction 子目錄於掃描期間消失，`_measure_tree` 拋出 `FileNotFoundError`；新增 race 測試先 RED，再以只忽略 `ENOENT` 的最小修復轉 GREEN。
- installer readiness：coordinator 與 capacity installer 原先沒有唯讀模式，無法在 control-plane mutation 前完成正式 preflight；新增 `--preflight`，並允許以已驗證 absolute user-home override 避免本機 directory-service 不可用。

## 驗證結果

- affected pytest：`361 passed, 1 warning`；warning 為既有 invalid escape `\/`。
- capability probes：七步正負向測試 `17 passed`。
- capacity focused：`10 passed`，含實際 log 回收、兩個高增長週期停損與 disappearing-directory race。
- formal coordinator preflight：四條 lane plist 建立與 lint 通過，沒有 target／launchctl mutation。
- formal capacity preflight：兩次皆 `PASS`；`bytes=208914216`、`file_count=33437`，host free 分別為 `36435640320`、`36430557184` bytes。
- clean candidate actor preflight：local synthetic actor 在 code commit `0b3daa5b9a4e67cac2db9ba44adf01b5bd53f8d2` 的 `runtime_sha` 與 synthetic `origin/main` 一致，digest 為 `d070e9798f155058c9297296c52808e3b9ca41a12bc0b8cc693bb38df9bdcd05`，結果 `ready` 且 `mutation_permitted=false`；後續只加入 evidence，production 仍必須對整合後 exact SHA 重驗。
- readiness gate：`READY`，`canary_created=false`；receipt 為 `production-canary-capability-receipt.json`。
- storage gate：`PASS`；receipt 為 `capacity-safety-receipt.json`。
- shell/plist/diff：三個 installer `bash -n`、五個 plist `plutil -lint`、`git diff --check` 全綠；無 `[DBG-` 殘留。

## Production 邊界

- 未執行：actor 建立／fast-forward、installer `--install`、`launchctl` mutation、provider call、queue/backlog mutation、production canary、release commit、tag、push、merge。
- publisher installer 對 dirty worktree 正確 fail closed；synthetic clean candidate actor 已證明 exact source SHA／runtime SHA／digest 契約，production 仍須在 candidate 整合至 `origin/main` 並重建 clean actor 後重驗。
- 四軌 runtime 驗收仍須另行取得 production control-plane 與 canary/tag/push 核准；任一 lane 失敗即停止後續 mutation。
