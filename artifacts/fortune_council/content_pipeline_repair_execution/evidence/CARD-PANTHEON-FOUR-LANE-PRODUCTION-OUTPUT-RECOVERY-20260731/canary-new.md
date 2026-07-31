# EV-CANARY-NEW-001

## Decision

```text
status: GO
lane: new
run_id: auto-new-v1-20260731-122-01
candidate_identity: auto-new-v1-20260731-122-01/candidate.json
article_id: V2-MBTI-PAIR-INTP-ISFP-WORK
publisher_decision: PUBLISHED
release_commit: 1b845702db2cd561a4559d7aa5a6bab7954ba4cb
release_tag: v0.3.186
public_article_count: 504
verified_at: 2026-07-31T14:50:05+08:00
```

## Evidence

- 真實 production candidate、approval 與 review 均存在；Reviewer 最終為
  `APPROVE`，findings 為空。
- Publisher evidence：
  `<publisher-state>/evidence/publish-0.3.186/publish-evidence.json`。
- evidence 狀態為 `PUBLISHED`、`validator_result=PASS`、`pushed=true`；
  run ID 與 article ID 均唯一命中。
- release commit 與 annotated tag 均可解析到同一 commit。
- 生成產物：
  `app/web/static/article-expansion-agy-auto-new-v1-20260731-122-01.js`；
  registry 與 article metadata 已引用該 module。

## Acceptance mapping

- real provider／candidate／review：PASS
- Publisher clean-origin、hash、deterministic、uniqueness gate：PASS
- release commit／tag／push：PASS
- public generated artifact：PASS
- idle、fixture 或 service-green substitute：未使用
