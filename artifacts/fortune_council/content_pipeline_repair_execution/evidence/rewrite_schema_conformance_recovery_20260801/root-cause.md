---
id: CARD-PANTHEON-REWRITE-SCHEMA-CONFORMANCE-RECOVERY-20260801-root-cause
status: resolved_candidate
type: evidence
---

# Rewrite schema conformance root cause

## Root question

為什麼 rewrite 的合法 JSON object 會在 broker response-schema 邊界因字串長度不符而終止，無法進入既有 deterministic local gate？

## RED feedback loop

- Command: `.venv/bin/python -m pytest -q tests/test_agy_gemini_outbox.py::test_rewrite_provider_length_mismatch_reaches_local_quality_gate`
- Result: expected `processed` but received `failed / V4BrokerFailure`.
- Symptom match: synthetic transport 回傳合法 JSON object；唯一刻意偏離是 rewrite paragraph 長度 161，現行 provider-facing schema 的 `maxLength=160` 先行拒絕。

## Ranked falsifiable hypotheses

1. **Canonical schema 被直接重用為 provider schema。** 若根因成立，只從 rewrite provider-facing schema 移除 string `minLength/maxLength`，相同 payload 應通過 broker structural validation，並由 `rewrite_quality_findings` 產生 `paragraph_length`。
2. **本機沒有等價的 canonical 長度 gate。** 若根因成立，移除 provider keyword 後 161 字 payload 會失去拒絕訊號；若 `rewrite_quality_findings` 仍回傳 `paragraph_length` 且 eligibility fail closed，則此假說被推翻。
3. **需要修改 broker／runner normalizer。** 若根因成立，單改 pipeline schema seam 不足以讓 RED 轉 GREEN；若同一個未截斷 payload 能原樣通過 `process_once` 並進入 local gate，則此假說被推翻。

## Candidate seam

CodeGraph 指向 `external_candidate_schema`、`validate_candidate`、`rewrite_quality_findings` 與 `OutboxGeminiClient.generate_json`。原始碼確認 rewrite external schema 直接引用 canonical `_article_json_schema("rewrite_existing_body")` 的 `bodySections`，因此把 deterministic quality 長度 keyword 提前成 provider transport contract。

## Hypothesis outcomes

1. **成立。** rewrite external schema 改用明確命名的 provider structural seam，只移除 paragraph string 的 `minLength/maxLength`；四個 synthetic path 均由 broker 成功傳遞至本機。
2. **推翻。** canonical schema 仍保留原長度 bounds；四個 payload 都產生精確 canonical `minLength/maxLength` diagnostic，且 `rewrite_quality_findings` 仍回傳 `paragraph_length`。
3. **推翻。** 未修改 broker、runner 或 normalizer，payload 原樣通過 provider structural validation；沒有 truncate、切字、刪段或補字。

## Repair behavior

既有 bounded content repair 接手本機 `paragraph_length` finding；第二次 writer prompt 含 closed reason，request SHA-256 與首次不同，並受 `max_repairs` 限制。修復後才呼叫 reviewer。

## Scope guard

修正只可作用於 rewrite writer provider schema；canonical `candidate_schema("rewrite_existing_body")`、create/new schema、i18n schema、broker 與 publisher 行為保持不變。
