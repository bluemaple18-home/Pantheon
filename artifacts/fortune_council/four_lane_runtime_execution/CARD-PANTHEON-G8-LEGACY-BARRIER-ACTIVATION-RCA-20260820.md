---
id: CARD-PANTHEON-G8-LEGACY-BARRIER-ACTIVATION-RCA-20260820
chain_id: PANTHEON-FOUR-LANE-PRODUCTION-RECOVERY-20260818
parent_card_id: CARD-PANTHEON-G8-ACTIVATION-FOUR-LANE-BOUNDED-CANARY-20260820
role: diagnostic
cycle: 2
status: ready
type: readonly_diagnostic
thickness: minimal
risk: medium
model: gpt-5.6-luna
reasoning: medium
model_reason: blocker已固定，只需唯讀追蹤activation script與既有transition contract。
ownership:
  - .work/CARD-PANTHEON-G8-LEGACY-BARRIER-ACTIVATION-RCA-20260820/**
forbidden_scope:
  - 修改source/tests/rules或production runtime
  - launchctl、activation、queue/run、transaction、tag、push、另開repair/reviewer
verification:
  - CodeGraph後限域source trace
  - blocked argv/phase與live/manifest/barrier tuple對帳
  - 唯一root cause、最小seam、RED test名稱/command
  - production mutation=0、git diff --check、evidence完整
evidence_path: .work/CARD-PANTHEON-G8-LEGACY-BARRIER-ACTIVATION-RCA-20260820/
---

# G8 legacy barrier activation RCA

## 工作名稱 → 正在做什麼 → 現在狀態

診斷 legacy barrier activation blocker → 唯讀追蹤previous_barrier_validation為何用新manifest驗舊barrier → `READY / NO MUTATION`

## Root Question

aggregate `--activate-only` 在old-live→new-stage transition已由capacity gate接受後，為何仍要求legacy prior-loaded barrier通過promoted current manifest digest驗證？

## 已知證據

- production authority、origin/main、actor均為`88c6c0a95a013d0e9e8ab84c1a0f75a58ada1ff5`。
- `TMPDIR=/private/tmp`後正式preactivation transition回`accepted/PASS`。
- 唯一一次official activation-only在`replace_live_plists`前停止：`previous_barrier_validation`／`legacy prior-loaded service 缺少 valid activation barrier`。
- old live identity為`g8-b746...`、old digest `f78faa...`；共用manifest已是g14 digest `db6cc697...`，驗證回`runtime manifest expected digest mismatch`。
- activation、lane run、Publisher transaction、tag、push、public mutation皆為0。

## 執行與交付

1. 讀主線blocked receipt與installer/manifest/barrier相關source、tests；CodeGraph無結果才限域rg。
2. 還原正式argv與phase ordering，標出capacity transition接受後到replace_live_plists前的所有gate。
3. 判定：參數誤用／artifact缺失／source contract衝突／live drift，僅能選一個主因。
4. 若existing正式參數即可解，交exact dry-run argv；不得執行。
5. 若需repair，交唯一source seam、RED fixture、必守fail-closed負例與最小檔案allowlist。
6. 最終只能`PARAMETER RECOVERY`、`SOURCE REPAIR REQUIRED`或`LIVE DRIFT`；附production mutation=0。
