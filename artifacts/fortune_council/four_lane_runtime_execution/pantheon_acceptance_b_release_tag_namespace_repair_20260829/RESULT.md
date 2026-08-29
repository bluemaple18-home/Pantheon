# Pantheon Acceptance B：Release Tag Namespace Repair 結果

## 裁決

`RE_REVIEW_REQUESTED`

`RELEASE_VERSION_AUTHORITY_SPLIT` 已在唯一 bounded seam 修補；尚未執行 production publisher、promotion、commit、push 或 tag，必須先交獨立 Reviewer。

## Exact RED → GREEN

- exact test：`tests/test_agy_content_publisher.py::test_translation_release_namespace_is_planned_before_mutation`
- RED：`KeyError: 'release_plan'`；舊 dry-run 在 ready selection 後未形成 release namespace plan。
- GREEN：fixture 的 `package.json`／`pyproject.toml` 皆為 `0.3.372`，local／remote 皆占用 `v0.3.373`，兩次 dry-run 均 frozen 選出 `0.3.374`。
- mutation boundary：`MutationJournal.begin=0`；translation apply、prerender、feed、release tests、commit、tag、push皆為 `0`；protected public／queue／ledger／retry／candidate／review／stage bytes before == after。

## 實作

### Shared read-only namespace planner

- 新增 frozen `ReleaseNamespacePlan`。
- `package.json.version` 與 `pyproject.toml project.version` 必須先完全相同。
- 同時讀 local `refs/tags` 與 fresh remote `refs/tags/v*`；只納入嚴格 `vX.Y.Z`，從版本檔 patch + 1 起選 first-free。
- create／rewrite／translation 三條 ready publisher 共用相同 planner，固定在 ready selection 後、`journal.begin()` 前執行；dry-run公開同一 plan receipt。
- `_bump_patch_version` 只能寫 frozen plan 的 exact selected version，不再自行盲算。

### Commit/tag drift gate

- `_stage_commit_tag_push` 強制要求 `namespace_plan`，不得繞過。
- git add／commit／tag 前重讀兩份版本檔與 local／remote tag snapshot；任一 drift 或 selected tag 被占用立即 fail closed。
- 最後跨程序競態仍由既有 annotated tag + atomic push fail closed/recovery seam負責。

### Promotion namespace prevention

- runtime promotion plan 與 plan-authority digest 明列 `git_tag_policy=DISABLED`。
- promotion public plan不提供 `tag`／`tag_name`／`release_tag`／`control_tag`，不得再把 `vX.Y.Z` 當 promotion checkpoint；未新增 registry/ledger。

## Candidate allowlist

- `scripts/agy_content_publisher.py`
- `scripts/pantheon_content_runtime_promotion.py`
- `tests/test_agy_content_publisher.py`
- `tests/test_pantheon_content_runtime_promotion.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-RELEASE-TAG-NAMESPACE-REPAIR-20260829.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_release_tag_namespace_repair_20260829/*`

其他既存 dirty/untracked artifacts 非本卡所有，未修改。

## 驗證

- exact + drift + promotion focused：`4 passed`
- `tests/test_agy_content_publisher.py`：`149 passed`（1 個既存 SyntaxWarning）
- `tests/test_pantheon_content_runtime_promotion.py`：`58 passed`
- `py_compile`：PASS
- `git diff --check`：PASS
- production immutable snapshot：既有 queue／ledger／candidate／review／stage hashes逐項等於 RCA post-failure baseline；actor仍為 `1e46c464...` 且 clean；Gen07不存在。

## Minimum sufficient

### why_not_less

- 只硬改成 `0.3.374` 無法處理下一個已占用 tag。
- 只在 commit/tag 前查 collision，仍會先付出內容套用、prerender與tests mutation成本。
- 只查 local tags 無法涵蓋actor未抓到的remote immutable namespace。

### why_not_more

- 不需要 version service、database、reservation service、第二套 registry/FSM或歷史 tag migration。
- 不需要改 transaction/recovery、JA lifecycle、provider、Reviewer、queue或deploy。

### do_not_absorb

- 不移動、刪除、覆寫 `v0.3.373`。
- 不修改或重產 Gen06 candidate，不建 Gen07，不重叫 provider。
- 不替 raw operator Git 命令建立新控制面；promotion正式 plan直接宣告 Git tag disabled。
- 不執行任何 production publisher/promotion/tag/push。

## Reviewer root question

候選是否同時證明：ready selection 後且 mutation 前 frozen first-free `0.3.374`、commit前 drift fail closed、三條 publisher共用、promotion tag disabled、production bytes不變，且沒有越界新增 authority？
