# Initial 31 Voice Rewrite Checks

## Scope

- Source: `app/web/static/article-bodies-initial-31.js`
- Integrated through: `app/web/static/article-meta.js`
- Routes: 31 initial public article routes, serials `personality-0001..0008`, `tarot-0001..0008`, `fortune-0001..0006`, `astrology-0001..0004`, plus the first article in love, career, interpersonal, wealth and life-direction.
- Layout/SEO contract: unchanged. No CSS, DOM, route, slug, H1, meta, FAQ, Schema or internal-link rule changes.

## Content checks

- Library entries: 31
- Route coverage: 31 / 31
- Minimum custom core text: 330 characters
- Minimum rendered article body: 1,644 characters
- Minimum rendered body sections: 8
- FAQ range: 5 on the sampled initial routes, within the existing 3-5 contract
- Related article links: 5 on the sampled initial routes, within the existing 1-5 contract
- Empty paragraphs: 0
- Full sentences repeated more than 3 times in this batch: 0
- Legacy template phrases (`通常不是想背牌義`, `不能替任何人下結論`, `正位不等於好消息`): absent
- Forbidden generic/guarantee phrases from the public article gate: absent in rendered public article text

## Engineering verification

- `node --check app/web/static/article-bodies-initial-31.js`: passed
- `node --check app/web/static/article-meta.js`: passed
- `node --check app/web/static/article.js`: passed
- `python -m py_compile main.py scripts/prerender_article_shells.py scripts/competitor_seo_tool.py`: passed
- `pytest -q`: `81 passed, 1 warning`
- `git diff --check`: passed
- Prerender shells: `139 / 139` contain `article-voice-20260714-3`
- Content refresh set: `125 / 125` public article routes now expose `2026-07-14`; hubs retain the base `2026-07-12` date.

## Browser acceptance

- Target: `/articles/personality/personality-0001`
- Desktop `1440x900`: HTTP 200, custom opening present, 8 body sections, visible update `2026-07-14`, horizontal overflow `false`.
- Mobile `390x844`: HTTP 200, custom opening present, 8 body sections, visible update `2026-07-14`, horizontal overflow `false`.
- Both viewports: console errors/warnings `0`, page errors `0`, failed requests `0`, 4xx/5xx responses `0`, favicon and initial body asset requests `200`.
- The diagnostic found only the existing `.ui-brand-mark` span with internal scroll width greater than its client width; document-level horizontal overflow remained false and no layout change was made.

## Notes

The shared article chrome still appends search intent, scenario, related reading, reader decision and next-step sections. The rewrite changes only the initial article-specific body voice and leaves the existing publication, SEO and layout contracts in place.
