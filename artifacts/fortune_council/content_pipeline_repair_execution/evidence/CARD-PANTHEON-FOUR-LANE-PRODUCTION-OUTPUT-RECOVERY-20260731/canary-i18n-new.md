# EV-CANARY-I18N-NEW-001

## Decision

```text
status: GO
lane: i18n-new
run_id: auto-i18n-en-cfd7211d31136567123c-replacement-01
candidate_identity: auto-i18n-en-cfd7211d31136567123c-replacement-01/candidate.json
locale: en
article_id: V2-MBTI-PAIR-INTP-ISFP-WORK
publisher_decision: PUBLISHED_TRANSLATION
release_commit: 5fac6eb6626f54968de50f95eff97e3015a4e09e
release_tag: v0.3.188
public_article_count: 504
verified_at: 2026-07-31T14:50:05+08:00
```

## Evidence

- canonical run state 為 `complete`、`approved_by_reviewer=1`；最後 Reviewer
  job `92b7c6385538d712ce5e56838be2cec00fbec4ef`。
- candidate article `V2-MBTI-PAIR-INTP-ISFP-WORK:en` verdict 為
  `APPROVE`，findings 為空。
- Publisher evidence：
  `<publisher-state>/evidence/translation-0.3.188/translation-evidence.json`；
  狀態 `PUBLISHED_TRANSLATION`、`pushed=true`。
- 發布 transaction：3 個 web tests、366 個 release tests、canonical
  probes 與 release-record gate 全部通過。
- production browser 實際渲染
  `https://www.mysticpantheon.com/en/articles/personality/personality-0675`：
  `lang=en`、canonical 正確、H1 為
  `Can INTPs and ISFPs Work Well Together?`、FAQ 存在、console
  warnings/errors 為空。

## Acceptance mapping

- real source／candidate／independent review：PASS
- native-quality、deterministic、source-drift gate：PASS
- Publisher／release commit／tag／push：PASS
- production user path：PASS
- idle、fixture 或 service-green substitute：未使用
