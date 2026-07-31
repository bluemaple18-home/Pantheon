# EV-CANARY-I18N-REWRITE-001

## Decision

```text
status: GO
lane: i18n-rewrite
run_id: auto-i18n-en-daf6984c146f81cb5738
candidate_identity: auto-i18n-en-daf6984c146f81cb5738/candidate.json
locale: en
article_id: ASTRO-LOVE-01
publisher_decision: PUBLISHED_TRANSLATION
release_commit: d9d1be2353bce1bc251e00f55d17523dcfeb18f9
release_tag: v0.3.189
public_article_count: 504
verified_at: 2026-07-31T14:50:05+08:00
```

## Evidence

- canonical run state 為 `complete`、`approved_by_reviewer=1`；最後 Reviewer
  job `5e9c56ac42e0e3290cdd45df2e242486eed0dce8`。
- candidate article `ASTRO-LOVE-01:en` verdict 為 `APPROVE`，findings 為空。
- Publisher evidence：
  `<publisher-state>/evidence/translation-0.3.189/translation-evidence.json`；
  狀態 `PUBLISHED_TRANSLATION`、`pushed=true`。
- 發布 transaction：3 個 web tests、366 個 release tests、canonical
  probes 與 release-record gate 全部通過。
- production asset 以 cache-busting／no-cache 重查為
  `200 application/javascript`，包含本 run ID、`ASTRO-LOVE-01` 與標題
  `How to Read Relationship Horoscopes Without Letting Them Run Your Love Life`。

## Acceptance mapping

- real rewritten source／candidate／independent review：PASS
- native-quality、deterministic、source-drift gate：PASS
- Publisher／release commit／tag／push：PASS
- production generated asset：PASS
- idle、fixture 或 service-green substitute：未使用
