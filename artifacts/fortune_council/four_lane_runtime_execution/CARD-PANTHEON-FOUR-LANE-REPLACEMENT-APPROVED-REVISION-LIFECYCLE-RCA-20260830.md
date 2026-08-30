# Pantheon 四線：replacement approved revision lifecycle RCA

## 工作名稱 → 正在做什麼 → 現在狀態

`Replacement approved revision lifecycle RCA` → 唯讀稽核 `attempts` replacement 從人工修稿、Formal Reviewer、staging 到 public publisher 的 authority chain → `RCA_COMPLETE_NO_GO_SINGLE_ADAPTER`。

## Concrete failure

- run：`auto-i18n-en-aa637e1bf05d3ad21429-replacement-01`
- production lifecycle owner：`attempts/01..03`；root candidate/review 是 attempts/03 terminal audit。
- Formal Reviewer：job `af0a7de946841d3e899f7b7aeb8c3993762775d3`，`APPROVE_READY_FOR_STAGING`。
- 現有 `stage-approved-edited-candidate` 只接受 `continuation/state.json + generations/<terminal>`，且 root terminal review 必須 `REJECT + hard_failure=true + findings`。
- replacement 沒有 continuation/generations，root review 是普通 `REJECT`，所以 formal plan 在讀取 `continuation/state.json` 時 fail closed。

## Scope

唯讀回答：last-good／formation；authoritative owners；downstream hard bindings；既有 seal/stage/publisher 能否接 lifecycle-neutral adapter；exact provider=0 RED；為何不能只修 parser；最小 frontier 或 NO_GO。

## 禁止範圍

- 不改 source、tests、runtime、queue、registry、publisher ledger 或 public content。
- 不呼叫 provider／publisher，不 stage、tag、push、promotion 或 activation。
- 不建立 Repair，不偽造 continuation/generations/hard_failure。
- 不新增 registry、FSM、DB、canonical writer 或第二套 publisher。

## 必查 consumers

1. approved revision stage planner／apply／loader／rollback。
2. publisher `collect_ready_translation_runs` 的 current locks。
3. staged candidate apply boundary。
4. i18n-rewrite 對既有 `(article_id, locale)` 的 public record ownership。
5. release transaction、ledger staging receipt、exact selector、tag/push/public URL 邊界。

## Acceptance

- 使用 `agentic-workflow-audit` 六項格式與兩個試金石。
- 單一裁決，明列 why_not_less／why_not_more／do_not_absorb。
- exact production-shaped provider=0 RED 至少覆蓋 staging blocker 與下一個 publisher apply blocker。
- production run tree、registry、ledger、public locale registry/module bytes before==after；outbox/processing=0。
- `git diff --check` PASS。

## 交付

`PANTHEON-FOUR-LANE-REPLACEMENT-APPROVED-REVISION-LIFECYCLE-RCA-20260830/RESULT.md`
