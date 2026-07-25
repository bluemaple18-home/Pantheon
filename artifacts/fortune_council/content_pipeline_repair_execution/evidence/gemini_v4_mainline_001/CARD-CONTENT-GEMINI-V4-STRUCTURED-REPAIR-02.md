---
card_id: CARD-CONTENT-GEMINI-V4-STRUCTURED-REPAIR-02
chain_id: CONTENT-GEMINI-V4-MAINLINE-001
status: REPAIR_READY
role: repair_executor
ownership: v4_structured_repair_only
generation: Repair-2
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: provider schema型別語意與非有限數值會直接影響 exactly-once operation 的 fail-closed correctness
reviewer_thread_id: 019f9548-1dba-7781-9890-5dd54f669419
review_verdict: CHANGES_REQUESTED
parent_candidate: 878ad3872e2fbf8bf135ddbff2a6fb596e7c96df
repair_limit: final_repair
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_001/repair-02/
allowlist:
  - scripts/agy_gemini_v4_structured_target.py
  - scripts/agy_gemini_v4_broker.py
  - tests/test_agy_gemini_v4_structured_target.py
  - tests/test_agy_gemini_v4_broker.py
  - docs/pantheon_gemini_reviewer_v4_architecture.md
  - docs/pantheon_gemini_v4_agy_cli_compatibility.md
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_001/CARD-CONTENT-GEMINI-V4-STRUCTURED-REPAIR-02.md
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_001/repair-02/**
forbidden_scope:
  - scripts/agy_gemini_runner.py
  - scripts/agy_gemini_outbox.py
  - scripts/agy_seo_copy_pipeline.py
  - app/**
  - CHANGELOG.md
  - pyproject.toml
  - package.json
  - credential content or global credential/config changes
  - real Gemini/API/agy generation
  - merge, push, deploy, publish, activation and default promotion
---

# Gemini V4 Structured Transport Repair-2

這是 chain 的最後一輪 Repair。只修同一 Reviewer re-review 中未關閉的
`F002`、`F003`；保留已關閉的 `F001`、`F004`、`F005`。不得新增 finding、
擴充功能、重寫 broker或自審。Repair-2 後若再 `CHANGES_REQUESTED`，主線必須
`BLOCKED / REVIEW_REPAIR_LIMIT`，不得開 Repair-3。

## CONTENT-GEMINI-V4-MAINLINE-001-F002 — P1

### Failure

`project_provider_schema()` 只依關鍵字名稱篩選，未驗證關鍵字是否適用目前
schema type，因此會接受並送出：

- boolean + enum
- string + minimum
- number + format

### Required fix

- provider projection v1 必須具型別感知。
- string只允許 string適用 constraints；number/integer只允許 numeric
  constraints；array/object/boolean/null各自使用官方 subset。
- enum若允許，所有值必須符合 schema type；bool不得等同 integer。
- format只允許官方支援且適用 string的 closed values。
- numeric bounds必須是有限 number，且 integer schema的 bounds契約明確。
- caller-only `minLength/maxLength` 可留在完整 caller schema，但不得送 provider。
- current production article schemas仍能投影；錯置 type/keyword組合必須在外呼前
  fail closed。

### RED

至少涵蓋 Reviewer 三個反證、錯型 enum、非有限 bound、合法 string enum／format、
合法 numeric enum／bounds及 current article schemas。

## CONTENT-GEMINI-V4-MAINLINE-001-F003 — P2

### Failure

Python `json.loads` 接受 `NaN/Infinity`，現有 canonical serializer也會輸出；
numeric comparisons 對 `NaN` 均為 false，導致非法 JSON通過 local schema gate。

### Required fix

- 所有 structured target 的外部 JSON boundary 使用 `parse_constant` fail closed，
  至少涵蓋 provider envelope與provider text result。
- canonical JSON serialization使用 `allow_nan=False`，不得輸出
  `NaN/Infinity/-Infinity`。
- broker解析 target stdout時同樣拒絕非有限 constant。
- broker numeric validator對 value、minimum、maximum明確檢查 finite；非法值或
  schema bound不得被判為 `VALID`。
- 不得 tolerant parse、轉成 null、clamp或自動修值。

### RED

涵蓋 provider envelope text中的 `NaN/Infinity/-Infinity`、broker raw result、
canonical serialization、nested value及非有限 schema bound；有限邊界值仍通過。

## TDD 與驗證

逐 finding 執行：

1. 新增 public/observable negative test並實際跑 RED。
2. 最小 production修正。
3. focused GREEN後跑兩個受影響 suites。
4. 重跑 Repair-1 的五套受影響 suite，確保 F001/F004/F005不退化。

Required final verification：

- `tests/test_agy_gemini_v4_structured_target.py`
- `tests/test_agy_gemini_v4_broker.py`
- `tests/test_agy_gemini_outbox.py`
- `tests/test_agy_gemini_v4_architecture_probe.py`
- `tests/test_agy_seo_copy_pipeline.py`
- `py_compile`
- privacy/secret/debug/allowlist scan
- `git diff --check`
- clean worktree after單一 candidate commit

Evidence只寫 `repair-02/`：`root-cause.md`、`red-green.txt`、
`finding-matrix.md`、`verification.txt`、`changed-files.txt`、`decision.md`。
不得保存 prompt、credential、provider body、完整環境或本機私密絕對路徑。

交付只能是 `REPAIR_READY_FOR_REVIEW` 或 `BLOCKED`。完成後由主線送回同一
Reviewer thread `019f9548-1dba-7781-9890-5dd54f669419` re-review；Repair executor
不得宣稱 `GO` 或執行 real canary。
