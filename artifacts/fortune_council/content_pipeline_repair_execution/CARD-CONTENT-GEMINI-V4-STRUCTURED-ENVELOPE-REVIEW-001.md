# CARD-CONTENT-GEMINI-V4-STRUCTURED-ENVELOPE-REVIEW-001

- card_id: `CARD-CONTENT-GEMINI-V4-STRUCTURED-ENVELOPE-REVIEW-001`
- chain_id: `CONTENT-GEMINI-V4-STRUCTURED-ENVELOPE-REVIEW-001`
- ownership: `independent_v4_structured_envelope_review_only`
- strictness: `strict`
- risk: `high`
- status: `PENDING`
- verdict: `PENDING`

## 審查標的

- Repair candidate:
  `a438bf2dec16fb386b5fe23bec83583140f44ed5`
- candidate parent／Repair provisioning:
  `c7d4e4dd540182b2e0276250222d6264bf2f64cf`
- source Activation-002 evidence:
  `b454dad83ff565fc6a206c80e7b939ff7c7ef3ca`

## 必審項目

1. Activation-002 `JSON_INVALID` 是否正確 localized 到 runner adapter，而不是
   broker／ledger。
2. Flag-on effective prompt 是否 exact 包含：
   - 正確且互斥的 writer／reviewer role
   - no-tool／no-workspace
   - single JSON object／no Markdown code fence
   - canonical compact response schema
   - sanitized user task
3. CommandFrame prompt digest／byte count 與 external request SHA 的雙 binding
   語意是否正確。
4. Flag-off legacy 是否完全 bypass renderer。
5. Flag-on failure是否維持 no fallback；privacy 與 exactly-once 邊界是否維持。
6. 是否存在 schema prompt injection、non-determinism、role confusion 或 prompt
   retention。

## Reviewer 可修改

- 本卡
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_structured_envelope_review_001/**`

## Reviewer 禁止

- 不修改 candidate code、tests、docs 或 Repair evidence。
- 不呼叫 Gemini／agy，不 retry Activation-001／002，不建立第三筆真實 payload。
- 不 merge、push、deploy、publish、default promotion 或 legacy removal。

## 驗證

- 核對 candidate SHA、parent、changed files 與 clean worktree。
- 獨立重跑 RED-capable seam、focused tests 與完整 affected matrix。
- 增加 adversarial role／schema determinism／flag boundary probes。
- 跑 py_compile、privacy scan、scope allowlist 與 `git diff --check`。

## Evidence

`artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_structured_envelope_review_001/`

至少包含：

- `review.md`
- `verification.txt`
- `decision.md`
- `changed-files.txt`

## 交付

只能：

- `DELIVERED_CANDIDATE / GO`
- `DELIVERED_CANDIDATE / NO_GO`
- `BLOCKED`

GO 只代表可回主線考慮後續 activation prep，不是 activation、整合、上線、預設
promotion、legacy removal 或第三次真實外呼授權。
