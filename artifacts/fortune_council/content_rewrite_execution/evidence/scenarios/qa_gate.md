# CARD-CONTENT-REWRITE-005 Scenarios QA Gate

## Scope

- Card path requested by delegation was not present in this worktree: `artifacts/fortune_council/content_rewrite_execution/CARD-CONTENT-REWRITE-005-scenario-batch.md`.
- Execution followed the full delegation payload in the Codex handoff message.
- Edited body library only: `app/web/static/article-bodies-second-batch.js`.
- Added evidence only under: `artifacts/fortune_council/content_rewrite_execution/evidence/scenarios/`.
- Scenario article scope: `THEME-LOVE-01..04`, `THEME-CAREER-01..04`, `THEME-INTERPERSONAL-01..02`, `THEME-WEALTH-01..03`, `THEME-LIFE-01..02`.

## Per-Article QA

| article slug | direct scenario answer | scenes | observable verbs | tool use bounded | limitation after inference | banned/template terms |
|---|---:|---:|---:|---:|---:|---:|
| `love-tarot-questions` | pass | 6 | 15 | pass | pass | pass |
| `long-situationship-stuck` | pass | 4 | 9 | pass | pass | pass |
| `before-getting-back-together` | pass | 5 | 9 | pass | pass | pass |
| `relationship-insecurity` | pass | 2 | 6 | pass | pass | pass |
| `career-fortune` | pass | 6 | 8 | pass | pass | pass |
| `hard-work-not-seen` | pass | 4 | 9 | pass | pass | pass |
| `should-i-change-job` | pass | 4 | 6 | pass | pass | pass |
| `before-starting-business` | pass | 4 | 5 | pass | pass | pass |
| `relationships-stuck` | pass | 7 | 6 | pass | pass | pass |
| `friendship-changing` | pass | 9 | 8 | pass | pass | pass |
| `wealth-fortune` | pass | 10 | 4 | pass | pass | pass |
| `money-anxiety` | pass | 12 | 5 | pass | pass | pass |
| `hard-to-save-money` | pass | 11 | 7 | pass | pass | pass |
| `life-direction` | pass | 6 | 6 | pass | pass | pass |
| `move-or-wait` | pass | 6 | 11 | pass | pass | pass |

## QA Method

- `scenes`: counted concrete situation markers such as `例如`, `你可能`, `如果`, `若`, and concrete life-scene nouns like `訊息`, `會議`, `求職網站`, `銀行 App`, `帳戶`, `收入`, `支出`.
- `observable verbs`: counted concrete actions including `查看`, `回想`, `安排`, `回應`, `觀察`, `記錄`, `列出`, `傳`, `約`, `說明`, `計算`, `檢查`, `訪談`, `報價`, `標出`, `比對`.
- `tool use bounded`: checked that tarot/personality/chart/astrology language only supports the scenario question and does not become the article's main lesson.
- `limitation after inference`: checked that limits appear after scenario explanation or tool use, not as a detached boilerplate block.
- `banned/template terms`: checked against `全面解析`, `深度解析`, `快速變化的時代`, `不可或缺`, `賦能`, `不僅`, `更是`, `總而言之`, `值得注意的是`, `必看`, `一定`, `保證`, `注定`, `抓住基本語氣`, `星盤語言要能回到`.

## Validation Evidence

```text
node --check app/web/static/article-bodies-second-batch.js
exit 0
```

```text
rg -n '全面解析|深度解析|快速變化的時代|不可或缺|賦能|不僅|更是|總而言之|值得注意的是|必看|一定|保證|注定|抓住基本語氣|星盤語言要能回到' app/web/static/article-bodies-second-batch.js
exit 1, no matches
```

```text
.venv/bin/python -m pytest tests/test_web.py
28 passed, 1 warning in 1.88s
```

```text
git diff --check
exit 0
```
