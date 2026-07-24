# Repair-2 Verification

執行環境使用 `/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest`。

| Command / check | Exit | Result |
| --- | ---: | --- |
| 起始 `git rev-parse HEAD`、`git status --porcelain=v1` | 0 | HEAD=`6ea7a7ffdfd2280555af0400baa4dc0167babdce`；clean |
| PPD-R-001 新 regression（修前） | 1 | RED：舊 checkpoint 未阻擋 concurrent bytes 被當成 expected post-image |
| PPD-R-001 兩個 concurrent recovery regressions（修後） | 0 | 2 passed |
| PPD-R-002 durable unresolved push regression（修前） | 1 | RED：`_stage_commit_tag_push` 無 state-root control context |
| PPD-R-002 durable record + atomic push matrix（修後） | 0 | 4 passed |
| PPD-R-003 三 queue E2E（修前） | 1 | RED：retry 被誤寫至已 published 的第一個 run |
| PPD-R-003 三 queue E2E（修後） | 0 | 1 passed |
| `python -m pytest tests/test_agy_content_publisher.py -q` | 0 | 35 passed |
| `python -m pytest tests/test_agy_seo_copy_pipeline.py tests/test_agy_multilingual_pipeline.py tests/test_web.py -q` | 0 | 138 passed；2 warnings |
| 第一次 `python -m pytest -q` | 1 | 402 passed、2 個既知 Ziwei failures；確認 `node_modules/iztro` 缺失 |
| `pnpm install --frozen-lockfile` | 0 | 依 lockfile 安裝 `iztro 2.5.8`；manifest/lockfile 無 diff |
| 第二次 `python -m pytest -q` | 0 | 404 passed；1 warning |
| 修訂 reconciliation assertion 後 `python -m pytest tests/test_agy_content_publisher.py -q` | 0 | 35 passed |
| 補入 untouched owned-file baseline regression 後 `python -m pytest tests/test_agy_content_publisher.py -q` | 0 | 35 passed |
| 最終 `python -m pytest -q` | 0 | 404 passed；1 warning |
| `python -m py_compile scripts/agy_content_publisher.py tests/test_agy_content_publisher.py` | 0 | passed |
| `git diff --check` | 0 | passed |
| `[DBG-` marker scan | 0 | 無 debug marker |

## File content SHA-256 before evidence files

- `scripts/agy_content_publisher.py`: `7e13f253c5e02cd39114b76400c09f2a6598021a7fdb6489886693e371c838a6`
- `tests/test_agy_content_publisher.py`: `945e8c06735cc6d6f25ba8b49732a6906fee0329ed89911278696dc80cb737aa`

## Warnings

- Focused web suite：既有 invalid escape sequence 與 Starlette/httpx deprecation warning。
- Full suite：既有 Starlette/httpx deprecation warning。
