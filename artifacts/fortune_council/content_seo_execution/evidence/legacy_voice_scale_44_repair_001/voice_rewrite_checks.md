# Scale 44 Voice Repair Checks

## Scope

- Source: `app/web/static/article-bodies-scale-44.js`
- Articles: 44
- Layout/SEO contract: unchanged
- Reworked surfaces: repeated overview, positive, reversal, relationship, work, limitation, and closing paragraphs

## Results

- Library body characters: 789-885 per article before shared article chrome.
- Public article body gate: minimum 1600 characters passed for every scale-44 route.
- Empty paragraphs: 0.
- Full sentences repeated more than 3 times: 0.
- Previous rejected templates remain absent, including `正位不等於好消息`, `它不只是反過來變壞`, and `比較實際的讀法，是把牌義拆成三個問題`.
- Each rewritten paragraph keeps the card-specific core extracted from its existing positive, reversal, relationship, and work context.

## Verification

- `node --check app/web/static/article-bodies-scale-44.js`: passed
- `pytest tests/test_web.py -q`: 38 passed
- `pytest -q`: 80 passed, 2 warnings (existing deprecation warnings)
- `git diff --check`: passed
