# CARD-PANTHEON-G7-PREACTIVATION-OLD-LIVE-TO-NEW-STAGE-TRANSITION-REPAIR-20260818

## 工作名稱

修復 G7 preactivation 舊 live → 新 stage 狀態轉換契約

## Root question

如何在不先 activation 的前提下，安全證明「舊 live 七服務可被新 staged 七服務原子取代」，避免 capacity guard 錯把 pre-check 當 post-check？

## 已知 blocker

- G6 production gate：`capacity_guard_preactivation_live_plist_mismatch`。
- 新 runtime manifest／stage：`b8a34451e7a2b10a9e7ce1f11f366250cc67d87b:activation-only`。
- 舊 live 七張 plist：同一組 `g8`／`b74646...:four-lane-model-route-v1` activation-only wrapper、loaded/no PID。
- 現行 validator 要求舊 live identity 符合新式 `*:activation-only` pattern，形成循環依賴：guard PASS 才 activation；activation 後 live identity 才更新。
- G6 evidence：`c61f7592dd0b7a1645a631f399e878a5db55f9db`。

## 需求與成功準則

- `FR-G7-01`：preactivation 必須把舊 live 七張 plist 驗成一個自洽、inert、loaded/no-PID 的 old aggregate；不得要求它等於新 target identity。
- `FR-G7-02`：新 staged 七張 plist、manifest、generation、barrier、Publisher exact markers 必須完整綁定新 target。
- `FR-G7-03`：只有 old aggregate 與 new staged aggregate 各自完整且轉換邊界成立，guard 才可 stage 第七張 capacity plist。
- `FR-G7-04`：aggregate activation 後的 postcheck 才要求 live 七張全部等於新 target identity。
- `SC-G7-01`：G6 真實拓撲 fixture 由 RED 轉 GREEN。
- `SC-G7-02`：任一 old-live 單線漂移、混合 old identity、PID 出現、stage 缺檔、barrier／marker／digest 漂移皆 fail-closed。
- `SC-G7-03`：一般 capacity preflight 不放寬；production mutation 為 0。

## 可改範圍

- `scripts/pantheon_content_capacity_guard.py`
- `scripts/install_pantheon_content_capacity_guard_launchd.sh`（只有必要時）
- `tests/test_pantheon_content_capacity_guard.py`
- 本卡與同卡 `.work` evidence

## 禁止範圍

- production runtime、LaunchAgents、queue、state、transaction、tag、remote push。
- Publisher selector、其他六服務 installer、promotion 模組、一般 preflight 語意。
- 新建第二個 Repair／Reviewer thread。

## 切片與依賴

### `SL-G7-OLD-AGGREGATE-CONTRACT`

- `traces_to`: `FR-G7-01`, `SC-G7-02`
- frontier：是。
- RED：以 G6 真實 old live identity／generation／manifest tuple 重現目前 mismatch；加入混合 identity、單線 coherent drift、PID 出現負向。
- GREEN：只驗 old aggregate 自洽與 inert，不要求等於 new target。

### `SL-G7-NEW-STAGE-CONTRACT`

- `traces_to`: `FR-G7-02`, `SC-G7-02`
- blocking edge：`SL-G7-OLD-AGGREGATE-CONTRACT` 完成後。
- 驗證新 staged 七服務、manifest、barrier、generation、Publisher exact markers 綁定同一 target。

### `SL-G7-TRANSITION-AND-POSTCHECK`

- `traces_to`: `FR-G7-03`, `FR-G7-04`, `SC-G7-01`, `SC-G7-03`
- blocking edge：前兩張 slice 完成後。
- pre-check 與 post-check 分離；不得在 pre-check 預設 activation 已完成。

## Checkpoint

完成前兩張 slice 後，跑 G6 happy／old-live drift／stage drift matrix；全綠才進第三張。

## 驗證

- G6/G7 精準 RED→GREEN matrix。
- 完整 `tests/test_pantheon_content_capacity_guard.py`。
- `tests/test_pantheon_content_runtime_manifest.py tests/test_pantheon_content_runtime_promotion.py`。
- `bash -n scripts/install_pantheon_content_capacity_guard_launchd.sh`。
- `git diff --check`。
- Reviewer 必須獨立重跑 G6 真實拓撲與負向 harness，回 `GO` 才可整合。

## 交付

- Root cause：明確指出 pre-check／post-check 錯位欄位。
- Candidate SHA、變更檔案、RED/GREEN 與完整測試數。
- Production mutation 必須為 `0`。

## Repair receipt

- Root cause：preactivation old-live half still required the new-form `gate2-actor:<sha>:activation-only` identity, incorrectly applying a post-activation live identity requirement before activation.
- Source fix：old live seven plists are now derived as one coherent aggregate tuple and may differ from the new target; new staged aggregate now includes the capacity guard candidate plist before it is written.
- RED：G6 old live `four-lane-model-route-v1` activation-only loaded/no-PID topology failed with `preactivation live plist mismatch`.
- GREEN：G6 happy path, G5 happy path, old-live drift, staged drift, capacity candidate drift, and original negative matrix all pass locally.
- Production mutation：`0`。

## Repair receipt iteration 2

- Reviewer NO-GO：candidate `5fdf66bb51e4d37aa91224264d24b1fa62120e7f` allowed installer stage write when normal preflight returned `PASS`.
- Root cause：`run_capacity_preflight` treated preflight `PASS` as final success before checking whether the staged transition context existed, so PID-bearing old live activation-only wrappers with valid RSS bypassed `preactivation-transition`.
- Source fix：when stage manifest/generation/Publisher markers exist, installer writes the preflight receipt and always runs `preactivation-transition` before any destination write; preflight `PASS` is accepted only as receipt evidence, not as a bypass.
- RED：G6 old activation-only live seven with `pid = 4242`, `state = waiting`, valid RSS failed because installer returned `0` and wrote the staged capacity plist.
- GREEN：the same PID-bearing topology is rejected nonzero, staged destination remains absent, and mutation log remains absent.
- Regression：normal non-transition capacity preflight semantics remain unchanged; real G6 loaded/no-PID transition remains accepted.
- Production mutation：`0`。
