---
card_id: CARD-CONTENT-WRITER-VNEXT-CONTRACT-REVIEW-001
status: CARD_DRAFTED
execution_authorized: true
production_authorized: false
chain_id: PANTHEON-WRITER-VNEXT-CONTRACT
role: code_review
cycle: 1
review_kind: independent_candidate_review
required_source_ref: codex/writer-vnext-contract-review-source-20260810
required_candidate_sha: 592388630545a108f3abe7ffef011586b643f035
required_candidate_parent: e4df0fc4349568cb0a7df2de56a4865885361494
repair_generation: 0
repair_limit: 2
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
ownership: Writer vNext contract 固定候選的獨立驗收
allowlist:
  - artifacts/fortune_council/content_writer_vnext_execution/CARD-CONTENT-WRITER-VNEXT-CONTRACT-REVIEW-001.md
  - artifacts/fortune_council/content_writer_vnext_execution/review/writer_vnext_contract_review_001/**
forbidden_scope:
  - 修改候選 source、既有 tests、spec、implementation card 或既有 evidence
  - orchestration、Gemini role、queue、Publisher、frontend、文章、metadata、registry 或 production 行為
  - merge、push、deploy、publication、canary、network、launchctl 或服務啟動
review_output: artifacts/fortune_council/content_writer_vnext_execution/review/writer_vnext_contract_review_001/
---

# Writer vNext Contract Independent Review

## 五行派工卡

任務 ID｜固定審查 candidate `592388630545a108f3abe7ffef011586b643f035`，不得改候選。

派工對象｜全新獨立 Reviewer；clean worktree；不得由實作者自審。

任務目的｜驗證 Writer vNext contract 真正符合 v0.2.0 規格、無固定 stage／文章形狀、fail-closed 且與既有 side-effect-free candidate validator 相容。

可改範圍｜只新增本卡副本與唯一 review evidence；source、tests、spec 全部唯讀。

驗收證據｜固定 SHA/parent、CodeGraph query 或限域 fallback、獨立 public reproducer、targeted/wider tests、allowlist、`git diff --check` 與唯一 verdict。

## 固定前提

1. `HEAD == 592388630545a108f3abe7ffef011586b643f035`，`HEAD^ == e4df0fc4349568cb0a7df2de56a4865885361494`；不符即 `BLOCKED / SOURCE_MISMATCH`。
2. 新 Runtime Authority Activation 已取得獨立 `REVIEW_GO`；這只解除 contract review 的 parked 條件，不授權 merge、production 或 Publisher 接線。
3. 本 review 不採信實作者的 `5 passed` 或 handoff 自述；必須從 public API 建立獨立 fixtures/reproducer。
4. finding 依 P0/P1/P2/P3 分級；任何 P0/P1 或 production control-plane 邊界破壞均 `REVIEW_NO_GO`。

## 必做獨立 public reproducer

在 review output 內建立 review-only reproducer，至少覆蓋：

- core-only：`selected_stages=[]` 可通過，缺未選 stage artifact 不得報錯。
- stage order：不同 sequence 與組合可通過；不得暗藏 Research→Outline→Blind Reader→Fact Checker 固定順序。
- content plan：未選時可完全缺；選用時 0、3、7 sections 可通過；每節只強制 `purpose` 與 boolean `supports_thesis`；FAQ、固定字數、固定節數不存在於契約 gate。
- claims：只允許五種 claim type；`verifiable_fact` 或 high-risk 缺 evidence 阻擋；其餘分類可無 citation；不得以假 citation 自動補值。
- blind read：綁定 candidate/blind-input SHA；選用且 `thesis_match=false` 阻擋；confusing/low-information/questions 僅留 evidence，不得單獨阻擋。
- identity/hash/schema：missing core、unsupported version、artifact SHA mismatch、article identity mismatch、selected artifact missing 均 fail closed；finding code 與 summary 穩定、排序確定。
- stage declaration：stage type 與 blocking policy 僅接受封閉 versioned enum；拒絕自由程式／條件、retry、publication 動作；duplicate stage ID、sequence ambiguity、artifact mapping collision 必須 fail closed 或列為阻擋 finding。
- legacy compatibility：實際呼叫現行 `scripts.agy_seo_copy_pipeline.validate_candidate` 的 side-effect-free boundary；確認 candidate identity/hash 未被 vNext artifacts 改寫，且不會觸發 queue、Publisher、Git 或 filesystem mutation。

## Source inspection

- 檢查 `scripts/agy_editorial_contracts.py` 沒有外部 client、queue、prompt、retry loop、publication、Git mutation或 runtime orchestration。
- 檢查候選 changed files只在 implementation allowlist，沒有修改既有 Publisher/transport/frontend。
- 將所有 finding 對應到具體 public input、預期/實際結果與 source location。

## 驗證

```bash
git rev-parse HEAD
git rev-parse HEAD^
git diff --check e4df0fc4349568cb0a7df2de56a4865885361494..592388630545a108f3abe7ffef011586b643f035
PYTHONDONTWRITEBYTECODE=1 <repo-root>/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_agy_editorial_contracts.py
PYTHONDONTWRITEBYTECODE=1 <repo-root>/.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_agy_editorial_contracts.py \
  tests/test_agy_seo_copy_pipeline.py \
  tests/test_agy_content_publisher.py
```

若 repo 內測試檔名不同，可用 CodeGraph／限域 `rg --files tests` 找最小等價 suite，並在 receipt 記錄替代原因。

## Verdict 與交付

- `REVIEW_GO`：無 P0/P1；列 residual，明確 contract 尚未 orchestration、接線、merge 或 production。
- `REVIEW_NO_GO`：任一 P0/P1；提供最短 reproducer 與 bounded Repair-1 建議，不自行修。
- 寫入 `review_report.md`、`verification_receipt.md`、`findings.json` 與必要 reproducer/output。
- 建立只含 allowlist 新檔的 review-only commit，交付 SHA 與 clean status。
- 禁止 merge、push、deploy、production、publication、canary 或服務啟動。
