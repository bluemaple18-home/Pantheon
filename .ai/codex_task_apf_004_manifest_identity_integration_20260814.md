# APF-004-MANIFEST-IDENTITY-INTEGRATION-001

- 目標：將 Reviewer 核准的 manifest create hardened identity 修復 `b479be9b6eedd1d8c0063d4bd76798a3d1068ba5` 整合到 APF-004 integration branch。
- 基線：`8fea7a47a86a97e0dd1eb6af94df1ba6056e7a17`；Reviewer：`019ffb96-c9fc-7463-856f-aa37988846df`；Verdict：`REVIEW_APPROVED`。
- 可改：candidate 的 runtime manifest、direct tests、repair card/evidence，加本 integration card；完整保存 candidate 行為，不手改語意。
- 禁止：live manifest/stage/runtime/plist write、install/activate/launchctl mutation、push/deploy/publish/tag/schedule、root checkout mutation。
- 驗收：確認 content/patch equivalence；重跑 manifest suite、三 installer affected slices、diff/DBG/secret/path/binary gates；commit；回 `INTEGRATION_READY | BLOCKED`，附 SHA，`mutation_executed=false`。
