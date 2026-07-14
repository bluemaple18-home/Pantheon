# CARD-CONTENT-REWRITE-004 verification

## Scope

- Personality foundation and single-type pages:
  - `MBTI-BASE-01` to `MBTI-BASE-04`
  - `MBTI-TYPE-INTJ`, `MBTI-TYPE-INFP`, `MBTI-TYPE-INFJ`, `MBTI-TYPE-ENFP`
  - `MBTI-TYPE-ENTJ`, `MBTI-TYPE-ENTP`, `MBTI-TYPE-ISFJ`
  - `MBTI-TYPE-INTP`, `MBTI-TYPE-ISTJ`, `MBTI-TYPE-ISTP`, `MBTI-TYPE-ISFP`, `MBTI-TYPE-ENFJ`, `MBTI-TYPE-ESTJ`, `MBTI-TYPE-ESFJ`, `MBTI-TYPE-ESTP`, `MBTI-TYPE-ESFP`
- Fortune/chart foundation and single-palace pages:
  - `CHART-BASE-01`, `CHART-BASE-02`
  - `CHART-ZIWEI-01` to `CHART-ZIWEI-07`

## Files changed

- `app/web/static/article-meta.js`
- `app/web/static/article-bodies-second-batch.js`
- `app/web/static/article-registry.js`

## Article QA

All target articles passed the local content QA script:

```text
MBTI-BASE-01 personality-0001 PASS scenes=15 limits=14 faq=5
MBTI-BASE-02 personality-0002 PASS scenes=22 limits=20 faq=5
MBTI-BASE-03 personality-0003 PASS scenes=15 limits=14 faq=5
MBTI-BASE-04 personality-0004 PASS scenes=15 limits=13 faq=5
MBTI-TYPE-INTJ personality-0005 PASS scenes=17 limits=14 faq=5
MBTI-TYPE-INFP personality-0006 PASS scenes=15 limits=13 faq=5
MBTI-TYPE-INFJ personality-0007 PASS scenes=14 limits=12 faq=5
MBTI-TYPE-ENFP personality-0008 PASS scenes=16 limits=12 faq=5
CHART-BASE-01 fortune-0001 PASS scenes=13 limits=15 faq=5
CHART-BASE-02 fortune-0002 PASS scenes=13 limits=16 faq=5
CHART-ZIWEI-01 fortune-0003 PASS scenes=14 limits=16 faq=5
CHART-ZIWEI-02 fortune-0004 PASS scenes=13 limits=15 faq=5
CHART-ZIWEI-03 fortune-0005 PASS scenes=14 limits=14 faq=5
CHART-ZIWEI-04 fortune-0006 PASS scenes=15 limits=16 faq=5
CHART-ZIWEI-05 fortune-0007 PASS scenes=13 limits=15 faq=5
MBTI-TYPE-ENTJ personality-0009 PASS scenes=17 limits=15 faq=5
CHART-ZIWEI-06 fortune-0008 PASS scenes=13 limits=14 faq=5
MBTI-TYPE-ENTP personality-0010 PASS scenes=14 limits=13 faq=5
CHART-ZIWEI-07 fortune-0009 PASS scenes=13 limits=17 faq=5
MBTI-TYPE-ISFJ personality-0011 PASS scenes=16 limits=13 faq=5
MBTI-TYPE-INTP personality-0012 PASS scenes=16 limits=17 faq=5
MBTI-TYPE-ISTJ personality-0013 PASS scenes=15 limits=13 faq=5
MBTI-TYPE-ISTP personality-0014 PASS scenes=17 limits=14 faq=5
MBTI-TYPE-ISFP personality-0015 PASS scenes=16 limits=14 faq=5
MBTI-TYPE-ENFJ personality-0016 PASS scenes=16 limits=13 faq=5
MBTI-TYPE-ESTJ personality-0017 PASS scenes=15 limits=16 faq=5
MBTI-TYPE-ESFJ personality-0018 PASS scenes=16 limits=14 faq=5
MBTI-TYPE-ESTP personality-0019 PASS scenes=14 limits=12 faq=5
MBTI-TYPE-ESFP personality-0020 PASS scenes=15 limits=15 faq=5
SUMMARY pass=29/29
```

Checks covered:

- No target-rendered blocker phrase hits for: `全面解析`, `深度解析`, `不可或缺`, `賦能`, `必看`, `一定`, `保證`, `注定`, `入口`, `標籤頁`, `集結頁`, `五大主題文章`, `公開文章負責`, `公開文章的任務`, `不是想背`, `心理診斷`, `投資建議`, `財運爆發`, `診斷`.
- Each target article has at least one concrete scenario marker.
- Each target article has at least one explicit limitation paragraph.
- Each target article renders 5 FAQ items.
- Each rendered body section has at least 2 paragraphs.

## Verification commands

```text
node --check app/web/static/article-registry.js
node --check app/web/static/article-meta.js
node --check app/web/static/article-bodies-second-batch.js
node --check app/web/static/article-bodies-next-30.js
uv run pytest tests/test_web.py
git diff --check
```

Results:

- JS syntax checks: passed.
- Full public article length sweep: passed; no articles below current test threshold.
- `tests/test_web.py`: 31 passed, 1 existing StarletteDeprecationWarning.
- `git diff --check`: passed.

## Blockers

- None.
