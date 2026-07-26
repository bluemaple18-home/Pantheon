---
status: DELIVERED_CANDIDATE
chain: PANTHEON-PRODUCTION-GEMINI-KEY-SHARDING-20260726
type: repair-2-final
risk: strict/high
parent: 76fede6d87b85778fde4abf3aeeabe4c2bbd4e9f
---

# Pantheon Production Gemini Key Sharding Repair 2

## Root question

修正 production launchd installer 未在任何安裝或 live 動作前拒絕非 absolute credential pool path 的唯一 blocker。

## Required

1. `scripts/install_agy_gemini_coordinator_launchd.sh` 在 `PRODUCTION_POOL_FILE` 非空時，第一個 pool preflight 必須驗證 absolute path，再做 `-f`、symlink、owner、mode。
2. 非 absolute path fail closed；不得寫 plist、複製 LaunchAgent、bootstrap、kickstart 或觸及 live。
3. `tests/test_agy_gemini_coordinator.py` 新增 regression，證明 relative pool path 被拒且安裝副作用為零。

## Allowed files

- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `tests/test_agy_gemini_coordinator.py`
- `docs/pantheon_gemini_outbox_runner.md`（僅必要時）
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/production_gemini_key_sharding_20260726/verification.md`
- 本卡

## Forbidden

- 不得修改 runner、outbox、provider、V4、queue、ledger 或 live。
- 不得讀取或輸出真實 credential。
- 不得新增 retry、fallback、redirect 或 failure-driven rotation。
- 不得建立 PR、merge 或 deploy。

## Verification

- Relative installer pool fail-closed regression
- Installer/coordinator focused
- Production-pool focused
- 核心三檔
- Publisher + multilingual
- Full pytest
- `bash -n`
- Plist lint
- Python compile
- `git diff --check`
- Privacy scan
- V4 diff

## Delivery

交付單一 repair commit full SHA、exact diff、測試結果、剩餘風險與乾淨工作樹；不得宣稱 PR、merge 或 deploy。
