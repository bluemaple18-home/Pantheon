---
id: CARD-PANTHEON-RUNTIME-RETRY-DEPLOY-RESUME-20260816
status: ready
role: implementation
chain_id: pantheon-runtime-retry-deploy-resume-20260816
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: production runtime、外部 provider retry 與發布交易邊界固定且回退成本高
ownership: Pantheon runtime retry、正式部署與原 run 接續
evidence_path: artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/runtime_retry_deploy_resume_20260816/
---

# Pantheon runtime 自動重試部署與原 run 接續

## 目標

把 `d27e8d2db655c919ea45b2f32c2476c9a9873132` 的 429 有界自動重試正式部署到 runtime，修正目前 actor／manifest／LaunchAgent identity 漂移，並讓既有 run 可安全接續。

## 已知狀態

- 原 run：`apf-create-run-new-7d0e46d9ec617526f77f8213`
- correlation：`apf004-gate-b-single-new-newflow-a6c4b798a6-20260816T021334Z`
- writer 已成功；reviewer 曾遇 503 與 429。
- 新 retry job 已建立，transport attempt=1；不得重建 attempt=0 或重用已消耗 job identity。
- `account-1` 成功；`account-2` 是 503；`account-3` 的 429 cooldown 已過期，沒有證據顯示三個 credential 已耗盡。
- `main` 已含 429 retry 修正與 346 tests PASS。

## 可改範圍

- `scripts/agy_gemini_outbox.py`
- `scripts/agy_gemini_coordinator.py`
- runtime promotion／manifest／LaunchAgent identity 的既有 public workflow 與對應 tests
- 本卡 evidence path

## 禁止範圍

- 不得讀取、輸出或寫入 API key。
- 不得手動 copy／修改 production actor、manifest、barrier、plist 或 queue 來繞過正式 public workflow。
- 不得重複 publish、重用 job identity、放寬 publication fail-closed。
- 未取得主線傳入的明確外部 payload 授權前，不得呼叫 Gemini；未取得發布授權前不得 publish／transaction／tag／push。
- 不得修改文章內容或擴張至其他 run。

## 執行要求

1. 先驗證獨立 clean worktree、source SHA 與本卡可讀。
2. 先查 CodeGraph；無索引才限域 `rg`。
3. 根因判定必須區分：provider 503、per-slot 429 cooldown、runtime identity 漂移、外部授權閘。
4. 使用既有正式 promotion／activation path；若 active queue 阻擋部署，提出並實作最小、安全、可測的 drain/resume seam，不得 ad-hoc mutation。
5. 修正後跑受影響測試、`git diff --check`、debug marker 掃描。
6. 只交付一個 candidate commit；不 push、不自行合併。

## 驗收

- 429 會在同一 logical request、同一 run、全新 job identity 下最多重試 2 次。
- 503 維持有界 retry；API_QUOTA、AUTH、MODEL_UNAVAILABLE 維持終止。
- cooldown 期間不打同 slot；cooldown 過期後可重新 admission。
- runtime actor、manifest、barrier、七服務 identity 可由正式流程收斂至同一 target SHA/generation。
- 原 run 的 queued retry 保留，且零重複 publication。
- 交付 candidate SHA、changed files、tests、production mutation summary、剩餘所需外部授權精確文字。
