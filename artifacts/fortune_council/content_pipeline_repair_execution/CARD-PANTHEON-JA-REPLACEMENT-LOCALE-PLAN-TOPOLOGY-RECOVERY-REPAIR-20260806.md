---
card_id: CARD-PANTHEON-JA-REPLACEMENT-LOCALE-PLAN-TOPOLOGY-RECOVERY-REPAIR-20260806
chain_id: pantheon-ja-replacement-locale-plan-topology-recovery-20260806
role: implementation
cycle: 1
status: CARD_DRAFTED
thickness: strict
risk: production-control-plane
model: gpt-5.6-sol
reasoning: high
model_reason: repeated production LocalePlanValidationError spans model adherence, bounded replacement lineage, evidence preservation, and exact-run recovery semantics
source_sha: 29fa640465ccad197e0bc3a3b0bf66989d90a325
---

# 修復 JA replacement locale-plan topology recovery

## 目標

沿用既有 multilingual pipeline 與一次性 `-replacement-01` recovery，找出並修復 JA production replacement 在新版 topology prompt 下仍於第三代 `LocalePlanValidationError` 終止的根因。不得新增另一套 pipeline、不得降低 deterministic gate 或 Reviewer 標準。

## 已知 production 證據

- 原 run：`auto-i18n-ja-af38c7e7beacd0001ccd`，terminal `LocalePlanValidationError`。
- bounded replacement：`auto-i18n-ja-af38c7e7beacd0001ccd-replacement-01`。
- replacement namespace：`10cf1bfa1b6d13a19cdfd52c`。
- production actor：`29fa640465ccad197e0bc3a3b0bf66989d90a325`。
- replacement 已完成多個 Writer／Reviewer job，最後 job `a6d2ad9897ae8f283a4b8f3cc371c317a9910672` 後再次 `LocalePlanValidationError`。
- i18n processing 為 0；broad coordinator／publisher／new／rewrite 已恢復，i18n-new／i18n-rewrite 未載入。
- 沒有 translation release、commit、tag 或 push。

## Ownership / allowlist

- `scripts/agy_multilingual_pipeline.py`
- `scripts/agy_gemini_coordinator.py`（只有證據證明 recovery routing 必須調整時）
- `tests/test_agy_multilingual_pipeline.py`
- `tests/test_agy_gemini_coordinator.py`（只有 coordinator 有變更時）
- 本卡與同卡 evidence receipt

## Forbidden scope

- 不修改 production queue、run、inbox、outbox、archive、credential、LaunchAgent 或 actor。
- 不呼叫 Gemini、不發布、不 commit/tag/push production content。
- 不刪除或覆寫既有 attempt／replacement evidence。
- 不新增第二代 replacement，不放寬 topology、fact coverage、safety、deterministic gate 或 Reviewer。
- 不碰 registry、metadata、sitemap、feed、redirect、其他正在產文的內容。

## 任務

1. 以 production-shaped fixture 重現 replacement 在前兩代 Reviewer 修復後，第三代 external plan 仍重用 prior fact-to-H2 topology而 fail closed。
2. 分辨是 prompt 約束仍不足、hydration/rebuild authority 與 production payload 不一致，或 recovery lineage錯誤；只修有證據的最小 seam。
3. 保留一次性 bounded replacement 與舊 evidence；不可用刪 cache、重置 queue、隨機搬 fact 或自動 canonicalize 製造通過。
4. 新增 RED/GREEN regression，證明真實 failure shape 被攔截或被明確、可機器判讀的 repair contract導向正確 topology。
5. 交付 candidate commit；不得自行 push、部署或重跑 production。

## 驗證

- `tests/test_agy_multilingual_pipeline.py` 全檔。
- 若改 coordinator：`tests/test_agy_gemini_coordinator.py` 全檔。
- exact-run regression：既有 `-k exact_run_ids` 測試。
- Python compile check、`git diff --check`。
- changed files 必須完全落在 allowlist。

## Evidence / handoff

- Evidence：`artifacts/fortune_council/content_pipeline_repair_execution/evidence/ja_replacement_locale_plan_topology_recovery_repair_20260806/`
- 交付：完整 candidate SHA、root cause、changed files、RED/GREEN 與完整測試結果、剩餘 production 風險。
- 狀態最多到 `DELIVERED_CANDIDATE`；主線負責獨立 review、整合、actor 對齊與另一次 exact canary。

## Stop-loss

- 同一 blocker 連續三次停止。
- 若必須改 production data、降低品質 gate 或建立第二代 replacement，立即 `BLOCKED`，不得自行擴權。
