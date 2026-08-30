---
id: PANTHEON-PUBLISHER-EXACT-RUN-ACTIVATION-ORDERING-RCA-20260829-RESULT
card_id: CARD-PANTHEON-PUBLISHER-EXACT-RUN-ACTIVATION-ORDERING-RCA-20260829
status: RCA_COMPLETE
verdict: CAPACITY_VALIDATOR_OVERREACH
---

# Pantheon publisher exact-run / fresh-run activation ordering RCA RESULT

## 唯一主裁決

唯一主因是 **`CAPACITY_VALIDATOR_OVERREACH`**。

正式 shared publisher contract 把 `publisher-exact-run-id` 定義為可選的 bounded selector：Publisher installer 在未指定時會明確刪除該 stage receipt，shared `publisher_plist_preflight` 也同時支援 `expected_exact_run_id` 與 `require_no_exact_run_id`。aggregate activation 只驗七份 plist 的 manifest cohort 與 model-route topology，不要求 run selector。

但 capacity transition 自 `29f758f6ad74afa412dd8ff3878efdd79074b36f` 起，無條件讀取 `publisher-exact-run-id` 且要求非空，因而把「既有 run 的 bounded publish selector」錯升格為「七服務 activation prerequisite」。在 current `new` flow，fresh run 依正式 scheduler 契約要到 activation 後的 coordinator cycle 才建立；activation 前不存在合法 run ID，因此 current failure 不是 publisher 漏寫，而是 consumer 把後段 authority 提前。

Secondary 是 `CROSS_VERSION_STAGE_SCHEMA_GAP`：`29f758f6` 源自舊的 pre-existing exact-run canary topology，後來被沿用到 fresh-run-after-activation acceptance，卻沒有把 selector optionality 帶入 capacity。這也是同一 activation control-plane seam 在 identity 修復後串行暴露的第二個相關失敗；依專案停線規則，本 RCA 停止 production mutation，不能逐症狀繞過。

## Full DAG 與 authority

| 順序 | edge | owner | reads | writes | exact-run語義 |
|---|---|---|---|---|---|
| 1 | promotion COMMITTED | promotion transaction | source、authorization、Rule24 | actor、manifest、barrier/readiness、receipt | 無 |
| 2 | coordinator `--install` | coordinator installer | manifest、model route | coordinator＋四 lane 共5份 stage plist 與 model-route controls | 無 |
| 3 | publisher `--install` | publisher installer | manifest、可選環境 selector | Publisher stage plist、max-runs、可選 exact receipt | 可缺席；只代表 bounded selection |
| 4 | capacity `--install-recovery-stage` | capacity installer | Rule24、barrier、六stage、old-live cohort/services | PASS 後才寫第7份 Capacity stage plist | 現在被私有 validator 錯誤強制 |
| 5 | coordinator aggregate activation | coordinator activator | 七stage、manifest cohort、model route、old-live snapshot | 七live plists、launchctl topology、readiness/barrier | shared aggregate 不需要 |
| 6 | activated coordinator scheduler cycle | coordinator scheduler | registry、new matrix | 最多一筆 fresh brief＋registry state | run ID 在此才正式分配 |
| 7 | new Writer | lane runner | fresh run/outbox | candidate 與 run state | 已分配 run-scoped |
| 8 | Formal Reviewer | reviewer entrypoint | candidate | APPROVE/REJECT | 已分配 run-scoped |
| 9 | publisher selection/transaction | publisher | approved exact run | release transaction/ledger/repo | 此處才是 required bounded selector |

完整 owner/read/write/optional/required machine matrix 見 `dag-and-history.json` 與 `prerequisite-matrix.json`。

## Prerequisite matrix 裁決

當下 observed edge 除 exact-run 外沒有下一個缺欄：

- Rule24=`PASS`、manifest digest 與 generation exact、barrier exact。
- coordinator＋四 lane 五份 stage plist 與 model-route controls 完整。
- Publisher stage plist 存在，`publisher-max-runs=1`，六份 stage plist 是一個 coherent target tuple。
- old live 七份 plist 是一個 coherent g47 normal cohort；7/7 services stopped，recovery topology 合法。
- 唯一缺失是 `publisher-exact-run-id`；它在 shared publisher contract 中可缺席，但 capacity lines 1049–1064 無條件要求。
- 同一 fixture 只加入一個有歷史 receipt 的合法 existing exact run 後，capacity 從 returncode 1／六份stage 轉為 returncode 0／七份stage。沒有改 manifest、barrier、plist cohort、Rule24 或 service topology。

因此 matrix 不只從錯誤訊息推測；它以單一輸入 counterfactual 證明 exact-run 是目前唯一 unmet prerequisite。

## Semantic owner 與 lifecycle

`publisher-exact-run-id` 不屬於 activation cohort、promotion manifest 或 Capacity。它的正式 owner 是 **Publisher bounded selection of an already allocated run**；publish transaction 消費它，但也不擁有 activation identity。

它可以在 activation 前 absent。合法存在時間是：run 已由 scheduler/registration seam 建立，且 operator 要把 Publisher 收斂到一筆 bounded selection 時。對舊 G8 流程，這筆 run 早已存在，所以 preactivation stage 帶有 selector；對 current fresh `new` 流程，run 尚未存在，Publisher installer 正確省略。

沒有找到可在不動 queue/registry 的前提下產生 current new run ID 的正式 provider=0 preallocation seam：

- `_seed_exact_new_matrix_run` 會 reserve identity、建立 brief 並 activate registry state；provider calls 雖可為0，但 production queue mutation 不是0。
- 普通 `seed_new_matrix_runs` 同樣在 scheduler cycle 建立 brief 與 registry。
- `create_single_source_run_adapter(plan_only=True)` 屬另一個已授權 workset/campaign adapter，不是 current new-lane scheduler 入口，不能借用來造 future run authority。

因此 durable invariant 應是：**activation cohort identity 與 run-scoped selection 分離；exact-run 是 optional post-allocation binding，不是 activation prerequisite。** 不需要新增 preallocation transaction。

## Last-good / first-bad

Contract last-good parent 是 `35cfdd52739f3e2896bf151ed6434a5e6d6ab95e`；其 child `29f758f6` 首次把四個 top-level stage 欄位一起讀取，並無條件要求 `publisher-exact-run-id` 非空。`git blame` 目前 lines 1040–1064 全部落在 `29f758f6`（shared function call 起點除外）。

最後一個已定位成功 production 七服務 cohort 是：

- actor `6477ab815e8aecca7d1e8e1588e6e5eba0fab001`
- generation `g47-6477ab81-activation-only-20260826`
- 七 plist replacement 集中於 `2026-08-26T10:45:12+08:00`
- `2026-08-26T10:45:19+08:00` 才註冊後續 new run，支持 scheduler 在 activation 後建立 run
- 該次能滿足 capacity 的 exact selector 來自更早已存在且 complete 的 historical run `auto-i18n-en-614aa4dc3542ab2c5637`，不是 activation cohort 產生

第一個已定位 fresh-run failure 是 current bde445/g71 receipt：Publisher 正式 install 未得到 future run，因此留下六份 coherent stage、max-runs=1 與 absent selector；capacity 在同一 edge RED。這閉合了「code first-bad mechanism」與「production first located incompatible shape」，也解釋為何中間有成功 activation：舊流程碰巧已有 run，並未證明 unconditional requirement 正確。

## Exact RED / historical GREEN

隔離 harness 精確走：

`coordinator --install → publisher --install → capacity --install-recovery-stage`

結果：

- fresh/no-future-run：前兩步 PASS；Capacity returncode 1，`preactivation stage mismatch`，stage 停在6份，selector absent。
- historical existing-run：同一其餘 fixture，指定有歷史 complete receipt 的 exact run；三步 PASS，stage 為7份。
- double run output byte-identical；兩份 SHA 均為 `ee8a886285ee4321251e7b06fcd474c687c4f5a5ad01f56d0df4f2358dd59aa9`，canonical digest `bfca973b57dc5df53dfcc52560794b0a3cf609d0db2986eba27bc01e036acadb`。
- production manifest、queue、publisher state、transactions、private stage 與七 live plist before==after。
- provider/reviewer/publisher/scheduler/activation calls 全為0。

Harness 只保存 identity/schema/hash 與分類，不保存敏感內容。

## Bounded Repair frontier

唯一最小 frontier 應一次覆蓋完整 stage/activation DAG：

1. Capacity transition 沿用 shared publisher plist optionality：若 selector receipt 存在，驗它與 plist exact match；若缺席，驗 Publisher plist 也沒有 exact selector。兩者皆可進入其餘既有 fail-closed checks。
2. 保留 manifest digest、generation、max-runs=1、barrier、model route、六/七 staged tuple、old-live aggregate、stopped recovery topology 與 mode checks。
3. 補 production-shaped regression：fresh/no-selector 應在完整 coordinator→publisher→capacity→aggregate preflight 路徑 GREEN；stale/missing-one-side/mismatch/empty/malformed selector 仍 RED；historical existing exact path 不退化。
4. scheduler 仍只在 activation 後透過既有正式 cycle 配置 fresh run；Publisher 的 exact binding 在 run 存在後另行驗證。

### why_not_less

只塞 placeholder、白名單 `new` lane、手寫 stage 或先建假 run 都會偽造不存在的 authority，且不能修正 shared optional contract 與 capacity private requirement 的矛盾。

### why_not_more

不需要改 promotion、scheduler allocation、publisher producer、aggregate activator或 manifest schema；它們已分別表達 activation cohort、optional selector 與 post-activation allocation。更大修改會把單一 consumer overreach 擴成新 control plane。

### do_not_absorb

禁止新 registry/FSM/DB/authority ledger、run preallocation transaction、placeholder ID、per-lane/per-installer if/else、手改 stage、capacity-first bypass、queue/ledger migration，以及任何 install/activate/scheduler/provider/reviewer/publisher/live mutation。

## Tests / receipts / mutation accounting

- Focused existing suites：`22 passed, 479 deselected`（capacity preactivation、publisher plist optionality、new scheduler seed、launchd topology）。
- Source/test 修改：0。
- production/live mutation：0。
- install/activate/scheduler/provider/reviewer/publisher：0。
- commit/push/tag/deploy：0。

## 終態

`RCA_COMPLETE`。因這是同一 control-plane seam 的第二次串行暴露，production acceptance 維持停線；不得在本 RCA 內實作或繞過。
