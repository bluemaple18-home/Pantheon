# Pantheon 四線：Empty Continuation Authority Repair 文件審查

## Findings

未發現阻塞問題。

非阻塞驗證要求：實作後的獨立 code review 必須看到一個「列舉 `continuation/` 時發生 filesystem error」的負向測試，並證明例外直接 fail closed、plan-only mutation 為 `0`。卡片 FR-001 已要求此行為；此項不擴張 source seam 或 acceptance scope。

## Verdict

`GO`

允許依卡片進入 bounded TDD Repair；本裁決不授權 production、provider、promotion、service、commit、tag、push 或 network mutation。

## Spec axis

- 根因已由 production-shaped exact RED 證明：`4237d7c28274ea3373079f1504c3e22d400f0648` 的 replacement branch 將空 `continuation/` 目錄的存在等同另一個 lifecycle owner，回傳 `replacement attempt lineage differs`。
- exact receipt 證明真實 shape 為 `attempts/01..03`、root candidate/review mirrors、`continuation_exists=true`、`continuation_entries=[]`、無 production mutation；protected run tree、queue state、publisher ledger、locale module、manifest digest 前後一致，四類 business calls 為 `0`。
- durable invariant 正確：authority 來自明示 owner kind 與 authoritative state/artifact，不來自一個沒有 entry 的 directory inode。
- 新增接受集合保持封閉：只有 missing `continuation/` 或 canonical、leaf 非 symlink、ordinary directory、可完整列舉且零 entry 的 `continuation/` 不構成 authority。
- symlink、non-directory、任何 hidden/unknown/nested entry、`state.json`、列舉錯誤、任何 `generations/`、mixed fields、attempt04、root/queue lineage drift都必須在 mutation 前拒絕。
- genuine `continuation_generation` 的 state SHA、complete status、generation tree、terminal hard-failure audit、next-generation absence與 mixed-field 防護明文保持不變。

## Standards axis

- 最小 seam 鎖在 `scripts/agy_multilingual_pipeline.py::_approved_stage_terminal_owner` 的 replacement predicate；不新增 authority、classifier、registry、ledger、FSM、DB 或 production module。
- 測試不得 `rmtree` 空 `continuation/`，而要直接建立並保留 production shape；這能抓住 accepted fixture 原本漏測的行為。
- `generations/` 即使為空仍拒絕，沒有將單點相容規則泛化到其他 lifecycle surface。
- allowlist 僅含一個 production source、一個 test file與本卡 evidence；source/test 淨新增上限分別為 `60/160` LOC，足以完成局部 predicate 與矩陣測試，也能阻止 scope expansion。
- plan-only 連跑兩次必須產生同一 operation/plan identity，空目錄與 protected bytes 原樣不變；provider、Writer、Reviewer、Publisher、commit、tag、push、service mutation均為 `0`。
- continuation positive/negative regressions、`py_compile`、受影響 tests、changed-file/LOC、`git diff --check` 均已列為完成條件。

## Why not less / why not more

- `why_not_less` 成立：刪 production residue或在 fixture 中再次 `rmtree` 只會隱藏已量測 shape，不能修正 authority classification。
- `why_not_more` 成立：publisher、promotion、public replacement transaction、service、queue與 registry 沒有本次 RED 證據；納入只會擴張事故面。
- `do_not_absorb` 完整：禁止 cleanup/migration/quarantine、empty `generations/` 相容、通用 filesystem framework、第二個 source seam與任何 production activation。

## 實作後獨立 code review 必查

1. RED-before 必須保留空 ordinary `continuation/`，不得先建立 state 再刪除，也不得使用任何等價 `rmtree` 正規化。
2. GREEN-after 只能新增 empty ordinary directory 這個接受 shape；absence 行為不變。
3. fail-closed matrix須包含 symlink、non-directory、state、hidden/unknown/nested entry、enumeration error、empty `generations/`、attempt04、root/queue/mixed-field drift。
4. 每個負向 case 與雙跑 plan-only 都須證明 protected bytes與所有 call/mutation counters為零。
5. genuine continuation positive、digest/state drift、next-generation presence、hard-failure audit與 mixed fields regression維持 GREEN。
6. changed-file allowlist、LOC ceiling與禁止範圍不得漂移；若需要第二個 production source seam，回 `BLOCKED_SCOPE_EXPANSION`。

## Review mutation accounting

- source/tests/production 修改：`0`
- provider/network/production/service/commit/tag/push：`0`
- 本次唯一新增：此 review RESULT。
