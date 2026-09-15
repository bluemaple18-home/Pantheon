# Expansion 50E 契約漂移驗證收據

## 裁決範圍

- 修正 expansion-50e 舊 cohort regression 與 canonical `rewrite_existing_body` profile 的衝突。
- 不修改 Publisher failure taxonomy、scheduler、fairness、canonical policy 數值或 production state。
- recovery 僅列入能由保存的 production failure、candidate hash 與 failure-base replay 共同證明的 run。

## 產品修正

- 未改寫的 expansion-50e 文章仍維持 800–1400 字、4 節。
- `substantive_rewrite` 直接讀取既有 `rewrite_existing_body` presentation profile；測試不再另寫 1300–2000 字、5 節常數。
- canonical profile 不合格的 rewrite 仍由既有 Publisher policy path 在 full release suite 前寫成 terminal rejection。

## Production 證據

共同 log：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/logs/agy-content-publisher.stdout.log`

| 文章 | 字數／節數 | candidate SHA-256 | failure base | production stale assertion 行 | failure evidence |
|---|---:|---|---|---|---|
| ASTRO-EXPANSION-50E-0065 | 1699／5 | `3c5c9c1ed97030ff451730d42d2d7f0027f94bf33f38b965480b2256a90c55bf` | `97229db82bef22a8a97390c342ad49db90f66e27` | 85391–85402、89695–89706、91948–91959 | `state/evidence/failed-rewrite-3ab265b592/failure.json` |
| ASTRO-EXPANSION-50E-0070 | 1607／5 | `a6aee2f44eda9fe6601b4b1a2d4f7dcbb4034567c9970809954885770451102a` | `207f69ed34c8f09837560d546f8b832c50aabf80` | 94137–94148、100722–100733、102923–102934 | `state/evidence/failed-rewrite-e66f0cdd23/failure.json` |
| ASTRO-EXPANSION-50E-0071 | 1715／5 | `2af1b532c4714fe8ed8dc910688cdd2345fe34ef3bad2f54a4543243fb326c4a` | `127c41272877b6fd789b0c55e6221f851a75416f` | 96329–96340、105127–105138、107334–107345 | `state/evidence/failed-rewrite-84dfbe75e5/failure.json` |
| ASTRO-EXPANSION-50E-0073 | 1548／5 | `cb9b3e68cf4758e9fd23e1459893bfe591b729efe07195d0455a868146ff224a` | `b930a28af669138df0289eaef1e25030a66401de` | 98524–98535、109544–109555、111757–111768 | `state/evidence/failed-rewrite-7bc91eb20b/failure.json` |
| ASTRO-EXPANSION-50E-0079 | 1543／5 | `279509d199c9dabea9060063de67902fd17e50f1dad59ff65de426ba46cc4909` | `e5413cc61e3f74c62972958947318b80d8b4f44d` | 117632–117643、124316–124327、126550–126561 | `state/evidence/failed-rewrite-b96dc54e73/failure.json` |
| ASTRO-EXPANSION-50E-0083 | 1561／5 | `c33963eb446784558e1031b794705eac71379af01801137dca11b10930dc5fd3` | `951f6f726977728ee394bb0b6bd1456c98ca2b0e` | 115410–115421、119857–119868、122085–122096 | `state/evidence/failed-rewrite-af808347bc/failure.json` |

上表每個 production failure 都命中同一個測試 `test_expansion_50e_adds_fifty_unique_full_articles`，且錯誤皆為合法 canonical rewrite 字數大於舊上限 1400。六個 retry record 均為 3/3 exhausted、`retryable=true`、candidate preserved。

## Failure-base RED → GREEN replay

每篇均在表列 failure base 的 detached worktree，以保存的 candidate 執行既有 `apply_rewrite_release()`，再只跑 expansion-50e target：

1. 舊測試：六篇各自精確 RED，錯誤依序為 1699、1607、1715、1548、1543、1561 `<= 1400`。
2. 僅套用本候選的 migration-aware 50e test diff。
3. 新測試：六篇各自 `1 passed`。

重播產物另以 SHA 校驗保存於本機 `/private/tmp`，供本輪 review 追查；產品 commit 不納入生成文章：

| 文章 | replay tracked patch SHA-256 | generated module SHA-256 |
|---|---|---|
| 0065 | `b6f26acea08f4dbde8b866a91aea444d720415bcc9d5fa28964cf7ff259884fa` | `dadbccffee08506917300189976c8d06bdce50a66d7c89385e59bded11e6bbc2` |
| 0070 | `00e83cbbc18523e46591a4a84dbc59609c9e8da00262b6a1ed275fbc8e41d6c6` | `3c5794726a8fab5e765c90bb96bf112c6d9f6bb6a7e2d95828f347e9f3621229` |
| 0071 | `5eebffb365ddbbb0e550508905fbf9b36bce4a5e8490d25219bd40fcb4daf75c` | `0a911fcffaca5da949717994af75a4a447c9e54f27c2de5c0cf8596beec46831` |
| 0073 | `23ca6c884773fe3f1c9c5723befcd1a086f368d4e975c7aa9587e176caa56d7f` | `1d7d05ac40e483a589309e45666dcb393bef12c6356037b9ad22f50890aedad3` |
| 0079 | `e7b11fa0688cefc7ec6d5a366ae9309a75851bc7ae79a02218ae84bb735c950a` | `80387520caf51fb27413dd517b5defede11edded490cd9b8c035ed763424b8d9` |
| 0083 | `eb32528cc0092dc3d7927b57d51baab4ac7add01fb916b87a660ae6a810c608a` | `09e946f284af640ca5c56328d453df612ca80aac3c46a0936c36cc3ab2933fdb` |

## Recovery eligibility

只有上列六個 exact run 具備完整的 candidate hash、failure timestamp、failure evidence、三次 production stale assertion 與各自 failure-base RED→GREEN replay。後續 recovery 必須使用既有 dry-run digest／CAS apply，並再次核對 candidate 與 evidence bytes；本卡未修改 production retry state。

## 驗證

- focused contract tests：5 passed。
- Publisher 全檔：214 passed。
- affected full release suite：758 passed。
- `py_compile`：PASS。
- `git diff --check`：PASS。

獨立 review 結果待候選 commit 後補記。
