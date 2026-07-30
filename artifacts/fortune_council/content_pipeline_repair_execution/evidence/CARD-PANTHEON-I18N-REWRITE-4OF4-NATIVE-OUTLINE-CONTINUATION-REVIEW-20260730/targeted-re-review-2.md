# Native Outline Continuation Final Targeted Re-review

- card: `CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REVIEW-20260730`
- chain: `pantheon-i18n-rewrite-4of4-runtime-stability-p0-20260730`
- role: `independent-review`
- review cycle: `3`
- repair generation: `2_of_2_final`
- formal thread: `019fb1c4-9a1b-7831-a8f5-16d38db5992a`
- reviewed candidate: `488c3ca290cc62811100f5b73a6eb530f86c6634`
- direct parent: `5d75d1802e379e022ae5682fd9d6ebe019d804f6`
- verdict: `REVIEW_NO_GO`
- context: `CONTEXT_DEGRADED`（CodeGraph 未在本 worktree 初始化；依 evidence-only
  邊界不建立索引，改採 candidate diff、限域 source、direct tests 與獨立 probes）

## Preflight

- worktree 在 checkout 前為 clean detached HEAD。
- candidate object 存在。
- candidate direct parent 精確等於 required direct parent。
- detach checkout 後 HEAD 精確為 reviewed candidate。

## Finding disposition

### `P0C-REREV-001` — CLOSED

Repair-2 將 plan prompt 內所有 structured fragments 統一改用
sorted-key compact UTF-8 canonical JSON。獨立 probe 驗證：

- later-generation plan pending 第一次與 replay 的完整 prompt bytes、prompt SHA、
  request SHA 與 job ID 相同；
- synthetic Outbox 只留下單一 request file，generation 05 只留下單一
  `plan-operation.json`；
- 沒有 `external-plan.json`，沒有 runtime retry operation；
- continuation state 維持 completed `[4]`、next generation `5`；
- root candidate／review 不變；
- brief、prior plan、findings、rebuild authority 的遞迴 dict insertion order
  反轉後，完整 plan prompt bytes 仍相同。

同一 synthetic payload 的 identity：

- prompt SHA-256:
  `442afc4428610e22335cb5fc0bf5cb5d171841c50e23f3861e8fb41ed6c1b328`
- request SHA-256:
  `dbf7fb559f033bcd755ac9f0740b095b088ec85f1bac58b6781e4bf25da7bf84`
- job ID:
  `dbf7fb559f033bcd755ac9f0740b095b088ec85f`

### `P0C-REREV-002` — OPEN, P1

- file and lines:
  `scripts/agy_multilingual_pipeline.py:620-632`,
  `scripts/agy_multilingual_pipeline.py:645-659`
- concrete failure path:
  `_ascii_is_name_acronym_or_number()` 只要每個 ASCII word 為全大寫、Title Case、
  含數字或多個大寫字母，就將整個 item 視為 name／acronym／number；僅有命中
  小型 `GENERAL_ENGLISH_WORDS` 集合才拒絕。因而明確的一般英文句
  `READERS EVALUATE SOURCES CAREFULLY` 每個 word 都走 `word.isupper()`，
  ja／ko 分支在沒有任何 kana／Han／Hangul 時仍回傳 true。
- observed impact:
  相同全英文內容逐一放入 `native_search_intent`、任一 query、
  `article_angle`、任一 H2、任一 coverage note，ja 與 ko 共 10 個 case
  全部被接受；其他母語欄位不需要參與掩護。這表示 per-item loop 雖已建立，
  item 本身仍非 fail closed。
- violated requirement:
  ja／ko 的每一個 semantic item 必須個別拒絕全英文，同時只為真正的 proper
  noun、ASCII acronym、產品名與 number 保留例外。
- minimal repair direction:
  不要用有限一般詞表加 capitalization shape 將任意多詞 ASCII item 判為
  entity。將 ASCII-only 例外收斂到可明確辨識的 entity／acronym／number
  token 或明確資料契約；一般 intent、query、angle、H2、coverage note 必須
  具有目標語言 authority，且加入不依賴特定英文詞彙的 adversarial cases。

由於這是原 finding 的同一失敗契約，本輪不另創 finding ID。

## Original finding regression

- `P0C-REV-003`: CLOSED，第一 continuation generation 仍以 root
  `review.json` 為 final finding authority。
- `P0C-REV-004`: CLOSED，active／complete identity、terminal hashes、
  complete replay與root transaction recovery probes通過。
- `P0C-REV-005`: CLOSED，consecutive same-article rebuild、cross-article／
  non-consecutive controls與topology rejection probes通過。
- `P0C-REV-006`: CLOSED，attempt contiguity、state generation consistency與
  future generation directory fail-closed probes通過。

## New findings

沒有 Repair-2 新引入且獨立於 `P0C-REREV-002` 的 P0／P1 finding；沒有
P2／P3 finding。

## Fresh verification

Direct multilingual tests：

```text
<existing-venv-python> -m pytest tests/test_agy_multilingual_pipeline.py -q
64 passed in 0.17s
```

Required original Review probes：

```text
<existing-venv-python> -m pytest <review-evidence>/adversarial_review_tests.py <review-evidence>/targeted_re_review_probes.py -q
15 passed in 0.08s
```

Required seven-file suite：

```text
<existing-venv-python> -m pytest tests/test_agy_multilingual_pipeline.py tests/test_agy_gemini_outbox.py tests/test_agy_seo_copy_pipeline.py tests/test_agy_content_publisher.py tests/test_agy_gemini_coordinator.py tests/test_agy_gemini_v4_broker.py tests/test_agy_gemini_reviewer_cutover.py -q
492 passed, 1 warning in 85.32s
```

Warning 為既有
`test_preflight_test_command_selectors_resolve_to_top_level_tests` 的
`DeprecationWarning: invalid escape sequence '\/'`。

Final targeted independent probes：

```text
<existing-venv-python> -m pytest <review-evidence>/targeted_re_review_2_probes.py -q
10 failed, 3 passed in 0.08s
```

三個 positive probes 覆蓋 later-plan完整 external identity、合法日文純漢字
heading與structured fragment canonicalization；十個 failure 全部是上述
`P0C-REREV-002` ja／ko 全英文 item 漏放。

```text
git diff --check 5d75d1802e379e022ae5682fd9d6ebe019d804f6 488c3ca290cc62811100f5b73a6eb530f86c6634
PASS
```

Review evidence working diff 的 `git diff --check` 亦 PASS；candidate changed-file
boundary只有 production script、direct test與 Repair-2 專屬 evidence／handoff。

## Residual risks and stop boundary

- `P0C-REREV-002` 未關閉，故依 P1 blocking 規則判 `REVIEW_NO_GO`。
- deterministic language gate 仍是 heuristic，不取代獨立母語 Reviewer；但本次
  failure 發生在 plan hydration 的 required fail-closed boundary，不能只留給
  Reviewer 補救。
- 本 Review 未修改 production code、direct tests、Implementation／Repair／既有
  Review evidence或既有 probes；只新增本 cycle 的 evidence、handoff與獨立 probe。
- 未呼叫 provider、未讀寫 production `.work`、未建立 production／external
  queue（identity probe只在pytest暫存目錄建立 synthetic queue）、未 push、
  deploy、publish或建立其他 task。
