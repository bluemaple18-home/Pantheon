# Gemini V4 Schema Diagnostic Repair-3 Independent Review

## Verdict

`DELIVERED_CANDIDATE / GO`

## Findings-first

### P0

無。

### P1

無。

### P2

無。

### P3 — size-invalid array 仍全量掃描

- path／line:
  `scripts/agy_gemini_v4_broker.py:839`，
  `scripts/agy_gemini_v4_broker.py:849`
- 觸發：
  response array 已超過 `maxItems`，但 item 本身均符合 `items` schema。
  以 700,000 個 integer、`maxItems=5` 的 synthetic probe 重現；canonical
  payload 仍可落在 2 MiB result ceiling 內。
- 證據：
  parent validator 約 `0.000012s` 即 short-circuit；candidate collector 約
  `0.271071s` 才完成，acceptance 都是 `false`。
- 風險：
  不影響 schema acceptance、privacy、no-fallback 或 exactly-once，但 malformed
  output 可造成 bounded ceiling 內的額外 CPU amplification。
- 建議：
  `maxItems` 已確定 mismatch 後停止 item traversal，或對 diagnostic item
  inspection 設定獨立固定上限；維持最多三筆 diagnostics 與原 boolean semantics。
- 判定：
  非阻塞。2 MiB stdout ceiling 仍提供硬上界，本次不因此降為 `NO_GO`。

## Correctness

- 以 parent commit 的 `_validate_json_schema` 與 candidate collector 執行
  deterministic 50,000-case JSON-compatible differential：
  `0 mismatches / 0 exceptions`。
- `JSON null` 與 JSON array 維持 `NOT_OBJECT`；invalid JSON 維持
  `JSON_INVALID`；schema mismatch、success、nonzero、timeout 與 replay/control
  failure 的既有測試全數通過。
- 最多三筆 diagnostics、最大 path depth 8；unknown additional property 只保留
  parent path，不保存未知 key 或 instance value。

## Security／privacy

- Runner 只接受固定 keyword allowlist、exact `SchemaDiagnostic`、tuple path、
  schema-defined property／items path、深度不超過 8、string token 不超過 64
  且符合 closed pattern、array index `0..1,048,576`。
- Forged scalar、container、unhashable token、過深 path、65 字以上 token、
  10,000 位 integer 與額外 message marker 均未造成 crash 或 raw persistence。
- Failed record 與回傳 failure result 都不含 forged marker；只保存 closed
  `broker_diagnostic`。
- 未保存 prompt、raw stdout／stderr、response body、instance value、credential、
  完整 environment、CLI log 或 validator message。

## Compatibility／regression

- `BrokerResult.schema_diagnostics` 位於 dataclass 尾端且有預設空 tuple；舊 12
  positional required fields與含兩個既有 defaults 的 14 positional fields 均可
  建構。
- Repo 內所有 `BrokerResult` constructors、replay、existing-operation no-resend、
  ledger／anchor 與 failed-record consumers 通過 affected matrix。
- Flag off 仍走單一 legacy call；flag on 任一 malformed／failed V4 result 均
  fail closed，legacy call count 為 0。

## Production schema coverage

下列 8 個 schema 的合法 synthetic sample 均同時被 parent 與 candidate 接受：

- external writer create／optimize／rewrite
- external reviewer
- internal candidate create／optimize／rewrite
- internal reviewer

共列舉 128 條 schema-defined paths，runner 全數接受；觀察最大深度 6，小於限制 8。

## Remaining risk

- 真實 Activation-003 mismatch 的欄位仍未知；本 review 沒有、也不授權 retry。
- P3 bounded-work amplification 尚存，但不改本 candidate 的安全診斷與
  fail-closed 結論。
- GO 不代表 V4 已可放量、成為 default transport 或移除 legacy。
