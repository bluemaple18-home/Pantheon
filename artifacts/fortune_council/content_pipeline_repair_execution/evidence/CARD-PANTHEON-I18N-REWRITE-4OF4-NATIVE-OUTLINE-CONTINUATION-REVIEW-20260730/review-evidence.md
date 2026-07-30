# Native Outline Continuation Independent Review Evidence

- card: `CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REVIEW-20260730`
- chain: `pantheon-i18n-rewrite-4of4-runtime-stability-p0-20260730`
- role: `independent-review`
- review cycle: `1`
- verdict: `REVIEW_NO_GO`
- reviewed candidate: `f0b70b4bba41a952f9b8bc2c12d3a2bc5c13502e`
- direct parent: `8bb80b888561b1a06afa9550f535f6e865724871`
- formal thread: `019fb1c4-9a1b-7831-a8f5-16d38db5992a`

## Context receipt

- Candidate `HEAD` 與 direct parent 精確符合 Review 卡，開工前 worktree clean。
- Candidate changed files為 production script、兩個指定 tests、Implementation evidence／handoff，共五檔；沒有 hidden generated 或 environment file。
- CodeGraph status／context query 均回報本 worktree 尚未初始化。因本卡只允許新增專屬 Review evidence，未執行會在 evidence path 外建立 `.codegraph` 的 prepare；本次標記 `CONTEXT_DEGRADED`，改以 candidate allowlist 限域 source、diff、tests 與 production caller review。
- `scripts/agy_gemini_outbox.py:646-647` 已把 `translate_existing` production tick 接到 `multilingual.run_writer_reviewer()`；不是未接線 helper。

## Findings

### P0C-REV-001 — P1 — pending article replay 會把同一 rebuild plan 當成 prior plan

- file: `scripts/agy_multilingual_pipeline.py:1414`
- concrete failure path:
  1. deferred lineage 的連續 finding 令 generation 04 `rebuild_outline=true`；
  2. plan phase 成功寫入 `generations/04/locale-plan.json`；
  3. article phase 回傳 pending；
  4. 同 logical continuation 重跑時，`_last_locale_plan(roots)` 讀到尚未完成的 generation 04 plan；
  5. replay 同一 external plan 時，validator 將它與自己比較，拋出 `locale plan rebuild reused prior outline topology`，不再回到 article pending request。
- violated requirement: R-002 pending article replay 必須 bounded／idempotent 且 request identity 不漂移；R-004 deferred continuation 重跑必須安全收斂。
- minimal repair direction: prior plan 只能來自 `state["next_generation"]` 之前已完成的 generation，或把原始 prior-plan identity/hash 鎖進 continuation state；replay 當前 generation 時不得把該 generation 自己當 prior。
- adversarial evidence: `test_pending_rebuild_article_replay_keeps_identity_and_roots`。

### P0C-REV-002 — P1 — locale plan hydration 接受非目標語言 plan

- file: `scripts/agy_multilingual_pipeline.py:628`
- concrete failure path: `validate_locale_plan()` 只驗證 `native_search_intent`、query、angle、H2 與 coverage note 非空；韓文 locale 可完整接受英文 intent、queries、angle、H2 與 coverage note。article phase 隨後被要求逐字沿用英文 H2，先發生 provider／semantic budget 成本，無法在 plan boundary fail closed。
- violated requirement: R-001 locale plan hydration 必須拒絕 non-native／empty plan；root question 要求先建立 locale-specific plan，再產生母語文章。
- minimal repair direction: 對 plan 的 native semantic fields 加 locale-aware wrong-script／target-language validation；`ja`／`ko` 至少拒絕全英文或殘留繁中主導的 plan，`en` 拒絕 CJK 主導 plan，再補三 locale adversarial fixtures。來源結構 blacklist 不應納入此語言判定。
- adversarial evidence: `test_requirement_rejects_cross_locale_plan`。

### P0C-REV-003 — P1 — 第一個 continuation generation 不以 root review 為 finding authority

- file: `scripts/agy_multilingual_pipeline.py:1411`
- concrete failure path: 只要舊 attempts 有任何 `external-review.json`，`history` 就非空，程式不會加入目前 root `review.json`。root review 由 deterministic gate 合併出的 finding，或 root review 與最後 external review 的合法差異，會從第一個 continuation plan prompt 消失；實測 root marker 未出現在 prompt，反而沿用 attempt 03 的舊 finding。
- violated requirement: R-003 第一個 continuation generation 必須正確沿用既有 root REJECT findings；R-004 starting review identity 必須是 continuation authority。
- minimal repair direction: 將已驗證的 root review 明確設為 continuation history 的最後一代 authority，或先驗證由 attempt artifacts 重建的 final review與 root review完全一致；deterministic findings 必須保留。
- adversarial evidence: `test_requirement_first_continuation_uses_root_review_findings`。

### P0C-REV-004 — P1 — complete state 跳過 starting review／terminal root identity

- file: `scripts/agy_multilingual_pipeline.py:1365`
- concrete failure path: `starting_review_sha256` 只在 `status == "active"` 時與 root review比對。把 continuation 標為 complete 後，以同 run／candidate 的另一份合法 review 取代 root review，replay 不會 fail closed，會直接從 `scripts/agy_multilingual_pipeline.py:1406-1407` 回傳漂移後的 roots；candidate 與 review若一起替換也沒有 terminal hash可檢查。
- violated requirement: R-004 不同 review 不得接管既有 state；complete replay 必須回放同一 terminal lineage。
- minimal repair direction: state 同時鎖定 starting review、terminal candidate 與 terminal review hash；active／complete 都驗證適用的 identity與 generation invariants，任何 root drift直接拒絕。
- adversarial evidence: `test_requirement_complete_state_rejects_review_drift`。

### P0C-REV-005 — P1 — repeated `MIRRORED_STRUCTURE` 不會觸發 topology rebuild

- file: `scripts/agy_multilingual_pipeline.py:43`
- concrete failure path: Reviewer contract把 `MIRRORED_STRUCTURE` 列為 hard reject，但 `REBUILD_FINDING_CODES` 只含 `AI_TEMPLATE_STYLE`、`SOURCE_SYNTAX_TRANSFER`、`NON_NATIVE_SEARCH_INTENT`。同 article、連續 generation 重複 `MIRRORED_STRUCTURE` 時，`rebuild_outline` 仍為 false，可繼續沿用相同 heading／fact topology。
- violated requirement: R-003 repeated finding 必須強制重建真正不同的 outline topology。
- minimal repair direction: 將 `MIRRORED_STRUCTURE` 納入 closed rebuild-code policy，並以同 article consecutive、cross-article、non-consecutive 三組測試鎖定。
- adversarial evidence: `test_requirement_rebuilds_repeated_mirrored_structure`；cross-article／non-consecutive control test通過。

### P0C-REV-006 — P2 — attempt lineage 有缺號時仍以 max 編號續跑

- file: `scripts/agy_multilingual_pipeline.py:1303`
- concrete failure path: attempts只剩 `01`、`03` 時，state以 `max(...) == 3` 建立，接受 `next_generation=4`，沒有拒絕缺少的 `02`。這不會覆寫既有 attempt，但 lineage已跳號且未 fail closed。
- violated requirement: R-004 new generation 必須從 deterministic下一編號開始，不能覆寫或跳號。
- minimal repair direction: 建 state 前驗證 attempt目錄精確為從 `01` 開始的 contiguous sequence，並驗證既有 generation目錄與 state的 completed／next generation一致。
- adversarial evidence: `test_requirement_attempt_number_gap_fails_closed`。

## Fresh verification

### Required suite

卡片指定命令先按原文執行：

```text
.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py tests/test_agy_gemini_outbox.py tests/test_agy_seo_copy_pipeline.py tests/test_agy_content_publisher.py tests/test_agy_gemini_coordinator.py tests/test_agy_gemini_v4_broker.py tests/test_agy_gemini_reviewer_cutover.py -q
```

結果：exit `127`，本 worktree沒有 `.venv/bin/python`。未在 Review worktree建立或安裝 runtime；改用 git common-dir所屬 canonical checkout 的既有 `uv` venv執行相同 selectors：

```text
<canonical-checkout>/.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py tests/test_agy_gemini_outbox.py tests/test_agy_seo_copy_pipeline.py tests/test_agy_content_publisher.py tests/test_agy_gemini_coordinator.py tests/test_agy_gemini_v4_broker.py tests/test_agy_gemini_reviewer_cutover.py -q
```

結果：`460 passed, 1 warning in 85.05s`。warning 是既有
`test_preflight_test_command_selectors_resolve_to_top_level_tests` 的
`DeprecationWarning: invalid escape sequence '\/'`。

### Candidate diff check

```text
git diff --check f0b70b4bba41a952f9b8bc2c12d3a2bc5c13502e^ f0b70b4bba41a952f9b8bc2c12d3a2bc5c13502e
```

結果：PASS，無輸出。

### Adversarial Review probes

```text
<canonical-checkout>/.venv/bin/python -m pytest artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REVIEW-20260730/adversarial_review_tests.py -q
```

結果：`6 failed, 6 passed in 0.11s`。

- 六個 failure 是以 requirement為 expected behavior 的可重現 findings：non-native plan、repeated mirrored topology、root review authority、complete review drift、attempt gap、pending rebuild article replay。
- 六個 pass 證明 cross-article／non-consecutive finding不誤觸發，以及 root transaction在 transaction/candidate/review/state atomic write與 unlink中斷時可保留舊 roots或由 write-ahead transaction安全收斂。

## Acceptance mapping

- R-001: **FAIL** — topic-neutral contracts與 schema／hash／coverage strictness大致成立，但 non-native plan未在 plan boundary拒絕。
- R-002: **FAIL** — plan/article paths與 receipts分離，required suite及 plan-pending測試通過；rebuild generation的 article-pending replay不成立。
- R-003: **FAIL** —同 article consecutive的三個 closed code與 topology比較成立；`MIRRORED_STRUCTURE`漏接，且第一 continuation未使用 root review finding authority。
- R-004: **FAIL** —attempts不被覆寫、root write-ahead interruption probes通過；complete identity與 gap lineage沒有 fail closed。
- R-005: **PASS with residual risk** —fresh runner仍可用、production outbox entrypoint可達、candidate changed files在 allowlist；未觸碰 provider或 production `.work`。

## Residual risks and stop boundary

- 未呼叫 provider、未讀寫 production `.work`、未建立 production queue／approval／apply／publish／ledger／registry／sitemap／feed／redirect。
- 未修改 production code、tests或 Implementation evidence；只新增本卡專屬 Review evidence。
- 未做真實 en／ja／ko 母語人工內容評讀；本 verdict已由可重現 P1 correctness／lineage failures決定，不需以該殘餘風險阻擋。
- 未 push、deploy、publish或建立 replacement／Repair／其他 task。

## Verdict

`REVIEW_NO_GO`

五筆 P1 finding阻擋本 candidate；P0C-REV-006 為非阻擋 P2，但必須保留於後續 repair驗證。
