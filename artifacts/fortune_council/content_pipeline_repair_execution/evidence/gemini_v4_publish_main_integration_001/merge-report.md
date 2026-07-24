# Gemini V4 Publish-main Integration｜Merge Report

## Result

- Git strategy：`ort`
- Conflicts：`0`
- Candidate contains locked publish base：`PASS`
- Candidate contains V4 reviewed tip：`PASS`
- V4 direct patch copying／rewriting：`0`

## Publication invariants

Relative to locked publish base, the merge changed none of:

- `app/**`
- article content／registry／metadata／sitemap／feed／prerender
- `scripts/agy_content_publisher.py`
- `scripts/agy_seo_copy_pipeline.py`
- `ops/launchd/**`

The publication base therefore remains byte-for-byte authoritative for all article and
automation paths.

## V4 invariants

- `AGY_GEMINI_V4_BROKER=1` remains the only opt-in switch.
- Flag off remains legacy.
- Flag on failure has no legacy fallback.
- Output-binding Repair and Shadow-002 GO evidence remain in ancestry.
- Default transport was not changed.
