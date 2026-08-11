---
id: CARD-CONTENT-WRITER-VNEXT-RA-SLICE-007-CAPACITY-PREFLIGHT
status: ready
chain_id: CONTENT-WRITER-VNEXT-RUNTIME-ACTIVATION
role: implementation
cycle: 1
thickness: standard
risk: high
model: gpt-5.6-terra
reasoning: medium
model_reason: 純唯讀主機容量盤點與 bounded cleanup eligibility 分類；規格固定但需 SRE 判讀，Terra medium 足夠。
traces_to:
  - RA-CHECKPOINT-B
  - STORAGE-CAPACITY-SAFETY-GATE-3
  - STORAGE-CAPACITY-SAFETY-GATE-5
depends_on:
  - RA-SLICE-006-INTEGRATED@643d535c1b21a577ea65cf2aa3845c35419b328f
---

# Writer vNext RA-SLICE-007：容量恢復 Preflight

## 目標

以固定取樣時間重新量測主機容量，盤點僅屬於 Pantheon Writer vNext／Codex 的可回收 worktree，產生不執行刪除的 cleanup plan，供主線決定是否回收並重跑容量閘門。

## Ownership

- Owner：RA-SLICE-007 implementation。
- 主線保留 cleanup 執行、整合、production canary 與最終判定權。
- 本卡只產生證據與候選計畫，不新增任何刪除權限。

## Allowlist

- `artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_007_capacity_preflight/**`

## 禁止範圍

- 不得刪除、移除、prune、archive、kill、stop、restart、deploy、push、tag、建立 canary、啟動 production 或正式產文。
- 不得修改 code、config、既有 RA001–RA006 artifacts、全域 ai-core 規則／gate／runtime。
- 不得掃描或建議清理其他專案、使用者文件、瀏覽器資料、認證、cookie、Downloads 或歸屬不明路徑。
- 不得以 `safe=true`、狀態文案或單次 `du` 自證可刪除。
- 共享 evidence 不得保存本機絕對路徑；以 worktree logical ID、branch、SHA 與 repo-relative／`local-only:<redacted>` 表示。

## 執行契約

1. 固定同一 `sampled_at`，量測主機 total/free、10% reserve、`max(20 GiB, 10%)` reserve、目前 deficit；同時記錄 VM、swap、memory pressure、Codex RSS。未知欄位即 `NO-GO`。
2. 從 `git worktree list --porcelain` 只盤點 Pantheon worktree。每個項目記錄：logical ID、branch、HEAD、dirty、bytes、是否有 unique commit、是否已有 retained archive ref、對應 task 是否已整合／封存。
3. 分類只能是：
   - `ELIGIBLE_FOR_MAINLINE_CLEANUP`
   - `RETAIN`
   - `BLOCKED_UNKNOWN`
   並附可重算理由。dirty、unique unprotected commit、缺 evidence／handoff、lineage 不明一律不得列 eligible。
4. 輸出保守可回收 bytes、跨過正式 reserve 所需最小 bytes；不得把預估值當實際回收。
5. 產生 deterministic cleanup plan，逐項列 expected SHA、branch、worktree logical ID、retained ref 與主線重驗命令。計畫不得自行執行。
6. 以第二次只讀取樣確認盤點期間未持續異常下降；兩次取樣間隔不得超過 300 秒。

## Evidence

固定寫入：

`artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_007_capacity_preflight/`

至少包含：

- `resource-snapshot.json`
- `worktree-inventory.json`
- `cleanup-plan.json`
- `capacity-verdict.md`
- `verification.txt`

## 驗收

- 兩次固定時間取樣齊全；所有數值有單位與來源。
- Pantheon worktree inventory 完整、無重複、分類 fail-closed。
- cleanup plan 僅含已整合、clean、有 retained ref、無未保存 unique work 的項目。
- 可回收總量與 reserve deficit 可由 inventory 重算。
- committed evidence 無本機絕對路徑、無其他專案內容。
- JSON 全部可 parse；allowlist audit、`git diff --check` 通過。
- 單一 candidate commit，worktree clean。

## Stop conditions

- 任一主機資源欄位未知。
- 需跨專案或刪除使用者資料才能補足 reserve。
- 任一候選 worktree dirty、SHA 漂移、unique commit 未被 retained ref 保護，或 lineage 無法證明。
- 同一 blocker 第 3 次失敗。

## 交付

只回：

- `RA_SLICE_007_CAPACITY_PREFLIGHT_READY_FOR_REVIEW` + candidate SHA + verdict；或
- `BLOCKED` + blocker evidence。

