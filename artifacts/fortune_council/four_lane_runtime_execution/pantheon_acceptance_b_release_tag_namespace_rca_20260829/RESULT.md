# Pantheon Acceptance B：Release Tag Namespace RCA 結果

## 唯一主裁決

`RELEASE_VERSION_AUTHORITY_SPLIT`

這不是 Gen06 內容、Reviewer、provider、promotion 或 recovery 再壞一層。根因是正式 release 版本同時由兩個互不校準的 authority 決定：

- publisher 只把 `pyproject.toml` 的 `0.3.372 + 1` 當下一版，得到 `0.3.373`；
- Git 的全域 `refs/tags/vX.Y.Z` namespace 已被一個非 release 的 runtime promotion checkpoint 先占用 `v0.3.373`。

兩者直到 `git tag` 才相遇；此時 translation apply、版本寫入、prerender、507 項測試與暫時 release commit 都已完成。

## 1. 最後成功的 release／tag

最後閉合 release 契約的是 `v0.3.372`：

- release commit：`47d7b804f4dbda6491f48141535fc869000421aa`
- commit：`chore(content): publish Gemini rewrite release v0.3.372`
- annotated tag object：`ff207a7d807e7c71dd2122ab58531ab8817ebce3`
- tag peeled commit：同一個 `47d7b804...`
- tag message：`Pantheon content release v0.3.372`
- `package.json`／`pyproject.toml`：都為 `0.3.372`
- `CHANGELOG.md` 最新 section：`0.3.372`
- exact release record gate：`PASS`

這個行為的 durable 形狀是「版本檔、CHANGELOG、release commit、annotated tag 同版本且同 commit」，再以 main + tag 同批 atomic push。

## 2. `v0.3.373` 如何先被消耗，以及 publisher 為何重選它

### 先消耗 namespace 的事件

commit `295ae1fc246f99f78335c407e974aa33142ef912` 只新增 gen05 runtime promotion plan／evidence，共 21 個 artifact；沒有修改 `package.json`、`pyproject.toml` 或 `CHANGELOG.md`。

之後在 `2026-08-28T08:54:07+08:00`，publisher 之外的人工 tag 操作建立：

- tag：`v0.3.373`
- tag object：`02996e750989933f5bdea047f64d950f3b3f5d17`
- peeled commit：`295ae1fc...`
- message：`Pantheon v0.3.373: gen05 runtime promotion plan`

這個操作把正式 release 使用的 `vX.Y.Z` namespace 當成 promotion checkpoint namespace；版本檔仍停在 `0.3.372`。後續換手卡甚至已明載「`v0.3.373` 不得移動」，證明它是既存 immutable tag，不是本次 publisher 新建的 tag。

### 本次仍選 `v0.3.373` 的精確機制

`scripts/agy_content_publisher.py` 的形成鏈是：

1. `_current_version` 只讀 `pyproject.toml`；不讀 `package.json`，也不讀 local／remote tags。
2. `_bump_patch_version` 固定做 patch `+ 1`，因此 `0.3.372 → 0.3.373`。
3. `publish_ready_translation_runs` 先 `journal.begin`、套用 approved translation，再 bump、prerender、feed、CHANGELOG、release tests。
4. `_stage_commit_tag_push` 先 `git add`、`git commit`，到 `git tag -a v0.3.373` 才讓 Git 檢查 uniqueness。

因此暫時 commit `042e2e52db6aa08170f075c2c38858ea18c721f2` 已形成，最後才因既有 tag 回傳 `128`。這不是 publisher 選錯候選文章，而是 version allocator 從未把 Git tag namespace 當輸入。

## 3. Durable invariant

### Release version authority

- `package.json` 與 `pyproject.toml` 必須先完全對齊；任一 drift 立即 fail closed。
- `refs/tags/vX.Y.Z` 是全 repo 的 immutable release namespace；promotion／evidence checkpoint 未來不得再使用這個格式。
- 下一 release version 必須由「對齊版本檔 + fresh local／remote SemVer tag set」共同規劃，不能只做版本檔 patch `+ 1`。
- 計畫完成後要 frozen；版本檔、CHANGELOG、commit message、annotated tag、atomic push 必須使用同一個 plan。

### Tag uniqueness

- 既有 `vX.Y.Z` 永不移動、覆寫或刪除來遷就新 release。
- preflight 必須同時讀 local ref 與 remote ref；已占用版本要明確列入 plan 的 `occupied_versions`，不能等 `git tag` 才發現。
- commit 前再驗一次 selected tag 仍未被其他 writer 占用；最後跨程序競態由 atomic push fail closed。

### Preflight／transaction boundary

- exact run ready selection 後、`journal.begin` 前，必須完成 release namespace plan。
- 已知 collision 的判定或跳號配置必須發生在 approved content apply、prerender、release tests、commit 之前。
- preflight 本身只能讀 refs／版本檔；不得寫 public content、queue、ledger、candidate、retry receipt、tag 或 remote。

### Retry idempotency

- namespace preflight 阻擋不屬於 candidate failure，不得消耗 translation retry attempt。
- 同一 bytes／refs 連跑兩次要得到同一 plan／blocker；不得再建立暫時 commit或 failure receipt。
- candidate、review、stage seal、queue state、publisher ledger 保持原 bytes；下一次正式入口只在 namespace authority 改變後才進 mutation。

本次 recovery 本身有正確保護：`FAILED_RECOVERED`、actor 回到 base、candidate preserved、Gen07 不存在、沒有新 tag／push／publish。但 retry attempts 因 collision 發生在 mutation boundary 之後由 `1` 增至 `2`；這是 late detection 的次生代價，不是候選內容失敗。

## 4. Exact RED-capable harness

唯一 regression test：

`tests/test_agy_content_publisher.py::test_translation_release_namespace_is_planned_before_mutation`

fixture 固定為版本檔 `0.3.372`、local／remote `v0.3.373` 都指向 `295ae1fc...`，並提供同一個完整且已 APPROVE 的 Gen06 exact run。測試走 publisher 的正式 dry-run／preflight seam，而不是直接測 private tag helper。

必要斷言：

- 在 `journal.begin` 前辨識 `v0.3.373` 已占用；若 planner 自動配置，固定選 `0.3.374` 且記錄 occupied `0.3.373`；若採 fail-closed，則回明確 collision 且不進 mutation。
- 連跑兩次結果一致，retry receipt 不增加。
- provider、translation apply、prerender、feed、release tests、commit、tag、push calls 全為 `0`。
- production/public、queue、ledger、candidate/review/stage seal bytes before == after。

exact command 與全部機器斷言已鎖在 `exact-red-harness-contract.json`。今日 source 必然 RED：dry-run 沒有 release namespace plan，正式路徑則已由真實事故證明會在完整產生／測試／commit 後才撞 tag。本卡遵守「不得再次執行 publisher」，沒有為了重現而做第二次 production 或 synthetic publisher run。

## Root cause 與 secondary factor

### Root cause

`RELEASE_VERSION_AUTHORITY_SPLIT`：非 release promotion tag 與 content release 共用 `vX.Y.Z` namespace，而 publisher allocator 不讀這個 namespace。

### Secondary factor

- `_stage_commit_tag_push` 把 uniqueness 檢查委託給最後的 `git tag`，使 collision 過晚顯現。
- `_current_version` 甚至只讀 pyproject；package 對齊要等 release record gate 才驗。
- recovery／retry 正確保住 candidate 與 actor，但因 blocker 發生在 `journal.begin` 後，仍增加一次 retry attempt並付出完整 prerender／tests 成本。

既有 `v0.3.373` tag、Gen06 candidate、Reviewer 或 recovery 都不是 root cause。

## Minimum bounded Repair frontier

只改 `scripts/agy_content_publisher.py` 的 shared release planning seam，並在 `tests/test_agy_content_publisher.py` 補上述唯一 exact regression：

1. 新增 read-only release namespace planner：驗 package／pyproject 對齊，讀 fresh local／remote `vX.Y.Z` refs，產生 frozen next-version plan。
2. create／rewrite／translation 三條 publisher 共用這個 planner，呼叫點固定在 ready selection 後、`journal.begin` 前。
3. `_bump_patch_version` 改為寫入 plan 的 exact version，不再自行從 pyproject 盲算。
4. `_stage_commit_tag_push` 在 commit 前重驗 plan 的 selected tag，並保留現有 atomic push／unknown-outcome recovery。
5. 未來 promotion checkpoint 禁用 `vX.Y.Z`；改用既有非 release prefix，不另建 registry。

### why_not_less

- 只把這次改成 `v0.3.374`：只能通過一次，下一個外部 tag 仍會重演。
- 只在 `_stage_commit_tag_push` 前檢查：仍然晚於 content apply、prerender、tests。
- 只檢查 local tag：actor 未抓到 remote tag或競態時仍可能晚撞。

### why_not_more

- 不需要 release database、version service、第二套 registry／FSM 或分散式 reservation。
- 不改 provider、Writer、Reviewer、Gen06 lifecycle、promotion、deployment 或 public URL flow。
- 不重寫 publisher transaction；沿用現有 journal、recovery、annotated tag 與 atomic push。

### do_not_absorb

- 不移動、刪除或 force-update `v0.3.373`。
- 不修改／重產 Gen06 candidate，不建 Gen07，不重叫 provider。
- 不把 retry receipt 當 release version authority。
- 不順便做歷史 tag migration、全 repo release 治理或 CI 大改版。

## 驗收狀態

status: `RCA_COMPLETE_REPAIR_REQUIRED`

RCA 四項證據已閉合；production 仍未發佈。下一步只能開一張 bounded Repair，修 shared early release namespace planning seam，回原 Reviewer 後再續同一 Gen06 publisher acceptance。
