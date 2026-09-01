# C-B exact terminal translation materializer correction

狀態：`READY_FOR_REBUILD`

## 目的

在既有 Coordinator seam 提供單一 externally pinned pending receipt 的 terminal-source translation materializer；translation registration 僅能重用 `multilingual.enqueue_article_translations(...)`。

## 範圍與禁止

可改 Coordinator、focused coordinator tests 與本目錄的 result/raw evidence。不得改 multilingual pipeline、Runner、C-A、installer、Publisher、manifest、model route、runtime queue/registry production artifacts 或公開內容；不得 commit/push/activation/provider/production mutation。

## 必要契約

- CLI 同時 exact pin target run、pending digest、plan digest，任一 mismatch 在 lock/enqueue/translation write 前 reject。
- pending selector 必須 absolute、lexical canonical、non-symlink、regular、owner-safe、safe mode 且 parent canonical。
- source terminal authority 與 target registration identity 於 enqueue 前後、pending terminalization 前均以 exact snapshot/CAS 重新驗證。
- result/materialized receipt 綁 source/target run、pending before/after digest、plan digest、brief SHA 與 stable registration identity digest proof graph。
- materialized `pending_digest_after` 必須由 strict pending payload 與完整 proof graph 重建；不可只做 SHA format 檢查。
- materialized replay 必須由 current strict pending body 重建 pre-terminal canonical file digest，並與 externally pinned `pending_digest_before` 相等。
- selector 在 lock 後、final authoritative read/CAS 前與 terminal write 前均重新驗 canonical、安全屬性與同一 inode identity。

## 驗證

1. RED：external pins、selector、target registration、source/CAS/replay drift 均在 mutation 前 reject。
2. GREEN：exact completed source 經既有 enqueue 一次 materialize，可 idempotent recovery；跑 focused coordinator/APF plan tests、py_compile、diff-check。

## 結果

- focused materializer matrix：25 passed；CLI/APF affected regression：3 passed。
- formal review NO_GO candidate `71d3e828` 的 pre-terminal pending body binding finding 已以 RED regression 關閉；本卡只標 ready-for-rebuild，未主張 review GO。
- 本卡僅為未提交 implementation candidate；未主張 runtime activation 或 independent review。

## 最小性

why_not_less：既有 pending + enqueue recovery 不足以提供 externally pinned immutable session authority 與 replay proof graph。

why_not_more：重用 existing enqueue、pending receipt 與 Coordinator seam；不新增 translation state、ledger、FSM、database 或 runtime。
