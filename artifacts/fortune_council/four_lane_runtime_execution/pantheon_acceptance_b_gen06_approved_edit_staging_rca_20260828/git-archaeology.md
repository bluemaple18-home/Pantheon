# Git archaeology

## HEAD 與 CodeGraph

- 分析 HEAD／production actor：`831c536043d85a6cafe813c08a4f06921f0dd0e2`。
- CodeGraph 可用，先查 staging、publisher、promotion 與 translation run context；graph 只找到 publisher policy／runtime promotion candidate，未找到 approved-edit staging symbol。之後才限域讀取下列 source 與 history。

## 最後成功／intended comparable

裁決：`NO_PRECEDENT`。repository history 中從未存在「把外部 formal-approved edited candidate 綁到既有 terminal-rejected production translation run，僅形成 publisher-ready staging，且不 apply/publish」的正式入口。

最接近但不等價的 intended comparable 是 commit `c1885823496270cb195308aae2d72c09c5b0712e`（2026-07-24，`fix(content): require native multilingual rewrites`）：

- 同時引入 `review_edited_candidate` 與 `approve_and_apply_translation_run`。
- `review_edited_candidate` 假設編輯稿已直接位於同一 `run_dir/candidate.json`，Reviewer 結果直接覆寫 `run_dir/review.json`。
- 下一個正式動作 `apply` 直接寫 `approval.json` 並修改 repo locale module／registry；沒有 stage、bind、seal、plan-only、expected-current lock 或 rollback receipt。
- 原始卡只證明 native editor → Reviewer → approval → apply 的本機 canary；未定義既有 production terminal run 的 artifact import/staging。

歷史 CLI union（對 `scripts/agy_multilingual_pipeline.py` 全 history 的 subparser additions/deletions 去重）：

```text
prepare
run
review
apply
authorize-next-generation-after-reviewer-reject
```

`git log --all -G 'stage.*approved|approved.*stage|bind.*candidate|candidate.*bind|seal.*candidate|candidate.*seal' -- scripts/agy_multilingual_pipeline.py scripts/agy_content_publisher.py` 無輸出。

## 缺口形成鏈

1. `c188582349...` 同時建立 edit-review 與 direct-apply 兩端，但漏掉可把隔離核准 artifact 匯入 durable production run 的 bind/seal stage。這是最早 design omission。
2. `2b5da2f068ff4661e2bebc02069098a1d0211663`（2026-07-24，`feat(content): queue and publish multilingual articles independently`）建立 publisher：`collect_ready_translation_runs` 只讀 queue state 指向的 run root candidate/review；`publish_ready_translation_runs` 直接呼叫 approval/apply，然後 bump version、prerender/feed、changelog、commit/tag/push boundary。它沒有補中間 stage，且 deferred ledger 是 publisher lifecycle history。
3. `f12f24315d30a8d030cf2e9d99a310c711eeeb0e`（2026-08-28，`fix: authorize one rejected translation retry`）只新增 terminal Reviewer REJECT → next generation 的 plan-only authority transition；明文「不直接產生內容」，沒有接受已編輯且核准 candidate 的 bind operation。
4. Gen06 首次走到「隔離內容修正 + formal re-review APPROVE，但 production root/Gen06 仍 REJECT」的狀態，才讓長期 omission 成為 `BLOCKED_NO_FORMAL_STAGING_SEAM`。這不是某次 commit 移除既有能力，而是新 recovery 路徑首次需要從未實作的 boundary。

上述三個 commit 均為 HEAD ancestor；不是 branch-only 或 stale actor 誤判。
