---
id: PANTHEON-PROMOTION-TRANSLATION-LEDGER-SCHEMA-RCA-20260829
status: complete
type: rca_result
verdict: NO-GO
---

# Promotion translation ledger schema RCA 結果

## 結論

**NO-GO。** 在 bounded Repair 與原 Reviewer 回歸驗證完成前，不得再次 promotion／promotion canary。

主裁決：**`cross-version schema contract gap`**。這不是四條 lane 各自壞掉，而是 publisher 的 producer-owned v1 durable record 與後來加入的 promotion preserved-run validator 之間，缺少一個唯一、明示、fail-closed 的 canonicalization seam。

Immediate defect／secondary：**`promotion validator overreach`**。commit `2c1c6a4850c508ffab26108f7fd9181c05ea2269` 把所有被匹配的 ledger collection 都強制送進 `entry.get("article_ids")`；它的 translation fixture 也自行使用 producer 從未寫出的 plural shape。`producer schema bug` 已被證偽。

## 四項停線證據

### 1. 最後成功 promotion 與當時 state

- 最後成功 promotion 是 `dfcb3c77f9404fc9ff0707cb944ad08f50a4abef`：plan=`READY_TO_APPLY`、apply=`POSTCHECK_PASSED`、finalize=`COMMITTED`；post-promotion actor 與 repo 都是 `dfcb`。
- promotion 前後 ledger digest 同為 `0fc223530e1f8af7d0b495e28e4a336471a2349ceabd93074459827cbe93d8f9`，證明 promotion 本身未改 ledger。
- 「當時 `translation_published_runs` 是空的」為假。live ledger 已有 v0.3.369 record `auto-i18n-en-fcaa5bb4adcfef7aa55c`，同樣使用 singular `article_id`。
- 上次成功的真正原因：該 v0.3.369 run 不在 136 個 preserved run IDs，promotion 只驗證 ledger 中與 preserved run 相同的 `run_id`，所以 latent incompatibility 沒被走到。
- v0.3.374 publish 在 11:21:04 寫入 `auto-i18n-ja-1414b75a404721e95e74`，ledger digest 變成 `4fa274...`；該 run 同時存在於 preserved registry，下一次 `55e2` plan 才首次命中 incompatibility。

機器證據：`schema-timeline-receipt.json`。

### 2. Writer、拒絕起點與 schema authority

- Publisher 在 `2b5da2f068ff4661e2bebc02069098a1d0211663`（2026-07-24）首次實作 multilingual publish 時，就固定寫入 singular `article_id`；目前 producer 仍在 `scripts/agy_content_publisher.py:4464-4475` 寫相同 shape。
- 兩筆實際 production translation records（v0.3.369、v0.3.374）都使用 singular `article_id`。new／rewrite records 則穩定使用 plural `article_ids`。
- `92131e35522ea18063f98cf3ecd76d9675a4c299` 首次讓 promotion 讀 publisher ledger，但當 `article_ids` 缺失時仍容許；`2c1c6a4850...` 才引入 `_validated_ledger_article_ids(entry.get("article_ids"))` 並開始穩定拒絕正式 translation shape。
- **Publisher 是 durable ledger schema authority。** Registry producer 是 run identity envelope authority；promotion 是 consumer／validator，只能在讀取邊界 canonicalize，再和 registry／brief 交叉驗證，不能反向重定義 publisher 已持久化的 schema。

### 3. Durable invariant

共同 canonical identity 為：

```text
{mode, lane, sorted unique article_ids[]}
```

但 persisted record 必須保持其 collection-specific 正式 shape：

| Lane | Registry envelope | Publisher durable collection | 正式 persisted identity | Promotion 內部 canonical identity |
|---|---|---|---|---|
| new | `article_ids: [...]` | `published_runs`／`superseded_runs` | `article_ids: [...]` | 同一 list |
| rewrite | `article_ids: [...]` | `rewrite_released_runs` | `article_ids: [...]` | 同一 list |
| i18n-new | `article_ids: [source_id]` | `translation_published_runs` | `article_id: source_id` | `[source_id]` |
| i18n-rewrite | `article_ids: [source_id]` | `translation_published_runs` | `article_id: source_id` | `[source_id]` |

跨版本 compatibility 契約：對 publisher ledger `schema_version: 1`，promotion 必須依 collection descriptor 接受且只接受該 collection 的正式 identity field，在記憶體內轉為共同 canonical identity；不得修改 live bytes。若同一 record 同時有 `article_id` 與 `article_ids`、欄位缺失、值空白、cardinality 不符或 canonical identity 與 brief／registry 不同，必須 fail closed。未來若 persisted shape 真正改版，必須 bump schema 或提供明示 migration；不能在 v1 中靜默 union。

### 4. Exact RED-capable fixture

已實跑：

```text
.venv/bin/python artifacts/fortune_council/four_lane_runtime_execution/pantheon_promotion_translation_ledger_schema_rca_20260829/real_v0374_red_fixture.py
```

結果 exit `1`，精確命中 `publisher ledger identity mismatch`。Fixture 使用 v0.3.374 的 run ID、article ID、locale、commit、version、timestamp 與 staging receipt shape；provider calls=0、publisher execute=0、apply/finalize=0、new transaction=0，ledger SHA 與 queue tree digest 前後完全相同。前兩次 harness 基礎設施錯誤不算 RED；第三次才是合格 RED。

機器證據：`red-fixture-receipt.json`；可重跑 harness：`real_v0374_red_fixture.py`。

## Zoom-out：模組與資料流地圖

```text
agy_multilingual_pipeline / agy_gemini_coordinator
  └─ 建立 registry state.identity_envelope
       共用：mode + lane + article_ids[] + digest
       lane-specific：new / rewrite / i18n-new / i18n-rewrite
                 │
                 ▼
agy_content_publisher（durable ledger schema authority）
  ├─ new       → published_runs.article_ids[]
  ├─ rewrite   → rewrite_released_runs.article_ids[]
  └─ i18n-*    → translation_published_runs.article_id
                 │
                 ▼
pantheon_content_runtime_promotion
  └─ _queue_identity_snapshot
       └─ _publisher_ledger_evidence
            └─ collection descriptor canonicalization（缺失 seam）
                 └─ 與 brief + registry envelope 比對 preserved-run identity
```

四線共用的是 canonical identity 與 preserved-run equality；lane-specific 的只有 durable collection descriptor，不應散落成 `if lane == ...`。目前摩擦點是 promotion 把「共同 canonical form」誤當成「所有 producer persisted form」，導致跨模組 schema 被壓平成單一欄位。

## Compatibility inventory

Live ledger 六種 record collections 已全部盤點：

- promotion 會消費 `published_runs`、`rewrite_released_runs`、`translation_published_runs`、`superseded_runs`。
- promotion 不消費 `quarantined_runs`、`translation_deferred_runs`；兩者只有 run/reason/time，沒有 article identity，不應被這次 Repair 吞入。
- 136 個 preserved IDs 與 live ledger 相交後，3 new + 3 rewrite 都符合 consumer contract；唯一 production blocking mismatch 是 v0.3.374 translation record。
- v0.3.369 translation record shape 相同，但不在 preserved set，因此不是這次 preflight 的第二個 blocker。
- `superseded_runs` live count=0；只找到 reader／test contract，沒有 production append seam。這是 inventory fact，不擴大本次 Repair。

機器證據：`live-compatibility-inventory.json`。

## 唯一 bounded Repair frontier

在 promotion ledger-read boundary 建立一個 **declarative collection descriptor + shared canonicalizer**：descriptor 明示每個 collection 的 mode、lane、lifecycle、正式 identity field 與 cardinality；shared canonicalizer 只依 descriptor 做 exact validation 與 in-memory normalization。禁止逐 lane `if/elif`，禁止對任一 record generic accept `article_id | article_ids`。

必要 tests：

1. real v0.3.374 singular translation record：plan 轉 GREEN、provider0、transaction0、bytes unchanged。
2. v0.3.369 同 shape compatibility。
3. translation `article_id` 與 registry／brief 不同：RED。
4. translation 同時出現 singular + plural、plural-only、missing、empty：全部 fail closed。
5. new／rewrite plural paths 保持 GREEN；duplicates／unsorted／wrong type 保持 RED。

### Anti-expansion reviewer hard gate

- 可改 source：**只限** `scripts/pantheon_content_runtime_promotion.py`，source 新增最多 45 LOC、刪除最多 15 LOC。
- 可改 test：**只限** `tests/test_pantheon_content_runtime_promotion.py`，test 新增最多 140 LOC。
- 總 changed LOC（additions + deletions）最多 200；超過即退件，必須重新證明 why_not_less。
- 必須通過：targeted promotion tests、exact RED→GREEN harness 等價測試、全檔 promotion test、`git diff --check`。
- Diff 若出現 publisher、coordinator、multilingual pipeline、ledger、registry、runtime、plist、migration、DB、FSM 或 live-state mutation，直接退件。

## Why not less / more / do not absorb

**why_not_less**：只改 synthetic test、跳過該 run、移除 identity equality、或手改 live ledger，都沒有修復 producer→consumer contract，且會讓下一筆正式 translation record 再爆。最少充分變更就是 promotion 讀取邊界的一個 exact canonicalization seam 加 fail-closed tests。

**why_not_more**：publisher 自 2026-07-24 起持續寫正式 singular schema，兩筆 production 一致；registry envelope 也正確表達共同 canonical identity。修改 producer、回填所有 ledger、建立 migration 或重新設計四線 schema，沒有 measured gap 支持，且增加不可逆風險。

**do_not_absorb**：不得建立 registry／FSM／DB／authority ledger；不得 live ledger rewrite；不得 generic union schema；不得逐 lane `if/else`；不得把 quarantine／deferred／superseded producer 補建、promotion lifecycle 重構、schema_version 2、publisher cleanup 或歷史資料 migration 吞進本卡。

## 剩餘風險

- RCA 已閉合，但 Repair 尚未實作，故目前仍是 NO-GO。
- `superseded_runs` 只有 test contract、無 live record；若未來要啟用 producer，應另卡證明，不屬本次 measured gap。
- 本 RCA 不宣稱服務恢復、promotion 成功或 public publish 完成。
