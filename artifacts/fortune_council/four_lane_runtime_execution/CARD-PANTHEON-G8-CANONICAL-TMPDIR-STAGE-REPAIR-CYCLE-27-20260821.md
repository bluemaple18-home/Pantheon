---
id: CARD-PANTHEON-G8-CANONICAL-TMPDIR-STAGE-REPAIR-CYCLE-27-20260821
status: ready
chain_id: PANTHEON-G8-PUBLISHER-CANARY
role: repair
cycle: 27
thickness: strict
risk: production-adjacent
model: gpt-5.5
reasoning: high
model_reason: blocker 已固定為 canonical TMPDIR；只修復 partial private stage，未升 Sol。
---

# 以 canonical TMPDIR 修復 G23 private stage

## 目標

修復 Cycle26 因 `/var/...` 與 `/private/var/...` alias 造成的 `plist canonical realpath or owner mismatch`。從 current runtime actor、固定 `TMPDIR=/private/tmp`，覆寫既有六服務 partial stage並補齊 Capacity plist；零 activation、零 canary。

## 固定 authority

- 主線/card source：`b23737e838`；runtime actor/source：`b1719c0d6243c7ec6372889405a846ccd1b666ed`。
- manifest：`d1ec853fd1b32e4a77e9ab45a19a9482bad5a5c692cfc5c8396cf365a23cccbf`；identity：`0152d79f9901b4000c43c70966907e5001846dc7792e865d9255ada62f91ebae`；generation：`g23-b1719c0d-20260821T022959Z`。
- exact run：`auto-i18n-en-614aa4dc3542ab2c5637`；target `ASTRO-BASE-01:en`；Publisher `max-runs=1`。
- live seven：coherent G23、activation-only、loaded/no-PID。
- partial stage：六份 plist；Capacity plist 缺失；Cycle26 所有 production I/O 為 0。

## 前置閘門

1. current capability/readiness/fail-closed/capacity、host free disk、actor/manifest/live/queue/state/exact run 全 PASS。
2. partial stage 必須精確符合 Cycle26 receipt；任一未知 drift 或多餘檔案即停。
3. 驗證 `/private/tmp` 已存在、owner/mode 可接受，且其 canonical realpath 精確為 `/private/tmp`。

## 唯一修復順序

1. 保存 partial stage 與 live/queue/state/exact-run 快照。
2. 從 `<runtime-root>/actor` 執行正式 coordinator＋四 lanes `--install` 一次，環境固定 `TMPDIR=/private/tmp`。
3. 從同一 actor 執行正式 Publisher exact-run `--install` 一次，固定相同 TMPDIR、exact run 與 `max-runs=1`。
4. 執行 Capacity public `--preflight` 一次；必須 `preactivation_transition=accepted/PASS`。
5. PASS 後執行 Capacity正式 `--install` 一次，同樣固定 canonical TMPDIR。
6. 重驗七服務 private stage coherent G23、Publisher normal mode／exact-run receipt、Capacity PASS；live/queue/state/exact run 不變。

## 可改範圍

- local-only private stage：僅上述既有 installers 可覆寫／補齊。
- `.work/CARD-PANTHEON-G8-CANONICAL-TMPDIR-STAGE-REPAIR-CYCLE-27-20260821/**`。
- 唯一 committed result：同目錄 `CARD-PANTHEON-G8-CANONICAL-TMPDIR-STAGE-REPAIR-CYCLE-27-20260821-RESULT.md`。

## 禁止

- 禁止修改 source、tests、config、workflow、manifest、live plist、queue、state、registry、sitemap、feed。
- 禁止 activation、launchctl mutation、barrier publish、canary、Publisher child、transaction、tag、push。
- 禁止第二個 TMPDIR、retry、第二次 install、換入口、手動拼 plist、另開 replacement thread。

## 驗收與停損

- 各正式 install/preflight `0|1`；retry=`0`；activation/canary/transaction/tag/push=`0`。
- 成功須證明 canonical temp path、七服務 staged plist coherent G23、Capacity PASS、live/queue/state/exact run 不變。
- 首次失敗立即停止；`git diff --check` PASS；candidate commit 只含 RESULT。

## 終局

- `REPAIRED / CAPACITY PASS / NO CANARY`
- `BLOCKED / NO ACTIVATION`
