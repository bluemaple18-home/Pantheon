# Pantheon four-lane exact replacement plan-only Repair 結果

## 裁決

`RE_REVIEW_REQUESTED`

本 Repair 只在 `scripts/agy_gemini_coordinator.py` 增加正式
`replace-failed-translation-run` exact operator seam。Plan-only 只讀 exact registry、
terminal run、brief 與 current source，輸出 canonical stdout JSON；execute 重做同一
preflight 後，只呼叫既有 `enqueue_translation_replacement()`。沒有修改 multilingual
helper、automatic lane sweep、runner、provider、publisher、registry schema或production。

## CodeGraph 與 source decision

- worktree preflight：`codegraph=ready`、`prepare_required=false`、indexed HEAD
  `9d6915660124e3a5b41a0878b2c80ab4aecbe6aa`。
- semantic query命中 `enqueue_translation_replacement()`、
  `validate_translation_brief()`、`source_sha256()`；原始碼確認正式 parser、exact state
  loader、closed reason classifier都已在 coordinator。
- source decision維持單一 coordinator seam；沒有第二 source檔。

## RED

新增 public `main()`／real argparse fixtures後，修前執行：

```text
7 failed, 387 deselected
```

七個 case都因 argparse不存在 `replace-failed-translation-run` 而穩定 RED；當時沒有
replacement、runner、provider、publisher或production mutation。

第一次獨立 review另以 source trace鎖定 rework RED：已推進／complete replacement仍會
被回報 `replacement_consumed=false`，且source registry只在helper寫入後重驗，可能
rejected但留下replacement。Review同時指出routing／identity-envelope與symlink path未封。
本次把 consumed-existing、lock內registry drift、routing與symlink shape轉成正式負向
fixture；這些case對review前candidate皆不滿足預期，修訂後一併GREEN。

第二次獨立 review以exact reproduction證明：replacement state不存在時，既存run dir的
`attempts/01/plan-operation.json`會繞過pristine檢查，plan仍錯誤PASS。修訂後以無brief／
有matching brief兩種orphan shape，各跑plan與execute RED→GREEN；四個case均structured
reject、全bytes before==after，execute的helper由`FailIfCalled`證明呼叫數為0。

## GREEN 與 invariant

- plan-only：exact registry digest、run ID、canonical／non-symlink run dir、failed closed
  reason、routing／identity-envelope、base brief identity與每個 current source SHA全部匹配
  才輸出 plan；fixture全 bytes before==after。
- execute：只把已驗證 terminal state與closed reason傳給既有 helper；形成固定
  `<source>-replacement-01` brief/state，source terminal bytes不變，沒有 attempts或
  matching outbox，runner/provider/publisher均0。
- execute先完成read-only plan，再進既有run identity lock；鎖內重讀registry、brief、
  source、terminal budget與replacement identity。任何locked plan drift都在helper前拒絕，
  race fixture證明replacement brief/state均不存在。
- idempotency：相同 execute第二跑回 `already_exists`；全 fixture bytes與第一跑後完全
  相同；只有exact fresh active state、run dir僅含brief且無matching queue residue才能
  回此狀態。attempt、outbox、complete與failed existing replacement全部拒絕。
- replacement directory shape不再依賴state存在才檢查：不存在、空目錄或只有exact
  matching `brief.json`才屬允許形狀；state缺失但帶attempt／candidate／review／其他entry
  一律在plan與鎖內execute的helper之前拒絕；matching outbox／processing／inbox／archive／failed
  residue也逐bucket fail closed。
- fail-closed：missing run、registry digest drift、run-dir drift、brief identity drift、
  source SHA drift、nonfailed state、second replacement、existing lineage collision、
  routing drift、source／replacement symlink與concurrent registry drift全部structured reject。
- production-shaped fixture具Gen01／02 Reviewer REJECT與Gen03
  `PLANNING_CONTRACT_FAILURE / terminal_stage=PLANNING`，封住repair 2/2與無Gen04；同時保護
  KO、JA、new、rewrite、i18n-new、i18n-rewrite與publisher bytes。
- automatic cycle預設仍以原本 `allow_existing_replacement=false` 運作；exact seam只在
  idempotent preflight顯式允許既存的同一 replacement identity，decision與second-level
  lineage仍拒絕。

## 驗證 receipt

```text
exact positive/negative/idempotency:
27 passed, 387 deselected

card affected translation replacement slice:
30 passed, 384 deselected

exact selector + closed reason regression:
12 passed, 402 deselected

existing multilingual enqueue helper:
2 passed, 260 deselected

py_compile scripts/agy_gemini_coordinator.py:
PASS

git diff --check:
PASS
```

Changed-file／LOC seal：

```text
120  1  scripts/agy_gemini_coordinator.py
260  0  tests/test_agy_gemini_coordinator.py
```

符合 source exactly 1、test exactly 1，以及 source `<=120/20`、test `<=260/20` ceiling。

## 額外 full-file baseline 分類

額外執行整份 coordinator test file時，先在未涉及本 seam的既有
`test_campaign_translation_runs_new_and_rewrite_through_real_vertical_chain` 失敗：fixture
仍提供 `safety_boundary`，current multilingual coverage validator要求該 provider欄位
缺失，exact error為 `external locale plan coverage fields are strict for article-01`；
stack沒有進入本卡新增函式。

同次額外 run後續停在既有
`install_agy_gemini_coordinator_launchd.sh --install`（pytest CPU 0、超過五分鐘）。執行
時誤啟動第二個相同 full run：原始 PID `89176`、duplicate PID `89199`；只終止
duplicate，原始 run確認卡在 installer child PID `56721` 後以 SIGINT停止。沒有因這些
baseline／execution-hygiene問題修改程式，也沒有觸碰 production service。

## Boundary seal

```text
source_files_changed: 1
test_files_changed: 1
second_source_seam: false
multilingual_helper_diff: 0
automatic_cycle_semantics_changed: false
production_mutation: 0
provider_calls: 0
runner_calls: 0
publisher_calls: 0
promotion_calls: 0
tag_calls: 0
push_calls: 0
commit: 0
```

Residual risk只剩獨立 Reviewer需核對：source/test都接近LOC ceiling，以及額外 full-file
基線本身不是全綠。本卡明示 affected suites均已通過；不得把額外 baseline failure吸收
進本 Repair。
