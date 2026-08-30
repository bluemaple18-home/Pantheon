---
id: PANTHEON-FOUR-LANE-EMPTY-CONTINUATION-AUTHORITY-REPAIR-20260830
status: ready_for_rereview
type: implementation
---

# Empty Continuation Authority Repair 結果

## 唯一裁決

`READY_FOR_REREVIEW`

本 Repair 只修改 `scripts/agy_multilingual_pipeline.py::_approved_stage_terminal_owner` 的 replacement branch。不存在的 `continuation/` 維持合法；canonical、leaf 非 symlink、ordinary directory、可完整列舉且零 entry 的 `continuation/` 現在不構成 continuation authority。其他 shape 與任何 `generations/` 仍 fail closed。

未修改 publisher、promotion、service、registry、queue、seal schema、owner kind、public replacement transaction或 production residue；沒有新增 authority、FSM、ledger、DB、module或共用 classifier。

## Root-cause feedback loop

### RED-before

先只改 test fixture，使 replacement lifecycle 直接建立下列 production shape，沒有先建立 continuation state 再刪除，也沒有使用 `rmtree`：

- `attempts/01..03/{candidate.json,review.json}`
- root `candidate.json`／`review.json` mirrors
- ordinary empty `continuation/`
- `generations/` 不存在

執行：

```text
python -m pytest tests/test_agy_multilingual_pipeline.py::test_replacement_approved_stage_plan_accepts_empty_continuation_residue_read_only -q
```

未修 source 結果：`1 failed`，精確錯誤為 `ValueError: replacement attempt lineage differs`，發生在 `_approved_stage_terminal_owner` 的 `(run_dir / "continuation").exists()` guard。

### Minimal fix / GREEN-after

replacement branch 現以 `os.lstat` 判 leaf type；只有 ordinary directory、canonical path且完整 `iterdir()` 結果為空時可繼續。symlink／non-directory／non-canonical／non-empty 仍回 `replacement attempt lineage differs`；`lstat` 或列舉 filesystem error 轉為 `replacement continuation residue cannot be inspected`。

同一 exact node 修後：`1 passed`。

## Exact plan-only double run

雙跑回傳相同 deterministic plan：

- `plan_digest_first`: `ff797d6fe7fdc742b0f1c930e772db86a87051b6dac1f26170b2a901c5746c72`
- `plan_digest_second`: `ff797d6fe7fdc742b0f1c930e772db86a87051b6dac1f26170b2a901c5746c72`
- `provider_calls`: `0`
- `continuation_exists`: `true`
- `continuation_entries`: `[]`
- `generations_exists`: `false`
- `editorial_staging_exists`: `false`

Protected SHA-256 before／after 完全相同：

| Surface | Before | After |
|---|---|---|
| run tree | `36033c831fc45ae5a71be0ef937bee2b49daccf15f0f5ee7410931992d81245d` | `36033c831fc45ae5a71be0ef937bee2b49daccf15f0f5ee7410931992d81245d` |
| queue state | `a4439cd616e4bd25d1fae225c54893fc0feeb9b68c480251167da16b70f2d248` | `a4439cd616e4bd25d1fae225c54893fc0feeb9b68c480251167da16b70f2d248` |
| publisher ledger | `8a31e575621450e3c1536b28d6ca94b718de3da857e1a5cb46c24e36aad79fd0` | `8a31e575621450e3c1536b28d6ca94b718de3da857e1a5cb46c24e36aad79fd0` |
| locale module | `09d171fd5bc4655d3d02ba9506af299ecb368765297c876d8aa5a50c612900ef` | `09d171fd5bc4655d3d02ba9506af299ecb368765297c876d8aa5a50c612900ef` |
| locale manifest | `be0929b6147abd895514f82476430082898922586644e92a908309e99a33bb76` | `be0929b6147abd895514f82476430082898922586644e92a908309e99a33bb76` |

REWORK 後，test protected snapshot 不再只收 file bytes。每個 run entry 都以 relative path為 key，保存 `type`、`mode`、`size`；file另存 SHA-256，symlink另存 exact target。正向 empty-directory與所有 residue／mixed-owner負向 case均比較完整 files＋directories＋symlink topology，並同時比較 queue、ledger，以及 replacement fixture 的 module／manifest SHA-256。

## Fail-closed matrix

| Shape | Result | Plan-only mutation |
|---|---|---:|
| empty symlink `continuation/` | REJECT | 0 |
| non-directory `continuation` leaf | REJECT | 0 |
| `continuation/state.json` | REJECT | 0 |
| hidden unknown entry | REJECT | 0 |
| nested directory entry | REJECT | 0 |
| enumeration filesystem error | REJECT (`cannot be inspected`) | 0 |
| empty `generations/` | REJECT | 0 |
| attempt04 | REJECT | 0 |
| root review drift | REJECT | 0 |

指定的 genuine continuation regressions亦已形成 exact test nodes：

- `generations/07` 已存在 → `terminal continuation state differs`，topology before==after。
- terminal review `hard_failure=false`，且同步更新 root／generation／continuation digests以抵達 audit seam → `terminal generation audit differs`，topology before==after。
- continuation owner混入 replacement `terminal_attempt` → `fields are mixed`。
- replacement owner混入 continuation `terminal_generation` → `fields are mixed`。

既有 queue／descriptor／mixed-field identity locks與 genuine continuation 的 state SHA、complete status、next generation absence、hard-failure audit仍由完整 multilingual suite覆蓋，沒有修改 continuation branch。

## Verification

- focused exact／negative／continuation nodes：`27 passed in 0.46s`
- complete affected suite：`tests/test_agy_multilingual_pipeline.py` → `303 passed in 1.92s`
- `python -m py_compile scripts/agy_multilingual_pipeline.py tests/test_agy_multilingual_pipeline.py`：PASS
- `git diff --check`：PASS
- `[DBG-` instrumentation：0
- CodeGraph：indexed exact base `4237d7c28274ea3373079f1504c3e22d400f0648`；semantic query定位 `_approved_stage_terminal_owner`／stage plan seam；原始碼確認後只改該 seam。

## Allowlist 與 LOC

Exact base／origin main：`4237d7c28274ea3373079f1504c3e22d400f0648`。

| File | Added | Deleted | Net |
|---|---:|---:|---:|
| `scripts/agy_multilingual_pipeline.py` | 21 | 1 | +20 |
| `tests/test_agy_multilingual_pipeline.py` | 172 | 12 | +160 |

Source net `+20 <= 60`；tests net `+160 <= 160`。交付 changed-file allowlist只有上述 source/test、本卡、本 RESULT與 reviewer-owned獨立 review RESULT；本次 REWORK 未修改 review RESULT。

## Mutation accounting

- provider／Writer／Reviewer／Publisher calls：`0`
- production／queue／registry／ledger／content mutation：`0`
- commit／tag／push／network：`0`
- service load／unload、promotion、activation：`0`
- production residue deletion／rewrite：`0`

本結果只表示兩個 P2 已閉合、同一 bounded candidate 可回原 Reviewer re-review；不表示 commit、push、promotion或 production acceptance 已獲准或完成。
