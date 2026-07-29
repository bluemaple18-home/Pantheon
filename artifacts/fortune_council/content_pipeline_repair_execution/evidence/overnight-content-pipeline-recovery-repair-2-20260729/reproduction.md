---
id: PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-REPAIR-2-REPRODUCTION
status: PASS
type: evidence
---

# Reproduction

## P1：正式 short-answer 入口

命令：

```bash
uv run pytest tests/test_agy_seo_copy_pipeline.py -k 'standalone_answer or false_social_origin or repair_fields or bounded_create_repair or run_writer_reviewer'
```

| 執行 | Exit code | 摘要 |
|---|---:|---|
| sandbox 首次執行 | 2 | uv cache 權限阻擋，pytest 未開始；不列為有效 RED。 |
| 受控 cache 存取重跑 | 1 | 有效 RED：`1 failed, 7 passed, 88 deselected`。第二次 Writer 仍收到完整 create schema，證明初始 short answer 被當成 schema failure。 |
| 最小 hydration/gate 修補後 | 1 | production path 已到 Reviewer；失敗原因是 test 對 prompt 內 policy catalog 的過寬字串斷言，不是產品症狀。 |
| 校正斷言後 | 0 | `8 passed, 88 deselected`；正式 E2E 轉綠。 |

有效 RED 根因：`run_writer_reviewer()` 初始 create 呼叫
`hydrate_candidate()` 時完整 `validate_candidate()` 先拋出
`standalone_answer`，candidate 與 deterministic findings 均未保存。

## P2：`false_social_origin` 欄位定位

同一 targeted command：

| 執行 | Exit code | 摘要 |
|---|---:|---|
| 第一個 fixture 執行 | 1 | fixture 缺既有 `Pantheon 64 分支` 前置條件；不列為有效 RED。 |
| 補齊前置條件後 | 1 | 有效 RED：`2 failed, 8 passed, 88 deselected`；title-only finding contract 實得 `bodySections`。 |
| 共用 predicate 修補後 | 1 | product mapping 已正確；body-only fixture 覆蓋了必要 Pantheon context，屬 test fixture 缺陷。 |
| 補回 context 後 | 0 | `10 passed, 88 deselected`。 |

有效 RED 根因：validator 對串接後全文使用 inline regex，但 Repair-1 對
`false_social_origin` 固定回傳 `bodySections`，未定位實際命中欄位。

## 假說處置

- 假說 A 成立：初始／intermediate create 只做 structural validation，
  deterministic 清零後執行 full policy gate，正式 E2E 以
  `writer → writer → reviewer` 收斂。
- 假說 B 成立：validator 與 repair locator 共用 predicate 後，四個單欄與
  多欄聯集均精確授權；跨欄拼接但單欄無命中時 fail closed。
- 無 debug instrumentation；`[DBG-...]` 掃描無命中。
