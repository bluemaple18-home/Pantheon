---
id: PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-REPAIR-1-REPRODUCTION
status: PASS
type: evidence
---

# Reproduction

## Root cause

Parent candidate 的 `_create_repair_fields()` 未列
`standalone_answer`，且未知 code 靜默 fallback 至 `bodySections`。因此
`standalone_answer` contract 不含 `answer`，無法提交短 answer 修復。

同時，`_create_repair_contract()` 也會收到獨立 Reviewer 自訂 code；Reviewer
finding 的既有 `bodySections` fallback 是合法 bounded repair 契約，不能被
deterministic fail-closed 一併移除。

## Targeted RED 1

命令：

```bash
uv run pytest tests/test_agy_seo_copy_pipeline.py -k 'standalone_answer or repair_fields or bounded_create_repair'
```

| 執行 | Exit code | 摘要 |
|---|---:|---|
| sandbox 首次執行 | 2 | uv cache 權限阻擋，pytest 未開始；不列為有效 RED。 |
| 受控 cache 存取重跑 | 1 | `1 failed, 89 deselected`；`standalone_answer` 實得 `{'bodySections'}`，預期 `{'answer'}`。 |
| 加入最小 mapping 後 | 0 | `1 passed, 89 deselected`。 |

## Targeted RED 2

加入 deterministic 完整性、fail-closed、Reviewer fallback、bytes-preserving
merge 與短 answer gate tests 後重跑同一命令：

| 執行 | Exit code | 摘要 |
|---|---:|---|
| 修正來源區分前 | 1 | `5 failed, 1 passed, 89 deselected`；舊介面無法標示 deterministic findings。 |
| 完成最小來源區分後 | 0 | `6 passed, 89 deselected`。 |

## 假說處置

- 假說 A 成立：明確 `standalone_answer -> answer` 後第一個 targeted test
  轉綠。
- 假說 B 成立：只有 deterministic 來源啟用 unmapped fail-closed；Reviewer
  自訂 `copy`、`TEMPLATE_STRUCTURE`、`search_intent_mismatch` 仍產生
  `('bodySections',)` contract。
- 無額外 debug instrumentation；未加入 `[DBG-...]`。
