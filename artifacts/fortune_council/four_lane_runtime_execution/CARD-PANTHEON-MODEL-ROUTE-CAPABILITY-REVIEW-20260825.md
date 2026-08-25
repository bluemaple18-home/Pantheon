---
id: CARD-PANTHEON-MODEL-ROUTE-CAPABILITY-REVIEW-20260825
status: ready
chain_id: PANTHEON-MODEL-ROUTE-CAPABILITY-20260825
role: review
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定候選涉及正式模型路由、activation fail-closed 與外部 CLI 錯誤分類，屬核心 bounded Review；規格已固定，不需 Sol。
---

# Pantheon 正式模型路由與 activation capability Review

工作名稱：Pantheon 正式模型路由與 activation capability Review

任務目的：獨立審查同一 source commit 內的 `PRE_CARD_CANDIDATE`，確認 Writer／Reviewer 固定為 3.5 Flash／3.1 Pro、activation 前完成雙模型 capability gate，且無證據的 `CLI_NONZERO` 不再自動重試。

允許範圍：唯讀審查 candidate diff；只可新增本卡專屬 Review result／evidence。禁止修改 candidate source、runtime、queue、stage、launchd、既有 run 與未追蹤檔。

驗收：檢查 config、CLI label、activation 前置位置、雙模型 models＋smoke、封閉診斷、`CLI_NONZERO` terminal policy、測試與 `git diff --check`；只以實際 diff／測試證據判定 `REVIEW_GO` 或含 P0/P1 finding ID 的 `REVIEW_NO_GO`。

## Candidate 範圍

- `config/agy_gemini_model_routes.v1.json`
- `scripts/agy_seo_copy_pipeline.py`
- `scripts/agy_gemini_outbox.py`
- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `tests/test_agy_seo_copy_pipeline.py`
- `tests/test_agy_gemini_outbox.py`

## 已知證據

- 原始失敗：正式 Writer route 使用不存在的 `gemini-3.5-flash-lite`，兩次只留下 `CLI_NONZERO`。
- 真實 CLI models 顯示 `Gemini 3.5 Flash (Low)` 與 `Gemini 3.1 Pro (Low)`。
- candidate 完整受影響測試：`331 passed`。
- installer preflight／stage→activation 隔離測試：`2 passed`。
- 新回歸與 terminal policy：`7 passed`。
- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`：PASS。
- `git diff --check`：PASS。
- candidate 新 live capability gate 曾 fail-closed：Writer smoke exit 1，只留下封閉 category／status（新版本）或 stderr digest；沒有 activation／queue write。Review 不得把外部服務當下可用性誤判成 source correctness。

## 禁止事項與停損

- 不得 activation、publish、push、tag、promotion、建立或重試文章 run。
- 不得自行修 code；發現 P0/P1 只寫 finding，交回主線決定是否建立唯一 Repair。
- 不得因 P2/P3 擴張 scope 或新增卡。
- 不得讀寫既有未追蹤檔。

## 交付

- Result：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-MODEL-ROUTE-CAPABILITY-REVIEW-20260825-RESULT.md`
- `REVIEW_GO`：列 reviewed commit、逐項證據、重跑命令與 residual risk。
- `REVIEW_NO_GO`：只列可重現 P0/P1 finding ID、證據、最小修正邊界；不得執行修正。
