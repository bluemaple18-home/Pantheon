# REVIEW REQUEST — CONTENT-P0-FAST-04H create prompt ablation

## Review identity

- Repository：`bluemaple18-home/Pantheon`
- Branch：`codex/fast04e-writer-prompt-priority`
- Code baseline：`5418181ba1269a664a9699d928820913b17db843`
- Relevant regression introduction：`64f2c4bf4d`
- Prior routing repair：`c690d4a2add01a030db4ab7e16a97c897e3068b3`
- Review mode：advisory only；本卡不授權修改、provider call、promotion 或 production mutation。

## Root question

在不新增 runtime／repair subsystem、不放寬 schema、不換模型的前提下，是否應只消除 create Writer prompt 中重複的 writing-contract 長文投影，作為下一個 measured-minimum repair？

## Current blocker

`5418181` 已把 create metadata constraints 與 schema diagnostics 移到 prompt 尾端，但 g82 slot-01 的全新 lineage 仍在 Writer schema acceptance 連續三次失敗：title 與 description 都低於既有 `minLength`。依三次同型 blocker 停線規則，沒有第 4 次、沒有 Reviewer、沒有 Publisher、沒有上線。

## Runtime evidence

- Runtime actor：`5418181ba1269a664a9699d928820913b17db843`
- Generation：`g82-5418181b-fast04e-prompt-priority-20260907`
- Run：`content-2eddbf3937-01-7b800e7d-g82-retry-01`
- Correlation：`247a10446c86ed93228be1f17feedaa6`
- Writer：`gemini-3.5-flash-lite`
- Authoritative response schema SHA：與先前成功 control 相同。

| Attempt | Job ID | Prompt SHA | Chars | Result |
|---|---|---|---:|---|
| fresh | `a11151263ae0cc6f05e093d41d5d9b1addba0ce3` | `51af5f936eceaaf7a4f77901c4541c7879b4c38d1c9690092fabe9f252d6482e` | 4,565 | title + description `minLength` |
| repair 1 | `618f946d0ae8a24c9e306d3626b1358078c7c991` | `20805418d6fc3736a67d55d7c1ba735bc29716bd423dd8089ce0b8099347e9df` | 4,798 | same |
| repair 2 | `13ccd2bc6cf4d28063050b31dd07c00b743e5fd2` | `08dc70216533ad5e91381c4c6d8a9156059c8f6dd2acee4fd5131a5cb74ebae1` | 4,798 | same |

三筆 transport 均正常完成，schema repair 使用新 request identity 並帶 closed diagnostics；`c690d4a2ad` 的 routing 已按設計運作。

## Control and falsified hypothesis

同一篇文章、同一 Writer model、同一 response schema 曾在 v2.0 prompt 成功：

- Job：`4a063e18b68f3556f283fd33311408f8cd4f3911`
- Prompt SHA：`5e232d46c1a97d44648346eed4c95f2b9504cbcd5eca8c505236573d2448c514`
- Prompt chars：3,632
- Output：title 23 字、description 78 字，schema-valid。

g82 首次 prompt 比成功 control 多 933 chars（約 25.7%）。因此本輪已否證「只調整 metadata／diagnostics 順序即可關閉回歸」。最強定位仍是 `64f2c4bf` 引入的 v2.1 create instruction load／contract interaction；目前沒有證據支持 transport、登入、模型或 schema 本身是根因。

## Measured duplication

目前 create Writer 同時收到：

1. `public_model_brief()` 內的結構化 `writingPolicy.writingContract`：424 chars。
2. `_create_writing_instruction()` 對同一契約的中文長文重述：252 chars。

`compact_publication_policy()` 本身為 3,281 chars。`_create_writing_instruction()` 也供獨立 Reviewer 使用；Reviewer 尚未成為 blocker。

## Candidate fork — recommended measured minimum

只改 create Writer prompt 的重複投影：

1. 保留 `public_model_brief()` 與結構化 `writingPolicy.writingContract`，不改 policy/schema。
2. 在 `_writer_prompt()` 的 create path 中，不再附加完整 `_create_writing_instruction()` 長文；最多以一句短指令要求逐項遵守 `writingPolicy.writingContract`。
3. `_reviewer_prompt()` 保留 `_create_writing_instruction()`，維持獨立語意 review 的明確 checklist。
4. 所有 deterministic `quality_findings()`、title `20–45`、description `70–95`、schema repair budget 與 Writer/Reviewer ownership 不變。

預期實作範圍只允許：

- `scripts/agy_seo_copy_pipeline.py`
- `tests/test_agy_seo_copy_pipeline.py`

## Required RED/GREEN and acceptance

先新增一個 current-baseline RED，證明 create Writer prompt 同時含 structured contract 與長文重述；最小修補後驗證：

- Writer prompt 只保留一份契約語意來源，且 title／description hard + preferred ranges 仍位於 context 尾端。
- Reviewer prompt 仍保留完整 writing-contract checklist。
- create 的 deterministic writing-contract gates 全部通過。
- optimize／rewrite prompt 位元或既有 assertion 不回歸。
- targeted test、`tests/test_agy_seo_copy_pipeline.py`、`py_compile`、`git diff --check` 全綠。

本機 deterministic fixture 無法證明外部模型一定產出合格長度；真正的 runtime GREEN 仍需新 commit 經 review 後，以全新 run 做一次 bounded canary。現有三次 immutable provider evidence 是本次症狀的 RED，不可重用或做第 4 次。

## Why not less / why not more

- Why not less：`5418181` 已實測證明只移動 metadata／diagnostics 順序不足。
- Why not more：不需要改 schema、移除 deterministic gates、加入本機 padding、換 Writer model、建立 writer-specific runtime／queue／registry，或重寫整個 policy pipeline。
- Do not absorb：OPEN-1／OPEN-2、slot-02～04、promotion、rollback finalize 與其他 backlog。

## Requested independent verdict

請獨立檢查 baseline source 與上述 runtime evidence，回答：

1. 推薦 fork 是否真的是 minimum sufficient？
2. Writer 保留 structured contract、移除長文重述是否比反向做法更安全？
3. 是否缺少會抓到實際回歸的 deterministic test 或 boundary？
4. 是否有任何 P0／P1 finding？

請輸出以下其中一個 verdict：

- `GO_FOR_BOUNDED_IMPLEMENTATION`
- `NEEDS_MORE_EVIDENCE`
- `BLOCK_SCOPE_EXPANSION`

Finding 請標 severity、path/line、evidence、risk、minimum fix 與 validation gap。不要直接修改程式或執行 provider／production。
