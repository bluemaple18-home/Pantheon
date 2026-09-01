# C-B materializer implementation result

狀態：`CB_REPAIR_READY_FOR_REBUILD`

- 僅新增 exact pending materializer 的 Coordinator seam 與 focused tests；實際 translation registration 仍只經既有 `multilingual.enqueue_article_translations(...)`。
- 25 個 focused cases 覆蓋 external target/pending/plan pins、selector canonical/ownership/mode/inode revalidation、target registration、source terminal/replay/CAS drift、enqueue crash recovery、proof graph tamper、重建 pending digest-after、重建 pre-terminal pending digest，以及 new/i18n-rewrite 的 idempotency。
- result/materialized receipt 回傳並綁定 source/target run、pending before/after digest、plan digest、brief SHA 與 registration identity digest。
- 所有 materializer invocation 僅在 temporary fixtures；未對 runtime/production queue 或 state 執行 materializer。
- `forensics/cb-review-no-go-71d3e8-20260901` 的 P1 已關閉：replay 現由 current strict pending body 重建 canonical pre-terminal file digest，並比對 immutable externally pinned `pending_digest_before`；同時保留 terminal digest reconstruction。未提交；clean integration、independent review 與 runtime activation 均未執行。剩餘風險是需由獨立 reviewer 檢驗 durable receipt/CAS 語意與既有 enqueue idempotency 的跨程序行為。
