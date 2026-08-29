# RESULT：Pantheon Publisher Exact-Run Activation Optionality Repair

- 狀態：`RE_REVIEW_REQUESTED`
- accepted base／HEAD：`bde44589f3785aae738bb7d7b1626270ba5505d0`
- 唯一主因：`CAPACITY_VALIDATOR_OVERREACH`
- scope expansion：`0`
- production／live mutation：`0`

## 裁決

最小 Repair 已恢復 `publisher-exact-run-id` 的 optional-before-run 契約。Capacity 現在只區分兩個既有合法 shape：

1. stage receipt 不存在時，使用 shared Publisher preflight 要求 Publisher plist 同樣沒有 `--exact-run-id`；
2. stage receipt 存在時，拒絕空值，並沿用 shared exact contract 驗證格式及 receipt ↔ plist 完全一致。

其他 manifest digest、generation、barrier、model route、stage/live tuple、old-live cohort、Rule24、stopped topology與normal/recovery mode驗證均未移除或放寬。Capacity 沒有讀取 run、queue、registry，也沒有驗 completion或新增 authority。

## RED → GREEN

- Reviewed production-shaped before receipts：完整 `coordinator --install → publisher --install → capacity --install-recovery-stage` 在 fresh/no-future-run shape 於 `preactivation stage mismatch` RED；兩次 bytes 相同，SHA `ee8a886285ee4321251e7b06fcd474c687c4f5a5ad01f56d0df4f2358dd59aa9`。
- 新增 targeted fixture 修前 RED：`1 failed`，stage receipt 與 Publisher plist同步缺席仍被舊 capacity validator拒絕；receipt SHA `6a9040cf58b623955234cb285bb4b8abb619e389a82ab06053b70f46319da0b5`。
- 同一 targeted fixture修後 GREEN：`1 passed`；receipt SHA `4b6d07f3dd9162cdd77e3e17e4080e549552f0916da64fe26a751d430973d321`。
- Candidate正式順序雙跑：fresh/no-selector與historical valid selector均三步 return code 0，stage均為7 plists／1 cohort tuple；兩份 bytes相同，SHA `04327717f255f2d47846b869ca3b1d7fa5407bfea774c13efc8ecfd0591161fd`，canonical digest `d5235759fa93fe3867b93dd3ee5c8b1267d96026cc2875b7e7a312dfdbda5280`。

## Negative / preserved matrix

- selector：historical valid selector GREEN；receipt缺失但plist存在、plist缺失但receipt存在、mismatch／stale、empty、雙側malformed皆 RED。
- preserved fail-closed：manifest digest、generation、barrier、model route、staged lane digest、six/seven tuple、old-live cohort、loaded/stopped topology、activation-only child I/O、normal/recovery drift由完整 capacity suite覆蓋。
- targeted capacity suite：`68 passed in 34.40s`。

## Broad parity

完全相同 selection／參數／環境：

`tests/test_pantheon_content_capacity_guard.py tests/test_pantheon_content_runtime_manifest.py tests/test_agy_gemini_coordinator.py`

- parent baseline：`493 passed / 8 failed`。
- candidate：`497 passed / 8 failed`；增加4個通過的測試 case，沒有新增 failure。
- 8個 failure node set逐一相同；normalized error lines均16條，digest均為 `834660a4c8ab119e7fff9e45af36ad32548b0c99e0bfd44a890269e7b2d196e2`；`baseline_identical=true`。
- 既有 failures均為不相關的 multilingual external locale plan strictness；未修、未掩蓋。

## Diff / gates

- source allowlist：`scripts/pantheon_content_capacity_guard.py`，`+20/-6`。
- test allowlist：`tests/test_pantheon_content_capacity_guard.py`，`+93/-8`。
- source+test changed LOC：`127`；diff SHA `87029a93697ffcb374c39f349f48e1ce5823df0bce413c8ba454f018459fb847`。
- 第二個 test file：未使用；第三個 source：未使用。
- `py_compile`：PASS。
- `git diff --check`：PASS。
- anti-expansion：沒有 scheduler、publisher installer、coordinator、promotion、manifest schema、FSM、registry、DB、ledger或migration修改；沒有per-lane／per-installer特判。

## Production immutability

Harness只在task-owned temporary roots寫入stage與plist。兩次candidate receipt均證明production manifest、queue、publisher state、transactions、live stage及7個live plists before==after；provider／reviewer／publisher／scheduler／activation calls全部為0。

## Minimum sufficient

- `why_not_less`：只刪除「receipt必須存在」會讓單邊缺失誤通過；必須用既有 shared preflight把雙側缺席綁成同一合法shape。
- `why_not_more`：selector格式、一致性與Publisher plist authority已由shared contract提供；不需要修改producer、scheduler、manifest或其他installer。
- `do_not_absorb`：不preallocate future run、不放placeholder、不讀queue／registry／completion、不新增identity/FSM/DB/ledger/migration、不做capacity-first bypass。

## Evidence

完整索引見 `evidence-index.json`；raw RED/GREEN、targeted、broad baseline/candidate stdout及雙跑JSON均保存在本目錄。
