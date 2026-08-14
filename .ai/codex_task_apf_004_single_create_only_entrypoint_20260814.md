---
id: APF-004-SINGLE-CREATE-ONLY-ENTRYPOINT
title: 新增單筆 create-only 正式入口
status: ready
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: implementation
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: production queue/state 的核心 adapter 契約已固定，需維持既有四 lane 相容與 fail-closed mutation 邊界
parent_candidate: 5d8f0f07e8cd68f9e67d259ceecbbf9429f12b52
traces_to:
  - FR-SINGLE-CREATE-001
  - SC-SINGLE-CREATE-001
  - SC-SINGLE-CREATE-002
---

# APF-004-SINGLE-CREATE-ONLY-ENTRYPOINT｜新增單筆 create-only 正式入口

## Root question

如何讓已授權的一筆 source payload 經正式 adapter 建立唯一 run，同時不放寬既有四 lane adapter、下游與 production mutation 邊界？

## 已知 blocker

正式 `create_campaign_run_adapter` 對單筆 authority-bound payload 回 `create-run adapter requires exactly four lanes`。已審核證據位於：

- `artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/create_run_only_20260814/`

## 需求追溯

- `FR-SINGLE-CREATE-001`：提供獨立 public entrypoint，接受恰好一筆 source work item 與 exact tuple，並復用既有 create-run primitives。
- `SC-SINGLE-CREATE-001`：plan-only deterministic、恰好 1 run／3 expected writes，filesystem before/after 完全一致。
- `SC-SINGLE-CREATE-002`：apply 恰好註冊 1 run、0 pending dependency、可 idempotent resume；全部非法輸入於任何寫入前 fail closed。
- blocking edges：無；目前 frontier 僅本卡。production canary 重跑被本卡與後續獨立 Review 阻擋。

## 任務五行卡

- 目標：新增公開、可測、fail-closed 的單筆 source create-only adapter；plan-only 必須產生恰好一個 run，apply 必須只建立該 run 與既有 transaction receipt。
- 可改：`scripts/agy_gemini_coordinator.py`、`tests/test_agy_gemini_coordinator.py`、`.work/APF-004-SINGLE-CREATE-ONLY-ENTRYPOINT/**`。
- 禁止：不得修改既有四 lane public contract；不得碰 publisher／runner／select／publish／transaction/tag/push 行為；不得 deploy、activate、schedule、LaunchAgent、production apply、外部模型或網路服務。
- 驗收：RED→GREEN；單筆 `new` exact tuple plan-only 為 1 run／零寫入；apply 為 1 registered run／0 pending dependency 且 idempotent；非法 lane、多筆、identity drift、caller run/status、root overlap、collision 均在寫入前拒絕。
- 證據：candidate SHA、RED/GREEN 命令、受影響 pytest、既有四 lane regression、`git diff --check`、allowlist diff 與 production-mutation=0 聲明。

## 固定介面與 invariants

1. 新入口使用新的人類可讀 public function 名稱；不得把 `allow_single=True`、mode switch 或其他 caller boolean 塞進既有 `create_campaign_run_adapter`。
2. 單筆入口只接受 source lane：`new` 或 `rewrite`；本卡不支援 `i18n-new`／`i18n-rewrite`。
3. `workset.items` 與 `exact_tuples` 都必須恰好一筆，且 lane／work_id／article_id／locale 完全一致。
4. `max_runs` 固定等於 1；caller-supplied `run_id`、status、verdict、ready 一律拒絕。
5. run identity、brief 產生、runtime/root validation、preflight collision、transaction path 與 atomic write 必須復用既有內部 primitive；不得複製第二套 writer。
6. `plan_only=True` 不得建立目錄或檔案；結果包含恰好一個 run、唯一 deterministic run ID、`production_mutation=false`，expected write set 只能是該 brief、state 與 transaction receipt。
7. `plan_only=False` 只允許 create-run apply：不得啟動 runner、外部模型、select、publish、publisher transaction、tag 或 push。
8. 既有 `create_campaign_run_adapter` 的四 lane positive／negative／resume 行為與錯誤契約保持不變。
9. 不把 APF-004 特定 article ID 硬編碼進 production code；測試使用已確認的 `ASTRO-SCENARIO-BIG-THREE` fixture。

## TDD 與驗證

先新增 public-interface 測試並保留 RED 證據，再做最小實作：

```bash
uv run --frozen pytest -q tests/test_agy_gemini_coordinator.py -k 'single_create_only'
uv run --frozen pytest -q tests/test_agy_gemini_coordinator.py -k 'create_run_adapter'
uv run --frozen pytest -q tests/test_agy_gemini_coordinator.py
git diff --check
```

若 repo 的既有 `.venv`／uv lock 不支援 `--frozen`，記錄實際失敗後改用專案既有受控測試入口；不得安裝或升級套件。

## 停損

- 若完成需要修改上述 allowlist 外的 code/config，回 `BLOCKED_SCOPE_CHANGE`。
- 若無法在不改既有四 lane public contract 的前提下復用內部 primitive，回 `BLOCKED_ARCHITECTURE_FORK`，附最小證據，不自行擴 scope。
- 同一 blocker 第 3 次失敗即停。

## 交付

建立單一 candidate commit，不 amend、不 push。回報：工作名稱 → 正在做什麼 → 現在狀態、candidate SHA、changed files、RED/GREEN、regression、diff-check、剩餘風險。不得宣稱 production 已執行。
