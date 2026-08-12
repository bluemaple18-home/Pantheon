---
id: CARD-CONTENT-WRITER-VNEXT-COMPOSITION-PREFLIGHT-001
card_id: CARD-CONTENT-WRITER-VNEXT-COMPOSITION-PREFLIGHT-001
status: ready
type: preflight
chain: PANTHEON-WRITER-VNEXT-ORCHESTRATION
role: implementation
cycle: 1
strictness: standard
model: gpt-5.6-terra
reasoning: medium
source_commit: 6476719ca652216785166f6c278f073b9b3be760
---

# Writer vNext Composition Preflight 001

## 目的

為 `WVO-SLICE-001` 建立可重現、fail-closed 的 composition manifest。鎖定 Writer contract 與 Runtime Authority 兩條 reviewed lineage、最後一代 `REVIEW_GO` evidence、檔案聯集、重疊與衝突，判定後續整合是否已具備唯一且可驗收的輸入。

本卡只做唯讀 Git object 檢查與 evidence 產出，不執行 composition，不完成 `WVO-SLICE-001`。

## 固定輸入

- Orchestration architecture candidate/review：`4cd768e353e6e349d15f57c5366a3275f7eefb8c` / `6476719ca652216785166f6c278f073b9b3be760`
- Writer contract candidate/review：`671fdba9bf1b5655cc9182bbf375cadae3efb0b5` / `038cf4d2979bf2a1a8ceaf4d44964c3fde5816c6`
- Runtime Authority candidate/review：`e6d93fba050eac7c22e1a34bf52d8ac4c707a1b3` / `38774ddf1bccc77a0b40917322bb100d238469d7`
- Review finding：`WVO-REVIEW-001`（P2 non-blocking）

## 可改範圍

只能新增：

- `artifacts/fortune_council/content_writer_vnext_execution/evidence/writer_vnext_composition_preflight_001/**`

## 禁止範圍

- 不得 merge、cherry-pick、rebase、reset、stash、apply patch 或建立 composition commit。
- 不改任何既有文件、程式、測試、設定、card、evidence、registry 或 shared metadata。
- 不 push、deploy、publish、canary，不啟動／重啟服務，不寫 production state。
- 不把 preflight verdict 宣稱為 `WVO-SLICE-001` 完成或 production readiness。

## 執行契約

1. 以 `git cat-file`／`git show` 確認六個固定 SHA 都是可讀 Git objects，且 candidate 與 review evidence identity 一致。
2. 只認下列 final review evidence；同 commit 內較早的 `REVIEW_NO_GO` artifacts 必須列為 obsolete，不能被選為 authority：
   - Writer：`artifacts/fortune_council/content_writer_vnext_execution/review/writer_vnext_contract_review_002/findings.json`
   - Runtime Authority：`artifacts/fortune_council/runtime_authority_activation_execution/review/runtime_authority_activation_review_003/findings.json`
   - Orchestration：`artifacts/fortune_council/content_writer_vnext_execution/review/writer_vnext_orchestration_architecture_review_001/findings.json`
3. 對每條 candidate lineage 找出 declared base、changed-file inventory、source/test/evidence 類別與 commit parent；不得用工作區 dirty state補證據。
4. 計算兩條 candidate lineage 的 exact file union、重疊檔、內容衝突風險、相依測試與預期 integration glue。任何無法唯一判定的 base、evidence generation、file ownership 或 conflict resolution 都 fail closed。
5. 產出 machine-readable composition manifest，明示這只是計畫，不授權執行 Git composition。
6. 提出後續 integration card 的最小 allowlist、禁止範圍、RED/GREEN 驗證與 rollback boundary；不得自行建立或派出該卡。

## 交付

新增並提交單一 evidence-only commit：

- `composition-manifest.json`
- `composition-plan.md`
- `verification-receipt.md`

`composition-manifest.json` 至少含：schema version、所有 candidate/review SHA、final evidence path + verdict、obsolete evidence paths、declared bases、file inventories、overlap、conflict classes、integration glue candidates、required tests、unresolved blockers、authorized action=`PREPARE_ONLY`。

最終 verdict：

- `COMPOSITION_READY`：輸入與 ownership 唯一、無 unresolved blocker；仍需主線另行授權 merge/composition。
- `BLOCKED`：列出 stable blocker code、證據與最小解除條件。

回報 evidence commit SHA、changed files、驗證與 verdict。
