# Create description repair 正式套用範圍

- 目標：解除新文連續 8 次在 transport `description minLength` 提前失敗，讓 49–63 字回應進入既有本機 repair；最終 70–95 字 gate 不變。
- 候選：`9730db3130d910af72f536266f552d61b8122c2d`，直接承接目前正式 `ebfa35a351`；只改 `scripts/agy_seo_copy_pipeline.py` 與對應測試。
- 證據：RED 重現 provider schema 仍含 minLength；修後 4 項精準測試 PASS，真實 `GeminiClient.generate_json` 配 fake transport 可到達本機 repair；獨立 Reviewer GO。完整單檔為211 PASS／26 個既有 sparse fixture 與舊路由失敗，不宣稱全庫通過。
- 正式操作：沿剛才同一 native promotion、容量 preflight、七服務安全停止／stage／activate／identity 驗證；失敗即回退 `ebfa35a351`。不清 queue、failed runs、allocator，不手動重試或額外試打 provider。
