---
id: CARD-PANTHEON-I18N-REWRITE-4OF4-LOCALE-AUTHORITY-SUCCESSOR-REPAIR-1-20260730-evidence
status: ready-for-re-review
type: repair-evidence
---

# Repair evidence

status: READY_FOR_RE_REVIEW

## Root-cause-to-fix mapping

- `LAS-REV-001`：抽取式 tokenization → anchored whole-value grammar；junk、未列 separator與未消費字元 fail closed。
- `LAS-REV-002`：capitalization shape authority → 明列 `OpenAI`／`API` authority；model code與 number 仍受 bounded grammar 管控。

## Acceptance mapping

- R1：targeted Review group與 direct regression已 GREEN。
- R2：targeted Review group與 direct regression已 GREEN。
- R3：successor independent probes、direct suite、prior Review probes與七檔 regression suite已 GREEN。
- Production compile、debug scan與 working diff check已通過。
- Changed-files allowlist與 evidence local-path／secret／raw-payload scan已通過。
- Single Repair commit與 direct-parent verification由 handoff與交付回報記錄。

## Residual risk

- 明列 authority set 刻意最小；未列新的品牌或 acronym 會 fail closed，需由後續正式需求另行擴充。
- 七檔 regression suite保留一則既有 invalid escape sequence DeprecationWarning，不影響本 Repair 判定。

## External／production actions

未呼叫 provider，未讀寫 production `.work`，未 push、deploy、publish、merge 或建立 re-review。
