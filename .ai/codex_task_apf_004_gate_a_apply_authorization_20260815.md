# APF-004 Gate A apply 授權卡

## 狀態

`AWAITING_USER_AUTHORIZATION`

本卡只鎖定下一個 production mutation；未取得使用者逐動作明確批准前，不得建立執行 thread、不得執行 apply。

## 已核准證據

- Reviewer：`APPROVED`
- 本機整合 commit：`2c6640926501cbdc6b1fb5490acc99b0ae0c422d`
- target/source SHA：`28b8b84b6dfa319d8151aac3bc1a6a819ae82aa1`
- plan digest：`46e720652f39441413afc9dac6805465227800cfcf2240e612f76088167e8b8b`
- target manifest digest：`c57a95aa72d8e01c676e50a9a54156da04ef1f9c3b4c86fa788819200df586a2`
- exact apply argv digest：`7eda8a88c32aff500b926f40f8151ae8a7153a2bfc37d13661a483acbb37136c`
- current production mutation：`0`

## 待授權單一動作

執行 `exact-apply-argv.json` 記錄的唯一 `apply`，以 `--expected-plan-digest 46e720652f39441413afc9dac6805465227800cfcf2240e612f76088167e8b8b` 綁定已核准 plan。

權威 argv artifact：

`artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/deterministic_plan_reproduction_after_digest_repair_20260815/exact-apply-argv.json`

唯一 Gate A evidence root：

`artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/gate_a_deterministic_plan_apply_20260815/`

此目錄必須在 apply 前不存在；本次只可在此建立 apply stdout／stderr、pre／post snapshots、receipt、postchecks、mutation summary、verification 與 artifact digests。不得覆寫既有 Gate A evidence root。

## 執行前 fail-closed gates

1. `origin/main` 必須包含本機整合 commit，且 target source `28b8b84...` 可讀、clean、origin 正確。
2. actor SHA、manifest digest、private-stage digest、capacity receipt digest、stop-loss 必須與 plan 證據一致。
3. transaction root 必須不存在；queue 必須維持 empty。
4. exact argv raw canonical digest必須仍為 `7eda8a88...`。
5. 任一 drift → 不執行，回 `BLOCKED`。

## 授權邊界

- 本次批准若取得，只涵蓋單次 `apply`。
- 不涵蓋 rollback、finalize、Gate B、publish、deploy、queue、tag、push 或其他 production mutation。
- apply 完成後先停，產出 receipt、postchecks、mutation summary，交既有 Reviewer 唯讀審查。
- 不得沿用舊 Gate A authorization。

## 使用者批准格式

`批准 Gate A 單次 apply，plan digest 46e720652f39441413afc9dac6805465227800cfcf2240e612f76088167e8b8b。`
