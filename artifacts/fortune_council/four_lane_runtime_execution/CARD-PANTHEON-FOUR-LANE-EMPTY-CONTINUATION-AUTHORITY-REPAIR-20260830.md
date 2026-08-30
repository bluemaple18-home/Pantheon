# Pantheon 四線：Empty Continuation Authority Repair

## 工作名稱 → 正在做什麼 → 現在狀態

`Empty Continuation Authority Repair` → 修正 replacement stage 對空 `continuation/` residue 的 lifecycle owner 判定，並以 production-shaped fixture 鎖定既有 continuation 與 mixed-owner 防護 → `READY_FOR_REVIEW / IMPLEMENTATION_NOT_STARTED`。

## 唯一裁決

`GO_SINGLE_GUARD_REPAIR`

本卡只修一個已量測缺口：`4237d7c28274ea3373079f1504c3e22d400f0648` 的 `_approved_stage_terminal_owner` 在 `kind=replacement_attempt` 時，將 `(run_dir / "continuation").exists()` 直接視為另一個 lifecycle owner。真實 replacement run 保留一個空、無 authoritative state/artifact 的普通目錄，因此 plan-only 被錯誤擋下。

允許的最小語意是：

- `continuation/` 不存在：維持合法 replacement shape。
- `continuation/` 是 canonical、非 symlink 的普通目錄，且逐項列舉後確實為空：同樣不構成 continuation authority。
- `continuation/` 為 symlink、非目錄、不可完整列舉，或包含任何 entry：replacement branch 必須 fail closed。
- `generations/` 存在仍一律 fail closed；本卡不類推 empty-directory 例外。
- 真正的 `continuation_generation` branch、owner kind 明示、closed fields、digests 與 terminal audit 規則全部不變。

若 discovery 顯示還需要修改 publisher、promotion、service、registry、queue、production residue，或需要新增第二個 authority/FSM/residue classifier，立即回 `BLOCKED_SCOPE_EXPANSION`，不得順手修補。

## 事故證據

唯一證據來源：

- `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-4237-FINAL-ACTIVATION-ACCEPTANCE-20260830/RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-4237-FINAL-ACTIVATION-ACCEPTANCE-20260830/phase-0-exact-stage-red.json`

已閉合事實：

| 項目 | 證據 |
|---|---|
| last-good | g75 replacement lifecycle、manual repaired candidate、Formal Reviewer APPROVE 均成立；production-shaped replacement stage 尚未成功 |
| first-bad | `4237d7c28274ea3373079f1504c3e22d400f0648` 首次加入 replacement stage guard；同 commit 的 fixture 刪掉 `continuation/`，漏掉真實 shape |
| exact shape | `attempts/01..03`、root `candidate.json`/`review.json` mirrors、空 `continuation/`、無 `generations/` |
| exact RED | return code `1`；`ValueError("replacement attempt lineage differs")` |
| durable invariant | lifecycle authority 來自 authoritative state/artifact 與明示 owner kind，不來自空目錄 inode 的存在 |
| mutation seal | run tree、queue state、publisher ledger、module、manifest bytes before==after；provider/Writer/Reviewer/Publisher calls `0` |

## Why not less / why not more / do not absorb

### why_not_less

不能刪 production `continuation/` 或再次在測試中 `rmtree`，因為那只會正規化掉已量測的 production shape，無法修正 guard 的錯誤 authority 判定，也無法防止下次同樣 residue 重現。

### why_not_more

缺口只在 replacement branch 的一個 existence predicate。owner union、approved seal、public replacement transaction、publisher reconciliation、promotion 與 service activation 都沒有本次 RED 證據；重構它們不會提高本卡驗收力。

### do_not_absorb

本卡不得吸收：

- 通用 filesystem residue classifier 或新 helper framework。
- 新 authority、registry、ledger、FSM、DB、canonical writer。
- empty `generations/` 的新相容契約。
- production cleanup、migration、quarantine 或目錄刪除。
- publisher、promotion、manifest、capacity、LaunchAgent、routing 或 queue 修補。
- provider、Writer、Reviewer、Publisher 呼叫與任何 production activation。

## 精確 allowlist 與硬限

### Production source

1. `scripts/agy_multilingual_pipeline.py`

### Tests

1. `tests/test_agy_multilingual_pipeline.py`

### Evidence

1. 本卡。
2. `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-EMPTY-CONTINUATION-AUTHORITY-REPAIR-20260830/RESULT.md` 與必要的純文字／JSON測試 receipt；不得複製 production residue、provider response 或 binary。

### LOC ceiling

- production source net新增 `<= 60` LOC。
- tests net新增 `<= 160` LOC。
- 不得新增 production module。
- 應優先在 `_approved_stage_terminal_owner` 的 replacement branch 局部修正；不得建立可被其他 subsystem 調用的新 authority framework。

任何 changed file 超出 allowlist、LOC 超限或出現第二個 source seam，均為 `BLOCKED_SCOPE_EXPANSION`。

## Functional requirements

### FR-001 — Empty directory is not authority

當 caller 明示 `terminal_owner_kind=replacement_attempt` 時，空 `continuation/` 只有在下列條件全部成立才可忽略：

- leaf 本身不是 symlink。
- leaf 是普通 directory，不是 file、socket 或其他型別。
- 完整列舉結果為零 entries，包含 hidden entry 也不得存在。
- 判定期間任何 filesystem error 都 fail closed。

此例外只代表「沒有 continuation authority」；不得將空目錄寫入 seal、digest 或 lifecycle state，也不得刪除它。

### FR-002 — Mixed owner remains closed

replacement branch 遇到下列任一 shape 必須在 mutation 前拒絕：

- `continuation/` 含 `state.json`，無論內容看似 valid、tampered 或 unreadable。
- `continuation/` 含任何未知 entry、nested directory 或 hidden entry。
- `continuation/` 是 symlink 或 non-directory leaf。
- `generations/` 存在，包括空目錄。
- continuation-specific CLI/descriptor fields 非 `None`。
- attempts 非精確連續 `01/02/03`、出現 attempt04、root mirror或queue replacement lineage drift。

禁止依 state 內容「猜」哪個 owner 應優先；owner kind 仍由 caller 明示。

### FR-003 — Genuine continuation is unchanged

`kind=continuation_generation` 必須保留現行：

- exact `continuation/state.json` SHA 與 `status=complete`。
- `next_generation`、terminal candidate/review SHA、generation tree、next-generation absence。
- terminal `REJECT + hard_failure=true + findings` audit。
- mixed replacement fields fail closed。

本 Repair 不得讓 continuation branch 接受缺 state、空 continuation、attempt lineage 或 replacement fields。

### FR-004 — Plan-only and bytes are immutable

production-shaped exact fixture 的 stage plan-only 在修後必須 GREEN，且：

- 不刪、不改空 `continuation/`。
- run tree、queue state、publisher ledger、generated locale module、locale manifest bytes before==after。
- provider、Writer、Reviewer、Publisher、commit、tag、push、service mutation 全部為 `0`。
- 連跑兩次回同一 deterministic plan/operation identity，protected bytes 仍不變。

## TDD 與 fixture 契約

### RED-001 — Exact production-shaped fixture

先新增一個能在未修 source 上穩定重現的 exact RED。fixture 必須直接建立／保留下列 shape：

```text
<run>/
├── attempts/
│   ├── 01/{candidate.json,review.json}
│   ├── 02/{candidate.json,review.json}
│   └── 03/{candidate.json,review.json}
├── candidate.json          # bytes == attempts/03/candidate.json
├── review.json             # bytes == attempts/03/review.json
└── continuation/           # 存在、ordinary directory、零 entries
```

`generations/` 必須不存在。fixture 不得以 `shutil.rmtree(run_dir / "continuation")` 或任何等價步驟把 residue 正規化掉；也不得先建立 continuation state 再刪除來模擬空目錄。測試須明確斷言 `continuation_exists=true`、`continuation_entries=[]`。

修前預期：exact `replacement attempt lineage differs` RED；修後同一 fixture GREEN。不得藉改 expected error 或跳過 guard 取得 GREEN。

### NEG-001 — Fail-closed matrix

至少覆蓋：

1. empty symlink `continuation/` → RED。
2. non-directory `continuation` leaf → RED。
3. `continuation/state.json` 存在 → RED。
4. unknown/hidden/nested entry → RED。
5. empty `generations/` → RED。
6. attempt04 → RED。
7. root mirror、replacement state或queue lineage drift → 既有 RED 不退化。

每個負向 case 都須證明 plan-only mutation `0`。

### REG-001 — Continuation regressions

至少重跑 genuine continuation stage positive、continuation digest/state drift、next-generation presence、hard-failure audit與mixed-field tests。不得因 replacement empty-residue 相容而放寬 continuation branch。

## Success criteria

### SC-001

Exact production-shaped RED 在未修 source 可重現；修後同 fixture stage plan-only GREEN，且空 `continuation/` 原樣保留。

### SC-002

empty ordinary directory 是唯一新增接受 shape；non-empty、tampered、symlink、non-directory、`generations/` 或 mixed owner 全部 fail closed。

### SC-003

genuine continuation positive/negative regressions維持 GREEN；attempts/root mirrors/queue lineage既有 locks 不變。

### SC-004

protected bytes before==after，連跑兩次 deterministic；provider/Writer/Reviewer/Publisher、commit/tag/push/service mutation皆為 `0`。

### SC-005

changed files、LOC ceiling、`py_compile`、受影響 tests、`git diff --check` 全部 PASS；無 production mutation、無 commit、無 push。

## Ordered implementation slices

### Slice 1 — Production-shaped RED

- 只改 `tests/test_agy_multilingual_pipeline.py`。
- 建立 exact shape；不得刪空 continuation residue。
- 記錄修前 error、protected byte seal與所有 call counters。
- 驗收：RED 是 `replacement attempt lineage differs`，且 mutation `0`。

### Slice 2 — Local predicate Repair

- 只改 `scripts/agy_multilingual_pipeline.py` 的 replacement owner 判定。
- 只接受 canonical ordinary empty `continuation/` directory或absence。
- 不變更 seal schema、CLI、continuation owner或 generations policy。
- 驗收：RED-001 GREEN；NEG-001 全 RED。

### Slice 3 — Regression and evidence

- 重跑 REG-001 與受影響 multilingual suite。
- 跑 `py_compile`、`git diff --check`、changed-file與LOC檢查。
- RESULT 明列 source/test net LOC、tests、negative matrix、protected byte digests及 mutation counters。
- 不 commit、不 push、不進 production。

## 驗證命令邊界

實作者可依 repo現有 `.venv`／`uv` 契約選用精確 test node；至少交付：

- exact production-shaped RED-before/GREEN-after receipt。
- `tests/test_agy_multilingual_pipeline.py` 受影響 test nodes與 continuation regressions。
- `python -m py_compile scripts/agy_multilingual_pipeline.py tests/test_agy_multilingual_pipeline.py` 的等價 repo-approved 命令。
- `git diff --check`。
- `git diff --numstat` 與 exact changed-file allowlist。

不得因 full suite 有既存 unrelated failure 而修改其他檔案；應在 RESULT 分類 baseline，不得吸收。

## Stop conditions

任一條成立立即停止並交 `BLOCKED_SCOPE_EXPANSION`：

- 需要修改第二個 production source file。
- 需要刪除或改寫 production residue。
- 需要將 empty-directory 相容擴張到 `generations/` 或其他 subsystem。
- 需要更改 owner kind、seal schema、public replacement transaction或 publisher。
- 需要 provider、production、promotion、service、commit、tag或push mutation。
- 同一 blocker 連續三次仍失敗。

## 交付格式

RESULT 必須以唯一 verdict 收斂：

- `READY_FOR_INDEPENDENT_CODE_REVIEW`，或
- `BLOCKED_SCOPE_EXPANSION`。

並附：exact RED/GREEN、negative matrix、continuation regression、changed-file allowlist、source/test net LOC、protected bytes before/after、call/mutation accounting、`py_compile`、tests與`git diff --check`。本卡本身目前狀態固定為 `READY_FOR_REVIEW`；Reviewer GO 前不得實作，且本卡階段不得 commit/push。
