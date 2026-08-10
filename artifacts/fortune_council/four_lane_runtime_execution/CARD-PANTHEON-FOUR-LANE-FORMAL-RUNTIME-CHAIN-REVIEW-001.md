---
card_id: CARD-PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN-REVIEW-001
status: RUNNING
execution_authorized: true
production_authorized: false
formal_thread_id: 019fea96-c155-75d0-9975-9c7074483e5e
dispatch_key: v1:1bd4c87ce46017d71e077dd96bd2b5ab278699ae9d41b346377d276d325cd58f
activation_status: BOUND
activation_token: act-v1:10edd76fff5f1810138eb7d75ea03a220a90e0740fd4d7a9d6b922b43f986413
cost_approval: 使用者於 2026-08-10 明確核准本卡 strict Review，並要求慎選模型與按條件使用子代理
chain_id: PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN
role: reviewer
cycle: 1
required_base_ref: codex/four-lane-formal-runtime-review-source-20260810
required_base_sha: c61491e748acad43e44e73f7eabbc320dcbaa532
candidate_sha: c61491e748acad43e44e73f7eabbc320dcbaa532
candidate_parent_sha: f31ef017170c69543528708fd1314dc87ff7528a
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 候選跨 Publisher、四軌 runtime identity、七服務 activation barrier、rollback 與 installer，且主線已發現 production-path evidence 衝突；需要 Sol high 做高風險獨立審查。
provider_boundary: Codex-only；禁止 Claude Code、Gemini 或其他外部 agent/provider 進入本 execution path
subagent_decision: ELIGIBLE_BOUNDED_OPTIONAL
subagent_reason: 候選共 87 個變更檔且跨 3 個以上 runtime 模組，符合安全委派門檻；但子代理只可做唯讀 advisory，正式 Reviewer 仍是唯一 verdict owner。
subagent_limit: 最多 2 個 gpt-5.6-terra / medium 唯讀 advisory 子代理
ownership: 固定 candidate 的獨立 correctness／runtime safety／evidence review 與唯一 verdict
traces_to:
  - FR-001
  - FR-002
  - FR-003
  - SC-001
  - SC-002
  - SC-003
  - SC-004
allowlist:
  - .ai/codex_task_four_lane_formal_runtime_chain_review_001.md
  - .work/CARD-PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN-REVIEW-001/review/**
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN-REVIEW-001.md
  - artifacts/fortune_council/four_lane_runtime_execution/review/formal_runtime_chain_review_001/**
forbidden_scope:
  - 修改任何 production source、tests、installer、plist 或 candidate commit
  - merge、push、deploy、production canary、launchctl、正式 queue／state／publisher mutation
  - 使用 hidden agent 冒充正式 Reviewer 或建立第二個 Reviewer thread
  - 子代理寫檔、commit、產生最終 verdict、對使用者發訊息或擴張 finding scope
  - full-auto、dangerously-bypass-approvals-and-sandbox、外部 provider
---

# 獨立審查 4lan 真實 Runtime 候選

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：獨立審查 4lan 真實 Runtime 候選
- 正在做什麼：只讀審查 `c61491e7…` 是否真正關閉舊 finding 003／005／008，並驗證證據與測試分類。
- 現在狀態：RUNNING；正式 Review thread 已綁定 exact SHA，candidate、merge 與 production 均未接受。

## 固定審查邊界

- Base：`f31ef017170c69543528708fd1314dc87ff7528a`
- Candidate：`c61491e748acad43e44e73f7eabbc320dcbaa532`
- Reviewer 不得改 source；只可新增本卡與 task-owned review evidence。
- 只有 P0／P1 可給 `REVIEW_NO_GO`；P2／P3 只列 residual risk，不移動 Repair 上限。
- 若 candidate SHA、parent、diff 或卡片 identity 不一致，立即 `BLOCKED / CROSS_THREAD_BINDING`。

## Root question

候選是否真的以正式 production implementations 證明：

1. coordinator → 四 lane → publisher → capacity guard 同一條 correlation chain；
2. 七服務每 tick 在第一次 I/O 前驗同一 runtime identity；
3. 只有 7/7 ready 才原子放行，rollback 核對七服務實際舊 control-plane identity？

## 主線預審假說（必須獨立重驗，不得照抄結論）

### H-001 Publisher capability 可能仍是模擬成功

核對 `scripts/agy_content_publisher.py` 的 `formal_capability_preflight()` 與 `scripts/pantheon_content_capability_adapter.py`：publish／transaction 是否真的呼叫正式 `publish_ready_runs()`、transaction worktree 與 release mutation boundary，或只是手寫 `status=PASS`、entrypoint 字串與 command plan。測試是否只驗非空字串而未驗實際 invocation。

### H-002 Full-suite unrelated 分類可能不成立

review evidence 宣稱 actor-recovery failures 涉及的 production 檔未修改，但 candidate diff 包含 `scripts/pantheon_content_actor_recovery.py`。必須以 baseline／candidate 可重現證據判定是環境 blocker、candidate regression 或未知；證據不足不得標 unrelated。

## Review 視角

1. Correctness：實際 call graph、資料／correlation handoff、fail-closed 時點。
2. Runtime safety：identity來源是否可信、barrier 是否真正阻止 child I/O、rollback 是否核對 loaded identity。
3. Regression：既有 non-formal runtime、installer、plist、CLI、queue/state 行為是否退化。
4. Test gap：測試是否命中 production public interface，而不是驗收自己寫出的 receipt 字串。
5. Evidence integrity：receipt、JUnit、fact gate 與實際 diff 是否一致。
6. Security／operations：環境變數、path、subprocess、git command plan、launchctl identity 是否可能被 caller 自證或注入。

正式 source decision 前，先執行 `review-orchestrator` 的 `plan`，task ID 固定為本卡 ID；只把它當 reviewer／finding schema 規劃器，不得讓它產生 verdict 或第二套 gate。

## 子代理契約

正式 Reviewer 可選擇不用子代理；若使用，最多兩個：

- Advisory A：Publisher／capability／transaction 正式路徑，`gpt-5.6-terra medium`，唯讀。
- Advisory B：runtime identity／barrier／rollback／test evidence，`gpt-5.6-terra medium`，唯讀。

子代理不得寫檔、commit、開 thread、呼叫外部 provider、產 verdict。正式 Sol Reviewer 必須親自讀關鍵 diff、重跑關鍵測試、重驗每個 finding，並對 advisory 結果去重與校正。若 advisory 結果衝突，正式 Reviewer以 source／test evidence 判定；無法判定則 `BLOCKED`，不得投票決定。

## 必跑驗證

1. `git diff --check` 與 exact changed-file inventory。
2. 針對 H-001 建立或執行不修改 source 的 invocation proof：證明正式函式真的被呼叫；不能只讀 receipt 欄位。
3. 重跑 4lan targeted suite；必要時用 monkeypatch／trace 唯讀觀察 call boundary，但不得修改 candidate。
4. 針對 H-002 對 base／candidate 做可比對重現；若環境缺 `.venv`，必須分離 hook blocker 與 candidate 行為，不得猜測。
5. 核對七服務 mismatch、6/7、7/7、early-start、rollback mismatch tests 是否在 mutation 前驗證實際 filesystem side effects。
6. 核對所有 evidence 內容與 candidate diff，不接受 summary 自證。

## Finding schema

每個 finding 必須包含：stable ID、P0/P1/P2/P3、category、`path:line`、觸發條件、source/test evidence、風險、最小修法、re-review 驗證方式、confidence。只有可重現 P0/P1 才阻擋。

## 交付契約

在 task-owned review evidence 內提交：

- `review.md`：findings first、Spec axis、Standards axis、testing gaps、residual risks。
- `finding-matrix.md`：H-001／H-002 與 FR／SC 狀態。
- 必要的唯讀 test／trace receipts。
- review-only commit SHA、clean status、精確 reviewed candidate。

唯一 verdict：

- `REVIEW_GO`：無未解 P0／P1；或
- `REVIEW_NO_GO`：至少一個可重現 P0／P1；列出固定 finding IDs，交回主線建立唯一 Repair-1。

不得宣稱 production ready，不得自行開 Repair。
