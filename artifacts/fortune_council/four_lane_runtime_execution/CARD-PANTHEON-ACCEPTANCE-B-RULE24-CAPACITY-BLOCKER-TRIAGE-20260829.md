# Pantheon Acceptance B：Rule24 容量阻擋唯讀分診

## 工作名稱

Pantheon Acceptance B Rule24 capacity blocker triage

## Root question

`dfcb` 正式發文續接在 promotion 前被 Rule24 判定 `NO-GO`，究竟是實際主機容量低於安全保留線、Rule24 證據欄位缺口，或兩者同時存在？

## 已知事故邊界

- 既有 receipt 回報 host free 約 `27,303,198,720` bytes。
- 本卡只做唯讀量測與證據分類。
- 掃描範圍只限 Pantheon main repo、Pantheon actor／queue／state、Pantheon worktree／runtime／evidence／cache。

## 必交付

1. 主機 filesystem total、free、10% 與 `max(20 GiB, 10%)` required reserve，並計算 shortfall。
2. Pantheon 範圍各 root 總量與主要占用候選。
3. 將候選分類為：
   - authoritative / non-rebuildable
   - rebuildable / cache / temp
   - unknown
4. 核對既有 Rule24 receipt 的實際 `NO-GO` 原因：主機保留線、容量預算欄位缺失或其他條件。
5. 只列出可在 Owner 明確授權後處理的最小安全 reclaim allowlist 候選與預估 bytes，不執行。
6. 最終唯一裁決：`REAL_HOST_CAPACITY_BLOCKER`、`RULE24_EVIDENCE_GAP` 或 `BOTH`。

## 禁止範圍

- 不刪除、移動、壓縮任何檔案。
- 不寫 production，不修改 registry／queue／state／actor。
- 不 stop／start launch agent。
- 不執行 promotion、publisher、push、tag。
- 不掃描或建議清理其他專案、整個 home、瀏覽器資料或 ownership 不明資料。

## 驗收

- 交付 `pantheon_acceptance_b_rule24_capacity_blocker_triage_20260829/RESULT.md`。
- 交付 machine-readable receipt，保留量測時間、命令邊界、bytes、分類、shortfall 與裁決。
- 所有清理候選必須標示 ownership certainty 與是否需要 Owner 授權。

