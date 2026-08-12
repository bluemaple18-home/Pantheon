# RA007 P1 Repair Re-review 規格審查

修復已完成原 P1 的主要量測面：兩個 sample 都有 VM allocation、swap、memory pressure 與 Codex RSS，interval 為 3 秒，且 reserve、deficit 與 delta 均可重算。

但本次固定契約要求 digest 可重算。兩個 committed `measurement_digest` 沒有記載 domain、canonical projection 或足以重建 canonical guard receipt 的原始資料；以 sample 本身去除 digest 後的 stable JSON SHA-256 也不相符。因此 digest 不是可驗證 evidence，原 P1 尚未完整修復。

判定：`REVIEW_NO_GO`。
