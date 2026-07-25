---
card_id: CARD-CONTENT-GEMINI-V4-QUOTA-SHARDING-001
chain_id: CONTENT-GEMINI-V4-MAINLINE-001
status: READY_FOR_REVIEW
ownership: v4_credential_pool_only
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
base_candidate: 5e3939ba46ed37f96a8cc915feacaab1a6ab5015
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_001/quota-sharding-001/
---

# Gemini V4 cross-operation quota sharding

## Root question

讓三個不同Google帳號／project的Gemini credential分攤不同文章operation，同時
保留每個operation恰一個credential、恰一個target process、恰一個model POST、
無retry、無fallback與durable replay。

## Requirements

- `SHARD-001`：pool必須明確opt-in；既有
  `AGY_GEMINI_V4_CREDENTIAL_FILE`單key設定保持相容。
- `SHARD-002`：pool manifest只保存stable slot ID與credential file path，
  不保存key value；manifest與credential files都必須owner-only、regular、
  non-symlink。
- `SHARD-003`：以`pool_id + operation_id`做deterministic selection；slot排序
  canonical，禁止mutable cursor與競態。
- `SHARD-004`：同一operation選定slot後不得更換；429、timeout、transport error
  或nonzero都terminal，禁止同operation換key重打。
- `SHARD-005`：既有ledger replay不讀manifest、不開credential、不重新選slot。
- `SHARD-006`：新structured operation將非敏感`pool_id`、`slot_id`與manifest
  digest綁入receipt及durable ledger事件；舊ledger仍可replay。
- `SHARD-007`：target只收到一個selected credential FD，不知道pool，也不新增
  retry／redirect／fallback。
- `SHARD-008`：flag-off legacy、explicit legacy replay、structured single-key
  與outbox行為不退化。

## Local manifest contract

```json
{
  "schema_version": 1,
  "pool_id": "pantheon-gemini-v1",
  "slots": [
    {
      "slot_id": "account-1",
      "credential_file": "<user-config>/pantheon/gemini-api-key-1"
    }
  ]
}
```

Deploy-time opt-in：`AGY_GEMINI_V4_CREDENTIAL_POOL_FILE`。它與
`AGY_GEMINI_V4_CREDENTIAL_FILE`互斥。共享文件與evidence不得保存本機絕對路徑。

## Allowed files

- 本卡與 `quota-sharding-001/` evidence
- `scripts/agy_gemini_runner.py`
- `scripts/agy_gemini_v4_broker.py`
- `tests/test_agy_gemini_outbox.py`
- `tests/test_agy_gemini_v4_broker.py`
- `docs/pantheon_gemini_reviewer_v4_architecture.md`
- `docs/pantheon_gemini_v4_agy_cli_compatibility.md`

## Forbidden

- `scripts/agy_gemini_v4_structured_target.py`
- `scripts/agy_seo_copy_pipeline.py`
- `app/**`、queue、registry、articles、sitemap、feed
- credential value、CLI OAuth、ADC、login、IAM或global config
- retry、fallback、key rotation within an operation
- real Gemini request、canary、publish、deploy、default promotion、push

## Slices

### SHARD-S1 — Manifest and deterministic selection

- `traces_to`: `SHARD-001`, `SHARD-002`, `SHARD-003`, `SHARD-005`
- dependencies：none
- RED：malformed／unsafe manifest、ambiguous single+pool設定、deterministic
  distribution、replay without manifest。
- GREEN：最小strict loader與lazy opener。

### SHARD-S2 — Durable credential identity

- `traces_to`: `SHARD-004`, `SHARD-006`, `SHARD-007`
- dependencies：SHARD-S1
- RED：new operation缺credential identity不得fork；ledger必須有恰一個
  `CREDENTIAL_SELECTED`；429不得嘗試第二slot。
- GREEN：receipt／command／ledger最小擴充；replay相容舊event chain。

### SHARD-S3 — Regression and operations evidence

- `traces_to`: `SHARD-008`
- dependencies：SHARD-S1、SHARD-S2
- verification：focused RED/GREEN、五套affected suites、py_compile、privacy、
  changed-files、`git diff --check`。

## Gate 1

`PASS`

- 實體卡已建立。
- base candidate為已通過Review、canary與auth-hardening的主線HEAD。
- source與key value未被修改或寫入card。
- frontier：`SHARD-S1`。

## Gate 2

`PASS`

- Pool loader、deterministic selector與lazy credential opener已落地。
- 新operation將credential identity綁入command、receipt與durable ledger。
- 同operation的429、timeout、transport error與nonzero不換slot、不重送。
- 舊ledger replay不讀manifest、不開credential。

## Gate 3

`PASS`

- focused RED：4個預期失敗；GREEN：4 passed。
- 最終affected suites：229 passed。
- `py_compile`、privacy scan、changed-files核對與`git diff --check`通過。
- 本機三slot完成300-operation no-network dry-run；外部request為0。
- 決策：`READY_FOR_REVIEW`；未啟用、未publish、未deploy、未push。
