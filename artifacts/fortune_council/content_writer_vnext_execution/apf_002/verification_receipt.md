# APF-002 verification receipt

- base SHA: `8355872298890d243f17556306bc203f066398f1`
- scope: APF-001 `matrix/new` 與 `legacy/rewrite` work item 到 Publisher-compatible、side-effect-free candidate/review boundary。
- dry-run fixtures: `test_campaign_editorial_work_item_resumes_successful_stages_and_keeps_identity` 與 `test_campaign_editorial_work_item_fails_closed_for_blocking_review`；均使用注入的固定 Writer／Reviewer，未呼叫外部服務或 Publisher mutation。
- resume evidence: successful brief、candidate、review artifacts 重跑後不會重送，factory/Writer/Reviewer 各只呼叫一次。
- fail-closed evidence: reviewer `REJECT` 或 finding 會阻止 manifest 與 compatible result。
- validation:
  - `uv run pytest tests/test_agy_gemini_coordinator.py tests/test_agy_editorial_contracts.py tests/test_agy_seo_copy_pipeline.py -q`
  - result: `250 passed in 138.67s`
  - `git diff --check`
  - `.venv/bin/python -m py_compile scripts/agy_gemini_coordinator.py scripts/agy_editorial_contracts.py`
- non-actions: 未 push、未 deploy、未 publish、未啟動 production。
