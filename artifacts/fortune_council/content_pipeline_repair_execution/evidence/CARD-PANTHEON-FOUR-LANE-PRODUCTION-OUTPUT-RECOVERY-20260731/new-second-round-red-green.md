# EV-NEW-SECOND-ROUND-RED-GREEN-001

## Scope

```text
lane: new
run_id: auto-new-v1-20260731-122-01
failure: false machine-owned reviewer rejection
production_publication_during_repair: false
```

## Observed production evidence

The run produced a real candidate after bounded Writer transport、schema and
semantic repair. The final deterministic findings file was empty, but the
external Reviewer returned:

```text
code: banned_phrase_usage
location: description
claimed_phrase: 帶您
```

The current trusted policy does not ban the standalone phrase `帶您`.
`BANNED_PHRASES` does not contain it, and `GENERIC_AI_PHRASES` only contains
the exact phrase `本篇帶您`. The local deterministic gate therefore correctly
returned no findings.

## Root cause

`banned_phrase_usage` is an external Reviewer alias for an objective,
machine-owned policy check. It was missing from
`MACHINE_OWNED_REVIEW_CODES`, so reconciliation preserved the false finding
as if it were semantic. The bounded repair mapper did not recognize that
external alias either and defaulted to repairing `bodySections`, while the
Reviewer claimed the problem was in `description`.

The repeated-looking attempts had three separate causes:

1. transport timeout retries;
2. bounded Writer schema repairs;
3. bounded semantic repairs.

One manual coordinator replay also omitted the installed production model
environment, temporarily creating full and lite request lineages in the same
run. All subsequent replays were pinned back to:

- Writer: `gemini-3.5-flash-lite`
- Reviewer: `gemini-3.1-flash-lite`

## RED

The public run seam was extended with a Reviewer payload containing
`banned_phrase_usage` while the trusted deterministic gate returned no
findings:

```text
expected: APPROVE
actual: REJECT
```

## Minimal repair

Add `banned_phrase_usage` to `MACHINE_OWNED_REVIEW_CODES`. This does not
change the trusted banned-phrase lists or weaken any deterministic check. It
only prevents the external Reviewer from inventing an objective policy
failure that local code did not observe.

## GREEN

```text
targeted regression: 2 passed
SEO pipeline + outbox: 267 passed in 64.00s
full suite: 818 passed, 2 warnings in 144.03s
git diff --check: PASS
```

The preserved production candidate and Reviewer response were replayed
offline after the repair:

```text
status: complete
approved_by_reviewer: 1
final_verdict: APPROVE
final_findings: []
additional Gemini calls for replay: 0
```

At this checkpoint the explicitly capped second-round call counter is
`7 / 40`. No candidate has yet been passed to Publisher.

## Successful production release

修補部署後，保留的 production candidate 經 Publisher dry-run 唯一命中本
run。正式結果：

```text
run_id: auto-new-v1-20260731-122-01
article_id: V2-MBTI-PAIR-INTP-ISFP-WORK
version: 0.3.186
commit: 1b845702db2cd561a4559d7aa5a6bab7954ba4cb
tag: v0.3.186
status: PUBLISHED
validator_result: PASS
pushed: true
public_article_count: 504
```

生成 module：
`app/web/static/article-expansion-agy-auto-new-v1-20260731-122-01.js`。release
通過 clean-origin、Reviewer hash、deterministic quality、batch uniqueness、
focused pipeline 與 release-record gate；不是 idle、fixture 或歷史發布。
