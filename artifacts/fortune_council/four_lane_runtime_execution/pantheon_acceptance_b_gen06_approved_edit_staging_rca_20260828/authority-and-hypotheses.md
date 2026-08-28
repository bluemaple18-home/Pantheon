# Authority、durable invariant 與假說裁決

## Authority owner

| 資料／邊界 | Authoritative owner | 現行 artifact／function | 本 RCA 的判定 |
|---|---|---|---|
| translation brief、candidate、review、generation audit、continuation | `scripts/agy_multilingual_pipeline.py` | run dir；`review_edited_candidate`；continuation authority transition | Gen06 rejected candidate/review 與 continuation terminal state必須保留；隔離核准稿目前不是 production authority。 |
| production run registry／lane lifecycle | `scripts/agy_gemini_coordinator.py` | `<production-root>/queue/runs/*.json`、lane inbox/archive/failed；`_write_state` 與 reactivation operations | registry 只指向既有 run root，沒有欄位或 receipt 綁定外部核准稿。 |
| publisher selection、deferred/published lifecycle、release transaction | `scripts/agy_content_publisher.py` | `collect_ready_translation_runs`、`state/ledger.json`、`publish_ready_translation_runs` | publisher 只接受其可驗證的 durable run payload；不能由 staging 任意刪改歷史 ledger。 |
| actor／manifest／private launchd stage promotion | `scripts/pantheon_content_runtime_promotion.py` | `PromotionRequest`、`_queue_identity_snapshot`、plan/apply/finalize | 只推 actor/manifest/readiness 並保留 queue bytes；不是內容 candidate/review stage owner。 |
| formal re-review attestation | RCA 前置 artifacts | repaired candidate、approved review、formal review result | SHA 與 verdict 足以成為 stage input，但尚無 production bind/seal authority。 |

## Durable invariant

單一 invariant：`publisher 只能消費一個由 translation-run authority 以 exact-current SHA locks、formal approval binding 與可回滾 receipt 封存的 staged payload；terminal generation audit、continuation 與 publisher ledger history不得被覆寫或隱式重分類。`

目前 invariant 的前半缺 writer／reader seam：edited candidate 已被 formal Reviewer 核准，但沒有 canonical stage receipt；因此 production run audit 與 publisher handoff 之間斷鏈。

## Promotion／replacement／publisher boundaries

- promotion：只替換 runtime actor/manifest/private stage，queue snapshot是 preservation input，不可用來更換 candidate。
- replacement／next generation：處理新生成 authority；會建立或授權另一 generation，不是已核准編輯稿的 import。
- publisher：消費 clean-approved durable run 並跨 release transaction；不應同時充當外部 artifact importer。
- approved-edit staging：目前缺失；應位於 translation run authority 與 publisher reader 之間，不能偷渡進上述三個 boundary。

## 假說排序與證偽

### A：existing seam 被漏找／可合法組合

結果：`FALSIFIED`。

- CodeGraph、current source、CLI history union 與全 history stage/bind/seal regex 均無正式入口。
- `review` 會呼叫 provider，且假設 candidate 已在 target run dir；不能 import 已完成 formal review。
- `apply` 直接修改 repo locale registry 並寫 approval，不是 staging。
- publisher 會跨 apply/version/prerender/feed/changelog/commit/tag/push-capable boundary。
- campaign replay 只在 campaign temp tree 生成／複製；遇到 existing complete state 會沿用既有 root candidate/review，沒有外部 approved payload import contract。
- runtime promotion 只保存 queue bytes，不改 candidate/review。

### B：intentional boundary 要求直接 apply/publish，沒有中間 staging

結果：`FALSIFIED`。

- 初始 multilingual contract 明確分開 Reviewer、approval 與 publisher；沒有任何 requirement 宣告「核准後必須直接發布」或禁止 staging。
- `review` 與 `apply` 分成兩個 CLI，證明其間本來就是顯式 control boundary；只是舊實作假設兩者共享同一可直接編輯的 run dir。
- production safety 把內容修正與 formal review 放在隔離 runtime 後，這個隱含共址假設失效。缺的是正式 artifact transfer authority，不是 staging expectation 錯誤。

### C：recovery/edit flow 少 bind/seal operation

結果：`SUPPORTED`。

- exact approved candidate、clean review、formal attestation、terminal Gen06 與 complete queue registry同時存在。
- 唯一 red-capable public-interface command 因 staging subcommand 不存在而 RED，所有 bytes 不變。
- next-generation authorizer已解 generation recovery，但不接受 edited approved payload；兩者職責不同。

## 唯一 root verdict

`FORMAL_STAGING_SEAM_MISSING`

層級：translation-run authority → publisher handoff 的 design omission；不是 provider、coordinator、promotion、publisher release、candidate 品質或 production drift 問題。
