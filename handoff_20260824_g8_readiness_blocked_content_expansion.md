# Pantheon G8 readiness blocked → Content Expansion 換手

## Goal

先完成 G8 `v0.3.370` production adoption／Publisher reset／單次發文 canary，隨即凍結 G8 feature work，將開發 frontier 移到 10K Content Expansion。

## Root Question

如何在不重造既有能力、不盲目撞測的前提下，解除目前 production readiness blocker，完成一次 bounded publication canary，然後開始 10K 內容施工？

## Constraints & Preferences

- 文件、自然語言、註解與 docstring 使用繁中；程式碼保留原語言。
- 下一手第一拍只能唯讀：先讀本 handoff、`AGENTS.md`、任務卡與 candidate evidence，再決定整合或 Repair。
- production mutation、canary、reset、activation、deploy、push、tag 均未授權；需要時必須停下取得使用者明確授權。
- 保留所有既有 G8 gate、transaction、去重、Publisher、回退與停損；「G8 freeze」只代表停止擴建控制面，不代表取消發文控制。
- 開發優先順序：先查 Pantheon 既有 authority／implementation／test，再查 `docs/content_prior_art_registry.md` 指定 donor 與精確 path。已有等價能力就 `KEEP`；可合法沿用就沿用，不憑空重造。
- 禁止重做 GSC ingestion、第二套 Topic/SEO Matrix、第二套 duplicate truth、第二套 Content Registry、第二套 Publisher/workflow。
- donor 只吸收 license-compatible implementation/test pattern；不得取代 Pantheon authority。禁止先掃整個外部 repo。
- 測試採 bounded evidence：先由現有失敗證據定位，再跑最小受影響 gate；同一 blocker 第 3 次失敗即停，不反覆盲撞。
- 使用者要求節約 token；只回報結果、blocker、需要授權的分岔。
- 主工作區原有未追蹤檔全部屬使用者，禁止 add、修改或刪除。

## Completed Actions

- 已把 `docs/content_prior_art_registry.md` 與 `docs/content_expansion_backlog.md` 整合至本機 `main`；目前主線 HEAD：`eb2ddd8157901e8764ffcc5fd8a5c68822fa357c`。
- 已確認 GSC ingestion 與 Topic/duplicate authority 已存在；backlog 明令禁止重做。
- 已建立並執行正式可見任務「核對 G8 production adoption readiness」：thread `01a03189-ae00-7003-ad0a-66b6de92a095`。
- 正式任務在獨立乾淨 detached worktree 執行，production 只讀；before/after tripwire PASS，protected surfaces changed `[]`。
- 任務已交付 candidate commit：`6de8e4874d77aacce90ffee3e265ed527686a0f0`；parent 是目前主線 HEAD `eb2ddd8157901e8764ffcc5fd8a5c68822fa357c`。
- Candidate 只新增 readiness RESULT 與 evidence；未 push、未 tag、未做 adoption/reset/canary。

## Active State

- 主工作區：`main`，HEAD `eb2ddd8157901e8764ffcc5fd8a5c68822fa357c`。
- 本機 `origin/main` ref：`5a9103785ebfc8d5a28fa8188def6069beb12d88`；本輪未 push。
- Candidate 尚未整合 main：`6de8e4874d77aacce90ffee3e265ed527686a0f0`。
- Candidate verdict：`BLOCKED`。
- Production actor：`db9fb4343df212fd3b65546b017aba159620a058`，仍非 release `v0.3.370`。
- Release tag `v0.3.370^{}`：`b0950d4c436cc902e17ac110b579b35b84aa53e4`。
- Publisher reset success receipt 不存在；現有 failure receipt 是 Cycle 33 `ROLLBACK_COMPLETE`。
- 10K Content Expansion 尚未開始。

## Candidate Evidence

- RESULT：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0370-PRODUCTION-ADOPTION-RESET-READINESS-20260822-RESULT.md`
- Evidence root：`artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_production_adoption_reset_readiness_20260822/`
- Execution contract：上述 evidence root 的 `execution-contract.json`
- Authorization request：上述 evidence root 的 `authorization-request.md`
- Candidate commit：`6de8e4874d77aacce90ffee3e265ed527686a0f0`

## Blocked & Errors

1. Git authority 尚未收斂：task HEAD 是 `eb2ddd...`，本機 `origin/main` ref 是 `5a910...`；需先唯讀釐清 ancestry／patch equivalence／正確整合策略。
2. 正式 read-only reconciler 回 `BLOCKED / ALLOWLIST_REQUIRED`；不得繞過，需用現有正式入口補齊精確 allowlist 或修正 authority input。
3. Current production 缺 Publisher reset success provenance，只存在 rollback failure receipt。
4. Candidate worktree 的 CodeGraph 未初始化；candidate 使用限域 source fallback。下一手 review 應先嘗試 CodeGraph，失敗才用限域 `rg`。

## Candidate Fork

- `FORK-A / current`：先 review `6de8e4874d`，確認 blocker 與 execution contract 可接受，再決定整合。
- `FORK-B / pending`：若 candidate 需修正，回同一正式 thread 做 Repair；不得另建第二個同角色 task。
- `FORK-C / gated`：只有 Git authority、allowlist、reset provenance readiness 全部收斂，才向使用者請求一次 bounded production adoption/reset 授權。
- `FORK-D / gated`：adoption/reset 成功且 fresh read-only reconciliation GO 後，才請求一次 bounded end-to-end publishing canary 授權。

## In Progress / Remaining Work

1. 唯讀驗收 candidate `6de8e4874d`：核對 allowlist、formal reconciler、tripwire、JSON、output ownership 與結論是否被證據支持。
2. 決定 candidate：整合 main，或回原 thread Repair。
3. 開一張 bounded blocker-resolution 卡：只處理 Git authority、reconciler allowlist 與 readiness provenance；禁止順手擴建 G8。
4. Blocker 收斂後重新產出 `READY-FOR-AUTHORIZATION`，停下等待使用者授權。
5. 授權後依既有正式 entrypoint 執行一次 bounded adoption/reset；fresh reconciliation 必須 GO。
6. 執行 `CONTENT-P0-02` 單次端到端 production publication canary。
7. Canary 成功後完成 `CONTENT-P0-03`，狀態固定為 `G8_FEATURE_FROZEN_FOR_EXPANSION`。
8. 進入 `CONTENT-P1-00 Existing Capability Reconciliation`，限時盤點與去重，不做新架構研究。
9. 依序施工：P1-01 Topic Matrix／10K inventory → P1-02 ContentSpec＋Locale → P1-03 Coverage／Dedup／Selection → P1-04 10篇 NEW slice → P1-05 四語 batch → P1-06 throughput／idempotency → P1-07 10→100→1000→10K。
10. 10K 後才做 P2：讀既有 GSC snapshots 形成四語 SEO opportunity／rewrite／merge／relink；禁止重做 collector。

## Waiting Conditions

- Candidate review 未完成前：不得整合或開 production mutation 卡。
- `READY-FOR-AUTHORIZATION` 未成立前：不得向 production 寫入。
- 使用者未明確授權 adoption/reset 或 canary：不得執行相關動作。
- P0-02 canary 未成功：不得宣稱 G8 freeze 或進入 sustained 10K publishing。

## Key Decisions & Resolved Questions

- 已確認「G8 freeze」是 feature freeze，不是移除控制。
- 已確認目前不是缺內容研究資料；當下 blocker 是 production closeout。
- 已確認後續開發以既有 implementation、tests、registry donor 為先；外部資料不足時才回報使用者請 GPT 補查。
- 已確認 P1 第一拍只能是 `CONTENT-P1-00`，不是直接另造 Topic Matrix、GSC collector 或 Registry DB。

## 下一手第一拍

只讀：讀本 handoff、`AGENTS.md`、candidate RESULT／execution contract／tripwire；核對 `main`、`origin/main`、candidate SHA 與工作區狀態。先回報「candidate 可整合／需回原 thread Repair」，不得直接 production mutation、canary 或 10K batch。
