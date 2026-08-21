---
id: CARD-PANTHEON-G8-PUBLISHER-RESET-CANONICAL-TMPDIR-REVIEW-20260821
status: ready
type: review
role: reviewer
chain_id: PANTHEON-G8-PUBLISHER-RESET-STAGE-VALIDATION-20260821
cycle: 1
thickness: standard
risk: production-safety-bounded
model: gpt-5.6-terra
reasoning: medium
model_reason: 使用者指定節省模式；diff 僅 installer 15 行與兩個 focused tests，root cause、base/candidate 與驗收均固定，Terra medium 足夠做獨立 correctness/regression review。
---

# G8 Publisher reset canonical TMPDIR Reviewer 卡

## 審查基準

- base：`fdca2f7a2c45694b649940ca345c31ed336d0752`
- candidate：`51da4581afeb028903735cd98f918cc3482e6f52`
- 審查模式：唯讀 correctness／regression／production safety／test gap review。
- RESULT：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-PUBLISHER-RESET-CANONICAL-TMPDIR-REVIEW-20260821-RESULT.md`

## Root Question

Candidate 將 Publisher reset temp directory canonicalize 後再建立 temp plist，是否確實修復 macOS `/var` 到 `/private/var` alias 所造成的 canonical realpath mismatch，同時保留所有 production fail-closed 邊界與 pre-mutation safety？

## 必審契約

1. 驗證 canonicalize 後的 temp path 確實解決 `/var` → `/private/var` alias mismatch。
2. 驗證 `scripts/pantheon_content_runtime_manifest.py` 的 canonical／owner／mode gate 未被修改或放寬。
3. 驗證 temp activation-only receipt 的 `NO-GO` 會完整出現在 stderr，不再被 redirect 吞掉。
4. 驗證 temp directory、mktemp、copy／chmod、transform 或 receipt 的任何 failure 都發生在 live plist／launchctl mutation 前。
5. 驗證 Publisher live plist、其他六服務 plist、launchctl 與 child I/O 的既有零變更契約未退化。
6. 檢查 focused tests 是否真實覆蓋 symlink alias 與 receipt failure，而非只斷言成功或模擬不相關錯誤。

## 允許範圍

- 唯讀審查 base 與 candidate diff。
- 執行本卡指定的 bounded 驗證。
- 新增唯一 REVIEW RESULT：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-PUBLISHER-RESET-CANONICAL-TMPDIR-REVIEW-20260821-RESULT.md`。

## 禁止範圍

- 禁止修改 source 或 tests。
- 禁止進行 repair、建立新 Repair／Reviewer thread 或 replacement cycle。
- 禁止碰 production、正式 reset、LaunchAgents、launchctl、queue、runtime actor 或 remote。
- 禁止 push、tag、deploy 或其他 production mutation。
- 禁止跑 release 全套或廣掃 repository。

## 必跑驗證

```text
git diff fdca2f7a2c45694b649940ca345c31ed336d0752..51da4581afeb028903735cd98f918cc3482e6f52 -- scripts/install_agy_gemini_coordinator_launchd.sh tests/test_agy_gemini_coordinator.py
<main-workspace>/.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -k 'canonicalizes_ambient_tmpdir_alias or reports_temp_receipt_failure_before_mutation' -q
<main-workspace>/.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -k publisher_terminal_reset -q
bash -n scripts/install_agy_gemini_coordinator_launchd.sh
git diff --check fdca2f7a2c45694b649940ca345c31ed336d0752..51da4581afeb028903735cd98f918cc3482e6f52
```

節省模式：focused evidence 足以支持 verdict 時立即停止；不跑 release 全套、不廣掃 repository。

## Verdict 契約

Verdict 僅能為：

- `REVIEW_GO`
- `REVIEW_NO_GO`

只有 P0／P1 finding 能阻擋。每項 finding 必須包含：

- severity
- path
- line
- evidence
- risk
- fix
- validation_gap
- confidence

若無 P0／P1 finding，必須明確回報 `REVIEW_GO`，並另列未驗範圍與殘餘風險，不得以 P2／建議事項阻擋。

## 交付

只新增唯一 REVIEW RESULT，不修改 source/tests。RESULT 必須列出：

- base／candidate full SHA
- verdict
- findings 或明確無 P0／P1 finding
- 完整驗證命令與結果
- correctness／regression／production safety／test gap 判定
- 未做／未驗／殘餘風險
