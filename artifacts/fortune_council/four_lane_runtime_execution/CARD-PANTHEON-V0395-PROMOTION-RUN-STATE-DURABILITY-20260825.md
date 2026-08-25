---
id: CARD-PANTHEON-V0395-PROMOTION-RUN-STATE-DURABILITY-20260825
status: ready
chain_id: PANTHEON-PROMOTION-RUN-STATE-DURABILITY-20260825
role: implementation
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 根因已固定，但涉及 production promotion、active run identity 與 fail-closed 狀態契約，採 strict/core-bounded 跑道。
traces_to: [SC-001, SC-002, SC-003, SC-004]
---

# Pantheon promotion 後發文狀態持久化

工作名稱：Pantheon promotion 後發文狀態持久化

任務目的：修正 active content run 被放在會由 promotion 替換的 actor `.work`；run state 必須由 durable runtime 擁有，promotion 必須驗證 registry 與實體 run 的 referential integrity，dangling run 必須 fail closed 且禁止 auto-seed 新 identity。

## 已知根因

- coordinator 預設 `run_root=<actor>/.work/gsc-copy`。
- aggregate promotion 會以乾淨 stage 原子替換整個 actor root。
- `--preserve-run-id` 只保存 queue registry，未驗證或保存 registry 指向的 actor-local `run_dir`。
- promotion 後 registry 尚在、`run_dir` 已消失；normal sweep 隨後可建立無關的新 run。
- 這是 2026-08-15 promotion replacement boundary 與既有 actor-local state ownership 的跨功能回歸；不是模型、使用者刪檔或強制停止造成。

## 唯一責任切片

`SLICE-V0395-01`：RED → durable run ownership → promotion referential-integrity gate → dangling fail-closed → GREEN。不得再拆 implementation 卡。

## 可改範圍

- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `scripts/pantheon_content_runtime_promotion.py`
- `scripts/agy_gemini_coordinator.py`
- `tests/test_install_agy_gemini_coordinator_launchd.py`
- `tests/test_pantheon_content_runtime_promotion.py`
- `tests/test_agy_gemini_coordinator.py`
- 本卡 RESULT 與 `g8_v0395_promotion_run_state_durability_20260825/` 證據

## 必要契約

- production coordinator 的 new/rewrite run root 必須位於 durable runtime boundary，不得位於 actor root；優先沿用既有 queue-owned `gsc-copy` snapshot seam，禁止新增第二套 state root。
- preserved registry 的每個 `run_dir` 必須是 allowed durable root 的 canonical descendant，目錄與 `brief.json` 必須存在，run identity 一致；plan 保存內容 digest，apply/postcheck 驗證 promotion 前後未漂移。
- dangling、symlink、越界、identity mismatch 或 digest drift 均在 actor replacement 前 fail closed，zero mutation。
- coordinator 發現 active registry dangling 時不得先執行 new/legacy sweep，也不得建立 replacement identity；輸出明確 blocked receipt。
- 不復原已遺失的 V0391 run，不手造 production artifacts。修復 promotion 後由主線另做唯一一次新 canary 驗收。

## 成功準則

- `SC-001`：RED 證明目前 promotion 接受「registry 存在但 `run_dir` 不存在」；GREEN 後 plan 即拒絕且 zero mutation。
- `SC-002`：installer/launchd contract 證明 actor 被替換前後，new/rewrite run root 均固定在 durable runtime，且不回退到 `<actor>/.work/gsc-copy`。
- `SC-003`：integration fixture 證明 active run 建立後經 promotion 仍可用相同 run identity 接續；run tree digest 前後一致。另有 dangling registry 負向測試證明不 auto-seed。
- `SC-004`：所有受影響完整 test files、shell syntax、`git diff --check` 通過；交付單一 candidate commit 與完整 SHA。

## 禁止範圍

- 禁止操作 production runtime、launchctl、Publisher、模型、真實 queue/state、publish、tag、push 或公開網站。
- 禁止修改文章內容、model route、Gemini request、Publisher release transaction、registry schema或 failed-job replacement 邏輯。
- 禁止新增 retry framework、第二個 Repair、第二套 durable state root或一般化重構。
- 禁止碰觸主線既有未追蹤檔。

## 停損與交付

- 同一 blocker 第三次失敗即停止；不得以新增卡、放寬 identity 或手造 artifacts 繞過。
- 若必要修改超出 allowlist，先 `BLOCKED` 回主線，不自行擴 scope。
- 交付：RED/GREEN、changed files、完整測試、candidate SHA、剩餘風險；不得宣稱已 promotion 或已發文。

## RESULT

狀態：PASS（candidate，未執行 production promotion／publish）

- `SC-001`：promotion plan 對 dangling preserved `run_dir` 在 mutation 前 fail closed；zero-mutation regression 通過。
- `SC-002`：installer 將 new/rewrite run root 固定為 `<queue-root>/gsc-copy`，actor-local override 在 side effect 前拒絕。
- `SC-003`：active run 經 synthetic promotion 保持相同 identity 與 run tree digest；coordinator 在 sweep 前對 dangling registry 回傳 blocked receipt，不建立 replacement identity。
- `SC-004`：promotion `30 passed`、coordinator/installer `292 passed`、shell syntax 與 `git diff --check` 通過。
- Evidence：`artifacts/fortune_council/four_lane_runtime_execution/g8_v0395_promotion_run_state_durability_20260825/evidence.md`。
- 剩餘風險：尚未執行 production promotion 或新 canary；主線須依卡片另行做唯一一次正式驗收。
