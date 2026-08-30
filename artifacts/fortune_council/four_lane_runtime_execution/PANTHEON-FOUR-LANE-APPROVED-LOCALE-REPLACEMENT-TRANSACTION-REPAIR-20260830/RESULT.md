# Pantheon 四線核准語系 replacement transaction Repair 結果

## 裁決

`READY_FOR_FINAL_REREVIEW`

本機候選已在 exact base `e01d56e3847600fa8723a006b3f16e3757af7610` 完成。修補只封閉既有 multilingual stage 與 publisher transaction seam；沒有新增 ledger、FSM、database、overlay、public loader 或第三個 authority owner，也沒有執行 commit、push、provider、network 或 production mutation。

## 最小充分範圍

- why not less：既有 stage 只接受 continuation generation，且 publisher 在 remote mutation 前沒有 durable prepared state；兩端都必須封閉，才能讓 replacement 的 identity、bytes 與 push outcome 可稽核。
- why not more：現有 approved-stage seal、publisher ledger、publish evidence 與 unresolved-push evidence family 已足夠承載交易，不需要建立第二套 registry 或 lifecycle engine。
- do not absorb：不加入 automatic fetch、模糊 job 掃描、跨 run 推測、generic resume、remote network fixture 或新 generation path。

## 實作結果

1. `terminal_owner` 改為封閉 union：`continuation_generation` 保留原契約；`replacement_attempt` 僅接受 exact attempts `01/02/03`、禁止 attempt 04、continuation 與 generations，並鎖定 queue replacement lineage、root/attempt audit bytes。
2. replacement stage 必須攜帶封閉 `public_replacement` descriptor；以 expected old/module/source SHA 驗證唯一 locale record owner、固定 module grammar 與 manifest，receipt-first 後只原位替換指定 record。其他 records、順序、locale 與 manifest bytes 保持不變；current-after 重跑為 idempotent。
3. publisher 將 stage locks、replacement lineage、old/new record/module digests 與 publication plan digest 綁進既有 ledger/evidence。
4. 只在 `push=True` 時，local commit/tag 後、任何 remote mutation 前寫入並 fsync `PUSH_PREPARED`；push ambiguity 僅存在 PREPARED 之後。
5. PREPARED resume 僅接受 exact selected run 與 exact local/remote edge：兩邊缺、只缺 tag、只缺 main、兩邊已達 target；第三 SHA、tag drift 或任何 digest drift 均 fail closed。完成順序為 ledger → evidence → 移除 control，重跑不重複 ledger。
6. `after local commit/tag before PREPARED` 是 local-only window。本修補沿用既有 preflight fail closed，驗證 fetch、ls-remote、push 均為 0；未新增 automatic fetch/reconstruction。這是卡片「reconstruct 或 fail closed」的 minimum-sufficient 選擇。
7. 正式 `stage-approved-edited-candidate` CLI 只從 operator 指定的 JSON 檔載入 exact `public_replacement`，共用既有 closed validator；CLI 不重建、搜尋或猜測 owner。
8. 若 crash 發生於 atomic ledger write 後、evidence write 前，matching PREPARED 只在 exact queue/stage/current-after、ledger entry、local tag object、peeled commit 與 remote refs 全匹配時補 atomic evidence並移除 exact control；不經一般 collector、不改 ledger/content/queue/stage/Git refs，也不 push。ledger/evidence 都存在時回 `ALREADY_PUBLISHED`。
9. remote tag identity 同時鎖定 annotated tag object 與 peeled commit；wrong object 即使 peeled commit 相同也會在 remote mutation 前 fail closed。
10. matching ledger 的 local finalization 在 collector、fetch、`ls-remote`、push 前完成 closed classification；只用 durable PREPARED、唯一 queue/stage seal、current-after、exact ledger、local HEAD/parent/annotated tag/peeled identity與 deterministic `base..target` diff。此分支沒有 remote dependency。
11. normal 與 resume 共用 `_translation_finalization_records`，以 PREPARED `recorded_at` 產生同一 ledger entry 與 canonical evidence bytes。Evidence 由 atomic temp+replace、file/parent fsync、readback byte verification 落盤；control cleanup 後 fsync parent。

## RED → GREEN 證據

- lifecycle RED：舊 API 不接受 `terminal_owner_kind`／replacement attempt authority；GREEN 後 exact attempt lifecycle 可 stage，attempt04、generation 混入、lineage/digest drift 均拒絕。
- existing-locale RED：既有 inventory collision 無正式 in-place replacement seam；GREEN 後 exact record 更新、錯誤 old digest、owner ambiguity、module/manifest drift 與 sibling-byte stability 均有測試。
- publisher RED：舊 commit/tag/push path 不接受 `prepared_context`，remote outcome 無 durable pre-mutation evidence；GREEN 後 PREPARED-before-push 與四種 missing-edge reconciliation 全數覆蓋。
- crash window：push 後、ledger 前可由 exact remote state收斂；remote third SHA fail closed。local commit/tag 後、PREPARED 前只允許 normal preflight fail closed，remote calls=0。
- re-review P1 RED：正式 CLI 原先無 descriptor 入口；ledger 已寫時 collector 會排除 run；remote tag 只比 peeled commit。GREEN 後 subprocess plan/execute、ledger→evidence crash/ledger drift/ALREADY_PUBLISHED，以及 wrong tag object/same peeled commit 均有 exact regression。
- final re-review negatives：CLI missing/unknown-key/wrong run/source/article identity 均 subprocess pre-write fail closed；matching-ledger 分支以 collector/remote `FailIfCalled` 證明 local-only；evidence replace 後、control cleanup 前 crash 的第二跑只 cleanup且 evidence/protected bytes不變；malformed、duplicate unpeeled/peeled、extra tag line 全部零第二次 push 拒絕。

## 驗證收據

- `tests/test_agy_multilingual_pipeline.py`: `290 passed in 1.82s`
- `tests/test_agy_content_publisher.py`: `165 passed, 1 warning in 15.82s`
- `py_compile`: PASS
- `git diff --check`: PASS
- warning 為既有 selector parse 的 `SyntaxWarning: invalid escape sequence '\\/'`，不在本卡 source seam。

## Allowlist 與 LOC

| 檔案 | additions | deletions | net |
|---|---:|---:|---:|
| `scripts/agy_multilingual_pipeline.py` | 248 | 58 | +190 |
| `scripts/agy_content_publisher.py` | 244 | 14 | +230 |
| `tests/test_agy_multilingual_pipeline.py` | 292 | 0 | +292 |
| `tests/test_agy_content_publisher.py` | 318 | 5 | +313 |

Production source 合計 net `+420`，正好位於卡片總上限；各單檔也未超限。新 source helpers：multilingual 3 個、publisher 4 個；未觸及第三個 production source。

## Mutation 與剩餘 gate

- provider calls：0
- network calls：0
- production mutations：0
- commit/tag/push：0
- generation path 變更：0

剩餘工作只有獨立 code review 與其後另行授權的 production acceptance；本 RESULT 不宣稱四線 production activation 或公開發文完成。
