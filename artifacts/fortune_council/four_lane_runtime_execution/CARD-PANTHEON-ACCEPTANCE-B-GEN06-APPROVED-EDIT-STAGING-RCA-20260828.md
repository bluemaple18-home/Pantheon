# PANTHEON Acceptance B Gen06 Approved Edit Staging RCA

## 工作名稱

Gen06 formal-approved edited candidate 綁回既有 production translation run 的 staging 缺口根因分析。

## 目標

對 `approved edited candidate -> existing terminal-rejected production translation run -> staging-only handoff` 的 `BLOCKED_NO_FORMAL_STAGING_SEAM` 做唯讀 RCA，產出單一根因裁決，並判定是否足以開一張 bounded Repair。

## 鎖定身份

- production run：`auto-i18n-ja-1414b75a404721e95e74`
- generation：`Gen06`
- terminal actor：`831c536...`
- approved candidate SHA-256：`a64d8a33b0b70933134452491c10058e820dd93d5c748d3cc220bbfc25da7b9c`
- formal review：`APPROVE_READY_FOR_STAGING`，`findings=[]`

## 可改範圍

- 本卡。
- 唯一 evidence 目錄：`artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_approved_edit_staging_rca_20260828/`。

## 禁止範圍

- 不修改 production translation run、locale registry、continuation queue、actor、manifest 或 publisher state。
- 不修改 source 或 tests，不建立 Repair，不建立 Gen07。
- provider、coordinator、publish、commit、tag、push 呼叫均為 0。
- 保留既有 untracked files，不清理、不覆寫其他任務 artifacts。

## 必須閉合的四項證據

1. 最後成功或 intended comparable 的 approved-edit/staging 行為；若從未存在，以 git history 與 contract 證明 `NO_PRECEDENT`。
2. 找出形成缺口的 commit／機制或 design omission，區分 edit review、run terminalization、staging 與 publisher boundary。
3. 明確列出 approved candidate/review、production run audit、registry/continuation、staged/publisher handoff 的 authoritative owner，以及 promotion/replacement/publisher 邊界。
4. 實跑一條 RED-capable fixture/command，穩定重現：exact approved candidate + formal review 存在、既有 run terminal rejected，但沒有正式 plan-only/apply staging 入口；同時證明 provider/coordinator/publish/tag/push=0 且 production bytes before==after。

## 假說

- A：既有正式 seam 被漏找，或既有 seam 可合法組合成 staging-only flow。
- B：設計契約刻意要求直接 apply/publish，原本就沒有中間 staging；目前 blocker 是錯誤 boundary expectation。
- C：recovery/edit flow 缺少正式 bind/seal operation，導致 formal-approved edited candidate 無法接回既有 run audit 與 publisher handoff。

至少證偽兩個假說，只保留一個 root verdict。

## 驗收與交付

- CodeGraph 先於 source decision；不可用時記錄 degraded，再做限域 `rg` 與 git archaeology。
- 輸出 `RESULT.md`，事實與詮釋分離，含四證據、假說裁決、單一 root verdict。
- 若需 implementation frontier，必須鎖定 exact files/functions/CLI、SHA locks、audit preservation、rollback receipt、idempotence、negative tests，並回答 `why_not_less`、`why_not_more`、`do_not_absorb`。
- 跑受影響唯讀驗證與 `git diff --check`。
- 最終明確回答：是否允許下一張 bounded Repair。
