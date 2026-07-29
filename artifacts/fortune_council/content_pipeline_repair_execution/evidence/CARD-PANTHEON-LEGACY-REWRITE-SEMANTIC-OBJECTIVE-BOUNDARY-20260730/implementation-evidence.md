---
id: CARD-PANTHEON-LEGACY-REWRITE-SEMANTIC-OBJECTIVE-BOUNDARY-20260730-EVIDENCE
status: DELIVERED_CANDIDATE
type: implementation-evidence
dispatch_key: v1:3f53b66a376fec16646a4371f92382c2538707c8289e868a5e67cdfb1bde7bee
activation_token: act-v1:d7db89e7bd68970762ae69c5e6c192f468a956019d3154c075def30c5c4b2d3c
---

# Legacy rewrite semantic/objective boundary implementation evidence

## Contract

- Root question：deterministic gate 已通過時，rewrite Reviewer 誤放在
  `semantic_findings` 的 machine-owned code 是否仍會造成假 `REJECT`。
- Allowlist：`scripts/agy_seo_copy_pipeline.py`、直接相關測試與本 evidence。
- Stop boundary：未修改 deterministic policy、production receipt／queue／approval／ledger、
  article registry、shared metadata、生成頁或 new／i18n lane。

## Preflight

- Formal thread：`019faee9-8e56-7c83-be16-ab19d95bcea6`
- Required base／HEAD：`3ee7b2d3becb8c07f7c62726d14412964739f628`
- Worktree：registered、detached、啟動時 clean、無 `index.lock`
- CodeGraph：bounded prepare 後 indexed HEAD 與 required base 一致；實際語意 query
  定位中央 seam `hydrate_rewrite_review()` 及 normal、repair、release、closure、
  review-existing 等 callers。
- Capability note：worktree-local `uv sync` 因 sandbox cache 權限失敗，`pnpm install`
  因 registry DNS 不可達；Python 驗證改用本機主 checkout 已存在且含 pytest 的 `.venv`，
  未下載或改動 lockfile。

## Root-cause loop

排序假說：

1. `hydrate_rewrite_review()` 將 semantic payload 直接轉成 canonical review，
   未套用 deterministic-authority reconciliation，導致所有 rewrite hydration callers
   都可能接受假 `REJECT`。
2. `objective_observations.code` hydration 使用 `casefold()`，使 schema enum 之外的
   大小寫變體可繞過 exact-code 契約。

Red-capable command：

```text
<main-checkout>/.venv/bin/python -m pytest \
  tests/test_agy_seo_copy_pipeline.py::test_rewrite_ignores_false_body_shape_review_without_spending_writer_repair -q
```

RED 證據：預期只呼叫一次 Writer，實際 `writer_calls == 2`；Reviewer 的純
machine-owned `semantic_findings` 觸發了不必要 repair。

## Implementation

- 在中央 `hydrate_rewrite_review()` 完成 hydration 後，以
  `REWRITE_MACHINE_OWNED_REVIEW_CODES` reconciliation。
- exact canonical machine code 才能被移除；大小寫、alias 或未知 code 不猜測，
  仍保留為 semantic finding／fail closed。
- 純 machine-owned `REJECT` 清空後轉 `APPROVE`；mixed payload 只移除
  machine-owned finding，保留真 semantic finding 與 `REJECT`。
- `objective_observations.code` 改為精確 enum membership；移除 case-insensitive 接受。
- create lane 保留既有 case-normalized reconciliation；multilingual lane 未更動。

## Verification

- 原始 RED 回歸：`1 passed`
- Targeted boundary set：`7 passed`
- SEO copy pipeline 全套：`121 passed`
- SEO publish gate、competitor SEO、coordinator、publisher、multilingual：
  `152 passed`，僅一則既有 `DeprecationWarning`
- 不重複計算 targeted 子集合，共 `273` 個 suite tests 通過。
- `git diff --check`：PASS
- Debug marker scan：無 `[DBG-...]`

## Acceptance mapping

- Pure machine-owned false reject：normal rewrite regression PASS。
- Mixed machine／semantic findings：中央 hydration regression PASS。
- True semantic reject：既有 semantic repair 與 exact-case hostile-label regressions PASS。
- `APPROVE`／`[]`：既有 normal、repair、review-existing regressions PASS。
- Invalid objective code：新增 exact-code fail-closed regression PASS。
- Path consistency：所有 rewrite external-review callers 維持共用
  `hydrate_rewrite_review()`，normal、repair 與 review-existing 均有 regression。

## Remaining risk

- 未重放 production receipt、未啟動 coordinator、未 deploy；依卡片留給部署後 runtime
  原樣重消化。
- CodeGraph 為 worktree-local generated index，未納入 candidate commit。
