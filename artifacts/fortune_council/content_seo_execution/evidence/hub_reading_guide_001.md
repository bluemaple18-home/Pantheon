# Hub Reading Guide 001

## Change

- Removed the product hub behavior that joined every article title into one paragraph.
- Tarot now uses four short reading-guide paragraphs:
  - article count and route selection;
  - definition and upright/reversed basics;
  - relationship questions;
  - work and life-direction questions.
- Other product hubs also stop dumping every title into prose and use count plus reading-purpose guidance.
- Existing visible hub-link module remains unchanged; no CSS, DOM structure, URL, article body, FAQ, Schema or internal-link rule change.

## Verification

- Tarot guide paragraphs: `4`
- Longest guide paragraph: `61` characters in the runtime sample
- Tarot article count reported by registry: `80`
- Visible category links: `12` on desktop and mobile
- Desktop `1440x900`: HTTP 200, horizontal overflow `false`, console/pageerror/requestfailed/bad response `0`
- Mobile `390x844`: HTTP 200, horizontal overflow `false`, console/pageerror/requestfailed/bad response `0`
- `pytest -q`: `82 passed, 2 warnings`
- `node --check app/web/static/article-meta.js`: passed
- `node --check app/web/static/article.js`: passed
- `git diff --check`: passed
- Prerender shells: `139 / 139` contain `article-voice-20260714-4`
