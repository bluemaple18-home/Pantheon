# EV-CANARY-REWRITE-001

## Decision

```text
status: GO
lane: rewrite
run_id: legacy-auto-sweep-v1-astrology-0004-astro-love-01-retry-01
candidate_identity: legacy-auto-sweep-v1-astrology-0004-astro-love-01-retry-01/candidate.json
article_id: ASTRO-LOVE-01
publisher_decision: PUBLISHED_REWRITE
release_commit: 2c1b5652b6b978335173c3382955166ec093de27
release_tag: v0.3.187
public_article_count: 504
verified_at: 2026-07-31T14:50:05+08:00
```

## Evidence

- 官方 seeder 在保留 orphan historical state 的前提下建立唯一 retry lineage；
  不是 fixture，也沒有重置 production state。
- 真實 candidate 與 review 存在；`ASTRO-LOVE-01` 最終 Reviewer verdict 為
  `APPROVE`，findings 為空。
- Publisher evidence：
  `<publisher-state>/evidence/rewrite-0.3.187/rewrite-evidence.json`。
- evidence 狀態為 `PUBLISHED_REWRITE`、`validator_result=PASS`、
  `pushed=true`，且只發布本 run。
- 生成 body override：
  `app/web/static/article-rewrite-agy-rewrite-20260731-01.js`；registry 將
  `ASTRO-LOVE-01` 對應至 `astrology-0004`。

## Acceptance mapping

- real eligible source／candidate／review：PASS
- Publisher source-drift、hash、rewrite deterministic gate：PASS
- release commit／tag／push：PASS
- public generated artifact：PASS
- idle、fixture 或 service-green substitute：未使用
