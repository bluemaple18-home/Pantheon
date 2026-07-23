# Gemini V4 Publish-main Integration｜Independent Review

## Findings

未發現阻塞問題；未識別 P0–P3 具體 finding。

## Spec axis

- Review啟動於獨立clean detached worktree；provisioning HEAD
  `ba22c050c1091860548f47c3135d9b9900a2990e`的唯一parent精確為fixed candidate，
  且只新增本Review卡。實際gitdir沒有`index.lock`。
- Publish base `78d8d2fc91bd435adf371762b9ff49665cdc26d5`精確帶有tag
  `v0.3.7`。Integration card commit
  `2cba7a3898a1c21950c21bdfa99273eac05e32dd`的唯一parent為publish base，且只新增
  Integration卡。
- Integration merge `99318a01d77804b90490ae87bc5485e0ddb85960`的first parent為
  Integration card commit，second parent精確為V4 reviewed tip
  `b2c51d4ee9da7a45a05be8c59725a28020d9bb60`。
- Fixed candidate `b0d0f6dd855bb185c9958c7a9cf6bd0ad178a8cc`的唯一parent為integration
  merge，且只加入Integration卡狀態與五個required evidence檔。Publish base與V4
  reviewed tip都是candidate ancestor。
- Candidate中的V4 broker、runner、focused tests與兩份V4架構文件和reviewed tip
  byte-identical，沒有重作或挑選patch。
- Flag off只有legacy branch；flag on只走V4 broker。V4 receipt、caller contract或
  parsed result任一不符即fail closed，沒有進入legacy fallback。
- Broker以exclusive ledger create、external anchor CAS、closed replay FSM與單一
  `EXEC_CONFIRMED`綁定exactly-once；既有operation只replay、不補事件、不重送。
  Schema-valid output在control byte count／SHA-256與ledger anchor一致後，才保留已驗證
  raw bytes供parsed result使用。

## Zero-drift proof

- `app` tree在base與candidate皆為
  `6adf22aa5bf23b3c7f0e8e9edd0436b43dc5dee1`。
- `ops/launchd` tree在base與candidate皆為
  `8ad95972f43062ff657ce94b36c1b50774e222f5`。
- `scripts/agy_content_publisher.py` blob皆為
  `9829981f810797e578ce016ea2eb40d520c8726d`。
- `scripts/agy_seo_copy_pipeline.py` blob皆為
  `6a0ac7d5d3d7c96ddf45b94f670dae19403d1b51`。
- `scripts/generate_feed.py` blob皆為
  `90435969096e848acafd518b266e0a6c2ed799e8`。
- `scripts/prerender_article_shells.py` blob皆為
  `528a1e2ca3cbd56298e03e5219724bbd48a6de3f`。
- Base-to-candidate scoped diff對`app/**`、publisher、SEO pipeline、feed、
  prerender與`ops/launchd/**`為空；changed-path名稱掃描也沒有article、registry、
  metadata、sitemap、feed或prerender命中。

## Standards axis

- Base-to-integration-merge有73個changed paths；加入五個integration evidence後，
  base-to-candidate為78個unique paths。Candidate direct commit只有6個paths，全部
  符合Integration owner allowlist；Review provisioning commit只有本Review卡。
- Regression為`142 passed`：V4 focused 74、legacy publishing 57、coordinator 6、
  publisher 5。
- Flag-off legacy／flag-on no-fallback targeted為`6 passed`；
  output-binding／exactly-once targeted為`4 passed`。兩組都已包含於142，不重複計數。
- Broker、runner、publisher、SEO pipeline與六個相關test檔`py_compile`通過。
- Candidate／Review provisioning的`git diff --check`、privacy、allowlist與
  changed-Python `[DBG-`掃描通過。
- Review期間external Gemini／agy invocation為`0`；沒有repair、merge、push、
  deploy、publish、activation、default promotion或legacy removal。

## Open questions

無。

## Remaining risks

- 本機read-only `origin/main` snapshot已是
  `1eb311f49c720925501a1fa3dfc9e2b492e71451`，其subject為v0.3.8 publication；
  locked base與該snapshot相差一個publication commit。Candidate與該moving ref彼此
  都不是對方ancestor，不能直接視為可遠端整合。
- GO只允許進入publisher coordination與final sync。同步moving publication ref後，
  必須重新驗證ancestry、zero drift與受影響tests。
- 本Review不授權遠端merge、push、deploy、publish、activation、default promotion
  或legacy removal。
