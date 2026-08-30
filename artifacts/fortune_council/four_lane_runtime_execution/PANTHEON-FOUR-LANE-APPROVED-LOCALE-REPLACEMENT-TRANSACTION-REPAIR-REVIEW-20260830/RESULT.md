# Approved Locale Replacement Transaction Repair 同卡 scoped re-review

## Verdict

`GO`

原唯一 blocker「remote push成功至translation ledger/evidence落盤之間沒有durable recovery state」已在同一卡片內閉合。修訂版沒有新增publication authority、第三個production source、第二ledger、FSM或DB；它只把既有 `_unresolved_push_path`／publisher state/evidence family從「push例外後才記錄」前移為remote mutation前的durable `PUSH_PREPARED`，並以closed state table限制首次push、exact missing-edge convergence、finalization-only與already-published。

專家視角：維護過 transactional content publishing 與 append-only audit 系統的 staff engineer。

本次只重審原crash-window finding與scope/authority邊界；前次已通過的lifecycle owner、exact locale owner與public loader判斷不重開。

## 原 finding closure

### 1. PREPARED 已覆蓋原 push→ledger crash window

修訂卡要求：

1. stage receipt與exact replacement after bytes先被seal。
2. MutationJournal包住local content/release mutation。
3. local commit/tag形成後、任何remote mutation前，原子且fsync寫入 `PUSH_PREPARED`。
4. remote main/tag兩者驗為target commit後，才append既有 `translation_published_runs`。
5. ledger後若evidence缺失，只能補同一evidence；兩者齊全回 `ALREADY_PUBLISHED`。

因此原反例「push已成功、ledger尚未寫、沒有recovery identity」不再可達：push前一定已有PREPARED。即使process在atomic push返回後終止，下一次exact execution只能驗target remote refs與sealed after bytes，然後finalize同一ledger/evidence，不得再bump version、建立commit/tag、重寫content或重新push。

### 2. after-commit/before-PREPARED 也有closed recovery

卡片沒有假裝此窗口不存在。若local commit/tag已形成但PREPARED尚未落盤，只能在下列全部成立時補PREPARED：

- selected exact run與approved stage/formal lineage一致。
- commit parent等於expected base。
- release namespace與唯一local tag一致。
- commit tree/diff中的public module等於sealed after state。
- remote仍為expected before main且target tag absent。

任一歧義或第三state均fail closed。隔離worktree在crash後可能被清理，但commit/tag位於共用Git object/ref store，仍可在不依賴暫存worktree bytes的情況下交叉驗證；不得以commit message或timestamp猜owner。

### 3. remote partial edge只補唯一缺邊

正常正式push仍使用既有atomic main+tag push。closed matrix額外處理exact partial remote state：

- main=target、tag=absent：只push exact target tag。
- main=base、tag=target：只push exact target main。
- main/tag=target：零push，只finalize。

這不是廣域repair或force reconciliation。每次補邊前都需驗PREPARED、stage/formal/replacement lineage、target commit tree、annotated tag object與peeled commit、expected before refs。remote第三SHA、tag多重/不一致、public after bytes drift一律零remote mutation並保留PREPARED。

## Authority review

### Published authority 未改變

published成立仍需同時具備：

- exact Git commit與target tag；
- remote main/tag指向同一target commit；
- 既有 `translation_published_runs` 中exact matching entry；
- entry綁定stage receipt、replacement lineage、old/new record與module digests、publication plan digest。

`PUSH_PREPARED` 不能選candidate、不能覆蓋Formal Reviewer、不能單獨證明published，也不能在remote或ledger drift時升格為成功。它是existing publisher transaction control/evidence，不是新authority ledger。

### 沒有第三個production source

兩個source仍足夠：

1. `scripts/agy_multilingual_pipeline.py`：closed terminal owner、stage seal、exact locale module proposed/apply bytes。
2. `scripts/agy_content_publisher.py`：selector、MutationJournal、local release、PREPARED、remote reconciliation、existing ledger/evidence finalization。

`app/web/static/article-locales.js` 只作inventory/first-match consumer，不修改。既有locale module只是transaction data target，不是Repair source change。若實作需要第三個production source、public loader precedence或新state owner，立即 `BLOCKED_SCOPE_EXPANSION`。

## Crash matrix review

| Window | Closed result |
|---|---|
| before local commit | MutationJournal/local Git rollback；零remote |
| local commit/tag後、PREPARED前 | exact orphan commit/tag驗證後只補PREPARED；歧義即BLOCK |
| PREPARED後、push前 | 執行一次原exact atomic push |
| remote main target、tag absent | 只補exact tag edge |
| remote tag target、main base | 只補exact main edge |
| both target、ledger absent | 零push，finalize同一ledger/evidence |
| ledger exact、evidence absent | 只補evidence |
| ledger/evidence exact | `ALREADY_PUBLISHED`，零寫 |
| remote第三SHA/tag歧義/after bytes drift | fail closed，零remote mutation |

矩陣已涵蓋原finding要求的post-push/pre-ledger crash、missing-edge-only convergence、second execute與remote divergence。測試名稱與可觀測counter也已在 `SLICE-PUSH-RECONCILIATION` 明列，可用fake git/remote實作，不需要production/provider呼叫。

finalization順序亦已封口為 `remote refs/after tree驗證 → idempotent ledger append → atomic evidence write → 移除exact PREPARED`。因此cleanup前crash只能清理matching stale control；正常control已移除時仍可由exact ledger/evidence/remote refs回 `ALREADY_PUBLISHED`。反向 `evidence存在但ledger缺失` 不是合法中間態，觀察到即fail closed。

## Source/test ceilings

修訂後 ceiling 可接受，但屬硬上限：

- production source總淨增 `<=420`：multilingual `<=190`、publisher `<=230`。
- tests總淨增 `<=760`：multilingual tests `<=360`、publisher tests `<=400`。
- 每個production source helper `<=6`，production source最多2檔，test最多2檔。

可行理由：publisher已存在 `_unresolved_push_path`、`_assert_no_unresolved_push`、`_reconcile_unresolved_push`、`_stage_commit_tag_push`、MutationJournal與ledger/evidence writer；實作應擴充這些owner，不另建transaction engine。若publisher需要超過230淨LOC或第7個helper，先縮約；不能縮回即BLOCK，不得以「crash完整性」擴張成通用FSM。

## Implementation order

1. `SLICE-LIFECYCLE-UNION`：先寫replacement attempt RED，完成closed terminal owner；保留完整generation regression。
2. `CHECKPOINT-01`：確認仍只有multilingual source、無mixed owner fields、provider=0。
3. `SLICE-EXACT-LOCALE-REPLACE`：先寫existing three-locale RED，再做exact in-place proposed/apply bytes與negative matrix。
4. `SLICE-PUBLISHER-TRANSACTION`：先完成真正zero-write dry-run、local apply/rollback、ledger schema；尚不宣稱remote closed。
5. `SLICE-PUSH-RECONCILIATION`：第一個RED固定為push成功後、ledger前crash；接著PREPARED-before-push、after-commit-before-seal、兩個missing-edge、both-pushed finalize、evidence-only與drift negatives。
6. `CHECKPOINT-02`：核對唯一順序 `stage → journal → local commit/tag → durable PREPARED → remote convergence → ledger → evidence`。
7. 跑兩個完整affected suites、py_compile、allowlist/LOC/helper ceiling與`git diff --check`；再交獨立code review。

不得平行先做publisher；它依賴stage seal與proposed after digest。不得先一次寫完整production再補RED。

## Stop conditions

- PREPARED可在缺stage/formal/tree/expected refs任一lock時驅動push或ledger。
- reconciliation掃描多run、多tag或以timestamp/commit message猜owner。
- missing-edge path使用force push、delete tag、rollback remote main或同時重發兩邊。
- remote第三SHA、tag object/peeled identity歧義或public after drift未做到零remote mutation。
- 需要新增transaction ledger/FSM/DB、第三production source、public loader/manifest precedence。
- after-commit/before-PREPARED不能由exact single commit/tag/tree/base證明。
- 超過source/test/helper ceiling且無法縮回。
- 同一blocker第三次重現。

## Verification seal

- card/source/test/production修改：`0`（本次只更新同一review RESULT）。
- provider/publisher execute/tag/push：`0`。
- 原 blocker：`RESOLVED_BY_SPEC`；implementation尚未開始，GO不等於code acceptance或production authorization。
