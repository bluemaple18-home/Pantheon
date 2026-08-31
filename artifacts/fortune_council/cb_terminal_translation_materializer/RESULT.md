# C-B exact terminal-source translation materializer receipt

結果：`CB_IMPLEMENTATION_READY_FOR_FREEZE`

CB_REVIEW_NO_GO evidence（P1）已保留並修復：replay 不再只驗 translation registration；它會重驗完整 source state／brief／candidate／review／normalized source，重算 expected translation brief，並拒絕 rewrite immutable brief drift。enqueue 後的 final CAS 也改為比較完整 source authority snapshot，而非只比較 state。

- CLI 僅接受一個 `source_run_id` 與一個 canonical pending receipt；重複 selector 直接拒絕。`main()` 正向會將 resolved repo/queue/receipt 原樣交給唯一 materializer invocation、輸出 result JSON 並回傳 0；拒絕則輸出 rejected JSON 並回傳 1。
- source terminal state、identity envelope、candidate/review SHA、pending payload digest、plan digest、dependency、lane/run/article/locale 均在 enqueue 前驗證。
- materialized receipt 在 exact target run lock 下以原 receipt canonical digest 作 CAS re-read；若 drift，不 terminalize。
- translation registration 只由既有 `multilingual.enqueue_article_translations` 執行；brief-only/state-missing crash window 只有 byte-identical expected brief 才可重入。
- runtime/public/provider 均未觸發；clean integration 與任何 production activation：`NOT_RUN`。
