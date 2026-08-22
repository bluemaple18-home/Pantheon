---
id: CARD-PANTHEON-G8-PUBLISHER-RESET-BOOTSTRAP-RCA-REPAIR-CYCLE-34-20260822-RESULT
card_id: CARD-PANTHEON-G8-PUBLISHER-RESET-BOOTSTRAP-RCA-REPAIR-CYCLE-34-20260822
chain_id: PANTHEON-G8-PUBLISHER-RESET-BOOTSTRAP-REPAIR-20260822
role: repair
cycle: 34
status: repair_ready_for_review
verdict: REPAIR_READY_FOR_REVIEW
production_mutation: false
---

# G8 Publisher reset bootstrap RCA／Repair Cycle 34 RESULT

## 終局判定

`REPAIR_READY_FOR_REVIEW`

已完成離線 RCA、最小修復與 focused regression；未執行 production mutation、reset、Capacity、activation、readiness、canary、Publisher child、transaction、tag、push或 deploy。

## Root cause

- promotion 後，共用 runtime manifest 已由 old-live G23 更新為 target G34；reset 複製 old-live Publisher plist並加入 `--activation-only`，其中 `--expected-digest` 仍為 G23，但 `--manifest` 指向已更新為 G34 的同一檔案。
- activation-only `barrier-exec` 因 manifest expected digest mismatch立即 exit `78`。launchctl bootstrap已註冊服務，但緊接的單次 `launchctl print` 可命中 terminal lifecycle settling而 exit `1`。
- 原 implementation 在 bootstrap 後直到 print／PID／path檢查結束前都維持 `ACTIVATION_PHASE=publisher_reset_bootstrap`，因此 Cycle 33 receipt將 settle failure記成 bootstrap exit `1`。
- `launchctl print-disabled gui/501` 顯示 Publisher enabled，已排除 persistent disabled；離線 control在 manifest identity一致時 child exit `0`且 reset成功，排除 plist結構必然無效與強制 fake bootstrap failure。

## RED → GREEN

離線 local-only command：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 <host-tmp>/publisher_reset_manifest_promotion_red.py red
```

- RED：bootstrap child exit `78`；首次 post-bootstrap print命中 registered／settling；reset exit `1`；receipt為 `publisher_reset_bootstrap`／exit `1`／`ROLLBACK_COMPLETE`。
- GREEN：同一 command、相同 promoted-manifest lifecycle；child仍 exit `78`，首次 print仍為 settling，下一次 read-only print取得 loaded/no-PID／exact path；reset exit `0`且無 failure receipt。

## Minimal repair

- 真 `launchctl bootstrap` 成功後立即切換 phase為 `publisher_reset_settle`。
- 以最多 20 次、間隔 0.05 秒的 bounded read-only `launchctl print` stabilization等待服務 identity可讀；沒有第二次 bootstrap或其他新增 mutation。
- 任一次可讀 identity若含 PID或 path不是唯一且精確等於 live Publisher plist，立即 fail closed並 rollback；只有 print尚不可讀才進下一次 bounded probe。
- 永久 absent／timeout回 `publisher_reset_settle` exit `1`並 rollback；bootstrap真失敗仍保留 `publisher_reset_bootstrap`原始 exit code；postcheck失敗仍保留 `publisher_reset_postcheck`。
- 未改 current manifest／stage驗證、other-service identity／PID／path、Publisher pre-mutation drift拒絕、exact-run／max-runs selector、transition ordering、edge selector或 rollback語意。

## Regression matrix

| Case | 結果 |
|---|---|
| Publisher initially absent，old-live manifest在promotion後使child exit `78`，首拍print settling | PASS；bounded settle後成功，bootstrap僅一次 |
| Scheduled Publisher loaded/no-PID | PASS |
| Terminal one-shot Publisher absent | PASS |
| 永久 post-bootstrap absent | PASS；`publisher_reset_settle`／`ROLLBACK_COMPLETE` |
| Post-bootstrap PID drift | PASS；立即 rollback |
| Post-bootstrap path drift | PASS；立即 rollback |
| 真 bootstrap failure | PASS；保留 `publisher_reset_bootstrap`與原 exit code |
| Postcheck failure | PASS；`publisher_reset_postcheck`／rollback |
| Pre-mutation Publisher／other-service identity、argv、PID、path drift | PASS；仍 fail closed |
| exact-run／max-runs與其他六份 live plist保存 | PASS |

## Verification

- promotion-lifecycle RED／GREEN command：PASS。
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_agy_gemini_coordinator.py -k 'publisher_terminal_reset'`：`20 passed, 244 deselected`。
- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`：PASS。
- `git diff --check`：PASS。
- `rg '\[DBG-' scripts tests`：無殘留。
- tracked diff僅含本卡允許的 installer、coordinator tests與本 RESULT。

## Handoff

本 worktree未 commit、未 push。主線須在獨立 Review驗證 bounded settle、mutation count、負向 rollback與 allowlist後，才可決定整合；本卡未授權任何 production continuation。
