# APF-004-GATE2-LAUNCHCTL-PATH-INDENT-INTEGRATION-001

## 正式狀態

- 工作名稱：整合 Gate 2 launchctl path 縮排修復
- 現在狀態：INTEGRATION_READY / production 停線 / 零 production mutation
- chain_id：pantheon-writer-vnext-apf004-gate2-production-realignment
- card_id：APF-004-GATE2-LAUNCHCTL-PATH-INDENT-INTEGRATION-001
- base：2a073ad57e6799383236d743bcc0567f0a2d3d72
- candidate：1005385a88868a90ff310e6e2edefa00e2fb5f74
- review_thread：019ffb96-c9fc-7463-856f-aa37988846df
- review_verdict：REVIEW_GO
- mutation_executed：false

## 目標與邊界

- 在乾淨 promotion worktree 整合已獨立審查的修復 candidate。
- 只接受 candidate 的四個既定檔案與本整合卡／整合證據。
- 重跑 exact positive、13 個 zero-mutation negatives、rollback／normal authority isolation、affected coordinator、runtime manifest 與三支 installer syntax gate。
- 驗證 candidate base、檔案集合、文字 diff、禁用 debug／本機絕對路徑／binary／secret drift。
- 不修改 root dirty checkout。
- 不推送、不 merge、不執行 production install／activate／launchctl mutation、不發文。

## 允許檔案

- `.ai/codex_task_apf_004_gate2_launchctl_path_indent_repair_20260814.md`
- `.ai/evidence/apf_004_gate2_launchctl_path_indent_repair_001.md`
- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `tests/test_agy_gemini_coordinator.py`
- `.ai/codex_task_apf_004_gate2_launchctl_path_indent_integration_20260814.md`
- `.ai/evidence/apf_004_gate2_launchctl_path_indent_integration_001.md`

## 禁止範圍

- production runtime、plist、launchctl、manifest、publisher、provider、business child 或 remote I/O。
- 任何未列入允許檔案的 source／config／workflow 變更。
- push、merge、tag、發文。

## 驗收

- promotion branch 的 parent chain 可追溯至 exact base 與 candidate。
- candidate 原始 review 維持 `REVIEW_GO`，無 P0/P1。
- 所列本機 gates 全部 PASS。
- `git diff --check` 與 `git show --check` PASS。
- 交付 exact promotion SHA；未取得下一階段明確授權前停在本機。
