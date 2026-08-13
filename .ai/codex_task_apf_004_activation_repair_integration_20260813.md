# APF-004-ACTIVATION-REPAIR-INTEGRATION-001

## 工作名稱

整合已核准的 APF-004 activation failure receipt 修復。

## 鎖定輸入

- Base main：`79bdc809b0b7e17005c5420236dfb71e2bf794c2`。
- Candidate：`e5ce8491ce320ff30ae18717ca45a82ae86b434c`。
- Reviewer：`019ffb96-c9fc-7463-856f-aa37988846df`。
- Verdict：`REVIEW_APPROVED`。
- 原 P1 已 resolved；reviewer matrix `5 passed`、affected suite `31 selected / 151 deselected`。

## 目標

將 candidate 以可審計方式整合到獨立 integration branch，重驗後產 integration commit；不得觸發 live runtime。

## 步驟

1. 確認 integration HEAD/base、candidate ancestry、worktree clean。
2. 將 candidate changes 整合到目前 branch；不得 force、不得改 dirty 主工作區。
3. 檢查 allowlist：installer、coordinator tests、repair card、sanitized evidence；integration card可保留。
4. 重跑 reviewer matrix、affected suite、`bash -n`、`[DBG-`、`git diff --check`。
5. 檢查無 secret、絕對跨機路徑、非預期 binary／generated artifacts。
6. commit integration；回 `INTEGRATION_READY` 或 `INTEGRATION_BLOCKED`。

## 禁止範圍

- 不修改 root checkout。
- 不 live `--install`／`--activate`、launchctl mutation、runtime manifest write。
- 不 push origin/main、不 deploy。
- 不 external model、publish、transaction、tag、schedule。
- 不自行產 live reactivation payload。

## 驗收

- Candidate changes 完整且 reviewer-approved P1 修復存在。
- 指定測試與靜態 gates 全 PASS。
- integration worktree clean。
- 回 exact integration commit、測試結果、剩餘風險。
