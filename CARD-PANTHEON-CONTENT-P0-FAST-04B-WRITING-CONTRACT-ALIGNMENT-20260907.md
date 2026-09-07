# CONTENT-P0-FAST-04B — Writing Contract Alignment

## Objective

保留既有 schema 修補、topic identity、run、reservation 與四篇選題，只補齊 `docs/pantheon_article_publication_standard.md` §2.1、§6 到 create Writer / Reviewer / machine gate 的契約落差。

## Scope

- `app/core/article_publication_policy_v2.json`
- `docs/pantheon_article_publication_standard.md`（同步 machine policy 版號）
- `scripts/agy_seo_copy_pipeline.py`
- `scripts/agy_content_publisher.py`（沿用既有 batch unique seam）
- `tests/test_agy_seo_copy_pipeline.py`
- `tests/test_agy_gemini_coordinator.py`（只更新既有 create fixture，使它符合新 hard gate）
- `tests/test_agy_content_publisher.py`（更新共用 fixture 並補跨 run RED/GREEN）

## Constraints

- 不重建 Writer、Reviewer、Publisher、topic inventory、reservation 或 runtime。
- 不改四篇 topic、route、article identity。
- 不執行舊 attempt 4，不發布、不 deploy、不做 production mutation。
- 保留工作樹既有變更；只做可獨立回退的加法修補。

## Contract Facts

- Authority：`docs/pantheon_article_publication_standard.md` 與 `app/core/article_publication_policy_v2.json`。
- Public seams：`compact_publication_policy()`、`public_model_brief()`、`_writer_prompt()`、`_reviewer_prompt()`、`quality_findings()`。
- 現況：create brief 已有語氣、禁詞、長度與一般限制，但缺少完整去模板化／文章結構契約；create deterministic gate 也未檢查場景密度、具體動詞與模板開頭。
- 既有 rewrite gate 已有場景與具體動詞檢查，可抽成 create / rewrite 共用 seam，不另建第二套流程。

## Acceptance

- RED test 能證明舊 create brief / prompt / gate 未落實新版寫法。
- 新版 contract 由 machine policy 投影到 public brief，Writer 與 Reviewer 均可見。
- create machine gate 能拒絕模板開頭、場景不足、具體動詞不足、可觀察動作不足與反例不足。
- 多篇候選可拒絕「前兩段只替換 primary keyword」的開場。
- Publisher 收集多個單篇 run 時，會在既有 batch unique seam 執行跨篇寫法檢查。
- 既有 schema 修補與四篇 identity 不變。
- targeted tests、pipeline 全檔、`py_compile`、`git diff --check` 通過。

## Root-cause hypotheses

- H1：`compact_publication_policy()` 沒有投影 human standard 的寫作契約；加入 versioned `writing_contract` 後，public brief 與 prompt 應能辨識新舊 request。
- H2：場景／動詞 gate 只存在 rewrite 路徑；抽成共用 helper 並接到 create `quality_findings()` 後，泛化正文應 fail closed。
- H3：四篇既有 topic / target 並未損壞；fresh request 由 current policy 即時產生 public brief，因此只需淘汰舊 attempt 4 request，不需重建 topic、run 或 reservation。
- H4：四線各自產生單篇 candidate，但 Publisher 已有 `_assert_batch_unique()`；在此既有 seam 接入跨篇 finding，即可 fail closed，不需建立新 batch runtime。

## RED evidence

- Command：`.venv/bin/python -m pytest -q tests/test_agy_seo_copy_pipeline.py::test_create_writing_contract_is_projected_and_generic_copy_fails_closed`
- Result：FAIL，`KeyError: 'writingContract'`；確認 create public brief 未包含新版寫作契約。
- Command：`.venv/bin/python -m pytest -q tests/test_agy_content_publisher.py::test_assert_batch_unique_blocks_keyword_swap_openings`
- Result：FAIL，`DID NOT RAISE PublishBlocked`；確認舊 Publisher batch seam 未執行新版跨篇寫法檢查。

## GREEN evidence

- 新契約／projection／舊 brief identity reuse：`4 passed`。
- SEO copy pipeline 全檔：`170 passed`。
- create repair／pending terminalization：`26 passed`。
- Coordinator 受影響 Publisher dry-run：`8 passed`。
- Publisher batch／collect／retry targeted：`5 passed` 與 `16 passed`。
- Publisher 全檔：`167 passed`（既有 `SyntaxWarning` 1 則，與本卡無關）。
- `py_compile`：PASS。
- `git diff --check`：PASS。

## Scoped self-review

- Correctness：policy v2.1 為單一 authority，public brief、Writer、Reviewer、machine gate 與 Publisher batch seam 均消費同一契約。
- Regression：舊 brief 可沿用原 identity / target，hydration 會採 current policy；既有 single-slot schema repair 與 terminalization 測試保持全綠。
- Maintainability：create / rewrite 共用場景與動詞常數；跨 run 檢查接在既有 `_assert_batch_unique()`，未建立第二套 runtime。
- Security / performance：無新網路、憑證、production write 或外部 side effect；batch 檢查只處理已收集的 bounded candidates。
- Residual P2：第二句是否真正「該篇專屬」與五段語意是否自然，仍由獨立 Reviewer 判定；machine gate 只攔可穩定觀察的訊號，避免用脆弱關鍵字假裝理解語意。

## Formal review

- Claude Code read-only verdict：`GO`。
- P0 / P1：`[]`。
- P2-1：Writer / Reviewer 門檻硬寫；已抽成 `_create_writing_instruction()`，由 `writingContract` 動態產生。
- P2-2：human authority 版號仍為 v2.0.0；已同步為 v2.1.0。
- P2-3：Publisher 共用 fixture 預設會跨 article 產生相同開頭；已讓 fixture 依 `article_id` 產生差異，碰撞測試改成顯式製造前兩段只換 keyword。
- P2 修補後重跑：pipeline `170 passed`、Publisher `167 passed`、`py_compile` PASS、`git diff --check` PASS。
- Claude Code final-delta re-review（綁定 pipeline SHA `af7bd0bc…`）：`FINAL_GO`；P0 / P1：`[]`。Reviewer 只執行兩個唯讀檢查，未修改檔案。

## Final evidence SHA-256

- `app/core/article_publication_policy_v2.json`：`a41fea031b225be772e876afd7b4c6bf562fdeb85ce49fa46d8d04207f78b3b2`
- `docs/pantheon_article_publication_standard.md`：`2e06c0b2add3ec4f795a2184a49cfe9c82614a7c0f7c5f10d845cab6da05ac8b`
- `scripts/agy_seo_copy_pipeline.py`：`af7bd0bcd4e5781d0c326f619de0b95a54859fbf1639a89a5e2eb33e5c3bb93d`
- `scripts/agy_content_publisher.py`：`0e8347bf1b780b95f9d2b7249abfeca782900bc0f729446638a55182d17bbddd`
- `tests/test_agy_seo_copy_pipeline.py`：`3f292de8eed5ee17e9243630e484b51e1e3fe73374b5b510ce43c800b5fb4408`
- `tests/test_agy_gemini_coordinator.py`：`450a441dca9d630d159f54a38c327314840c2443e232637031b8382274aa30d2`
- `tests/test_agy_content_publisher.py`：`87845610ce11673ac7878d92b6e9e804f9c77ed58694496d406761058921d866`

## Clean integration evidence

- 基線：`origin/main@8d85427bab45c149dc5b762a2de478f8c77901d1`。
- 只搬入 FAST-04B reviewed hunks；保留既有 publication reference corpus 的 `legacyPaths`／`slug`／`urlSlug`，並排除同一髒工作樹內未屬本卡的翻譯 schema fixture 與 Publisher lifecycle 測試改動。
- 最終整合版：SEO pipeline `170 passed`；Publisher `166 passed`；Coordinator 受影響 editorial／Publisher replay `9 passed`；`py_compile` PASS；`git diff --check` PASS。
- `scripts/agy_seo_copy_pipeline.py`：`99082e1281dda58a606f4281ecb301406700696edbbe79029e971a34675a9c38`
- `tests/test_agy_gemini_coordinator.py`：`e29cdfcbe5e003b9630af822fb410109904f7528360a30b8e074697ca688dd31`
- `tests/test_agy_content_publisher.py`：`cf26525ddd9416809a9b11bd00e01d0c1caa1d63868dc7adac1c58d921005700`

## Rollback

只反向套用本卡新增的 policy、pipeline 與測試 diff；不得回退或覆寫工作樹其他既有變更。

## Status

`LOCAL_GREEN / FORMAL_FINAL_DELTA_GO / COMMIT_PUSH_RUNTIME_PROMOTION_PENDING`
