# Green verification

- `uv run pytest tests/test_agy_editorial_contracts.py -q`: 6 passed.
- `uv run python artifacts/fortune_council/content_writer_vnext_execution/review/writer_vnext_contract_review_001/public_reproducer.py`: 27/27 passed, including `boolean_sequence_ambiguity_fails_closed`.
- `uv run pytest tests/test_agy_editorial_contracts.py tests/test_agy_seo_copy_pipeline.py tests/test_agy_content_publisher.py -q -rA`: exit 0; the same suite collects 116 tests after this regression was added.

The repair changes the selected-stage `sequence` guard from subclass acceptance to an exact `int` check. Thus Python `True` and `False` now receive `schema_version_unsupported`, while ordinary integer sequence values retain their uniqueness and ordering behavior.
