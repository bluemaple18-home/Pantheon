# Pantheon 自動發文限定驗收派工換手

## Root Question

如何用最小範圍證明 Pantheon 能自行循環處理新文、舊文重寫、翻譯與失敗跳下一篇，而不再擴張成無限修復。

## Goal

下一個主線只建立三張正式可見驗收卡，讓獨立 thread 執行；主線不親自跑驗收，只負責依證據收卡、整合判定，以及三卡全過後才決定是否重新啟用自動排程。

## Blocker

目前沒有技術 blocker。真正未閉合的是三條尚未以完整 runtime 行為驗過的契約；在它們通過前，不得宣稱自動化可無人值守。

## Candidate Fork

- 正確路徑：三張 bounded 驗收卡，依序執行，禁止平行操作共享 production runtime。
- 禁止岔路：再次修改已通過的新文發文鏈、重做 promotion、追求 coordinator 漂亮 exit code、順手修 P2/P3 或建立額外 Repair。

## Constraints & Preferences

- 使用者要求：開卡派工、由其他正式可見 thread 執行，不由主線親自施工；節省模式；不要無限膨脹。
- 主線仍必須保留 Gate 5：核對卡片證據與最終 GO/NO-GO，這個接受責任不能外包。
- 三張卡必須序列執行；production queue、registry、publisher、網站與 launchd 是共享狀態。
- 自動排程目前保持停止；三卡驗完且使用者再次明確授權前，不得重新啟用。
- 不開第四張驗收卡。若卡片發現真正 P0/P1 code defect，只允許依既有 Reviewer/Repair 唯一性規則走一個 bounded Repair；不得因建議或美化開 Repair。
- 同一 blocker 第三次即停。每篇內容審核/修復最多三次，超過後 terminal/manual，釋放槽位並前進下一篇。
- Writer 固定 `gemini-3.5-flash-lite`；Reviewer 固定 `gemini-3.1-flash-lite`。
- 不碰既有未追蹤檔。
- 完成定義必須包含公開網址 HTTP 200 且正文可見；中間狀態、commit、push、promotion 或 exit 0 均不能單獨算完成。

## Completed Actions

- Source main 已含修復：`878db727f4`（legacy registry compatibility）與 `6477ab815e`（legacy active runtime migration）。
- 完整測試曾通過：`364 passed`。
- production runtime 已 promotion 至 actor `6477ab815e8aecca7d1e8e1588e6e5eba0fab001`，generation `g47-6477ab81-activation-only-20260826`。
- Writer/Reviewer route 已確認為兩個 Lite 正式 API model。
- 新文完整 canary 已成功：
  - run：`v0391-publish-canary-20260826-02`
  - article：`V2-TAROT-DEATH-MONEY`
  - publication commit：`0257bd5213eed0d0df10661a54f6215901a54997`
  - tag：`v0.3.371`
  - 公開網址：`https://www.mysticpantheon.com/articles/tarot/tarot-1884`
  - HTTP 200、browser 正文/FAQ 可見、sitemap 唯一一次、ledger 唯一一次。
- 正式 activation/reset/capacity/七服務 aggregate 路徑曾通過，capacity preflight 使用 canonical `TMPDIR=/private/tmp`。
- 啟用後曾觀察自動建立並派送 `auto-new-v1-20260826-001-01` 的 Writer 工作。
- 使用者要求暫停後，七個服務均已 bootout；本次換手再次唯讀確認全部為 `STOPPED`。

## Active State

- Repo：`<repo-root>`
- Branch：`main`
- HEAD：`6477ab815e8aecca7d1e8e1588e6e5eba0fab001`
- 主工作區已有使用者未追蹤檔；未碰、不得清除、不得帶入新 worktree。
- 七個停止中的 label：
  - `com.pantheon.agy-content-publisher`
  - `com.pantheon.agy-gemini-coordinator`
  - `com.pantheon.agy-gemini-new`
  - `com.pantheon.agy-gemini-rewrite`
  - `com.pantheon.agy-gemini-i18n-new`
  - `com.pantheon.agy-gemini-i18n-rewrite`
  - `com.pantheon.content-capacity-guard`
- plist、queue、ledger 保留，沒有刪除。
- `auto-new-v1-20260826-001-01` 已存在；後續必須 reconciliation/resume，禁止重複 seed 同一 identity。

## In Progress / Remaining Work

下一個主線第一拍只讀本檔與專案規則，然後依 visible-thread 正規流程建立下列三張實體卡與正式 thread。先完成前一張並收證，再開下一張。

### 卡 A：舊文重寫原網址驗收

- 目的：選一篇既有舊文，走 selector → rewrite Writer → Reviewer/最多三次 repair → publish update。
- 必驗：沿用同 article identity 與原 canonical URL；公開網址 HTTP 200；正文確實更新；沒有新增重複 URL、ledger transaction 或文章。
- 禁止：改新文鏈、另建文章 identity、為了內容偏好超過三次重寫。

### 卡 B：翻譯公開網址驗收

- 目的：由一篇已通過的中文來源走 translation Writer → Reviewer/最多三次 repair → publish locale URL。
- 必驗：locale/來源 identity 綁定、公開 locale URL HTTP 200 且譯文可見、canonical/hreflang 正確、同 locale 不重複發佈。
- 禁止：重寫中文來源、擴成全語系批次、同時測多篇。

### 卡 C：三次失敗停單篇並前進驗收

- 目的：用 bounded、可回復且不污染公開內容的失敗情境，證明同一 item 第三次失敗後進 terminal/manual、釋放槽位，下一個 eligible item 會被選取。
- 必驗：失敗 item 沒有 publish transaction/公開 URL；attempt 精確等於三；不再重試；下一 item identity 不同且進入執行；全域 loop 沒有因單篇失敗停死。
- 禁止：破壞正式 API credential、製造無上限失敗、把測試字樣發布到公開網站、為證明前進而直接手改 registry 狀態。

三卡全 GO 後，主線才補上/核對每日硬上限契約（建議新文 1、舊文重寫 1、翻譯 1、每日最多 3 個 publication），再向使用者回報可否重啟。這不是第四張流程驗收卡；若目前 config 尚無硬上限，必須先明確回報缺口，不得直接開啟常駐排程。

## Waiting Conditions

- 等新對話接手本檔。
- 建立正式可見 thread 前，須先建立並提交 `status: ready` 的實體卡，驗證 source SHA、clean 獨立 worktree、正式 thread ID 與 activation receipt。
- production mutation 與重啟排程仍需遵守既有授權邊界；本換手本身不授權重新啟用常駐自動化。

## Blocked & Errors

- 無當前 blocker。
- coordinator 自動 cycle 曾因歷史 registry `failed: 2` 回 exit 1，但同一 cycle 仍成功 seed/dispatch；這不是本輪三卡的自動 Repair 授權，不得只為漂亮 exit code 修改。
- 過去錯誤 invocation surface 曾把 Lite 送入不存在的 Antigravity CLI label；正式 production Gemini API route 已避開。驗收卡不得自行改回 CLI `--model` 推測路徑。

## Key Decisions & Resolved Questions

- 新文寫作→審核→publish→公開網址已通過，不再重驗。
- 尚未驗的是舊文、翻譯、三次失敗後前進；範圍固定為這三項。
- 派工 thread 可以執行驗收，但最終主線 acceptance 不能外包；主線只做證據核對，不親自重跑流程。
- 正常內容失敗只停該 item，不應停整個系統；只有 API 全掛、push/deploy/公開網址失敗、容量或 quota stop-loss 才全域停。
- 同一 identity 必須 resume，避免重複發文。

## Next Step

新對話第一句：

`讀 handoff_20260826_pantheon_automation_acceptance_dispatch.md；第一拍只讀確認。然後依序建立三張實體驗收卡並派到正式可見 thread：A 舊文原網址、B 翻譯公開網址、C 三次失敗後前進。主線只收證與判定，不親自跑；七服務保持停止，不開第四張卡，不重驗新文。`
