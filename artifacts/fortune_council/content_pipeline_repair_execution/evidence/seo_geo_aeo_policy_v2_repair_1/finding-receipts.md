# Repair-1 Finding Receipts

## P1-001 — Rewrite prerender mode 與 terminal rejection

- Publisher 以 `ARTICLE_ID=rewrite_existing_body` 顯式傳入 prerender。
- Prerender 使用該 mode 呼叫同版 validator，不再固定當 create。
- Structured prerender failure 轉為 `PolicyRejected`；mutation recovery 後寫 terminal
  policy evidence，`retry_eligible=false`，不建立 transport retry。
- `policy_rejected` 是 scheduler 正常收斂狀態，避免外層 runner 因非零結果忙迴圈。

## P1-002 — Cultural reflection evidence bypass

- Machine-readable policy 定義 deterministic verifiable-claim regex markers。
- Marker 只表示「需要 evidence」，不判斷主張真偽。
- `cultural_reflection` 命中研究、統計、百分比或方法效果主張時 required fail；可刪除
  主張或提供真實來源，不得虛構引用。
- 純文化／反思 disclosure 仍可無來源通過。

## P1-003 — No-op rewrite

- Candidate validator、rewrite quality gate、apply gate 與 publisher apply 都帶入
  `current_body_sha256`。
- Proposed canonical body hash 等於 current hash 時回報 `no_substantive_change`，在任何
  metadata 或 override 寫入前 fail closed。
- 真正正文變更仍可標記 `substantive_rewrite` 並更新真實 modified。

## P2-001 — Full audit completeness

- Artifact 缺檔不再以 hypothetical render 取代，直接記錄
  `initial_html_artifact_missing`。
- 全 inventory 傳入 cross-corpus validator。
- Duplicate ID／route findings 綁回每個 `inventory_index` migration item。
- Audit input hash 涵蓋 machine policy、sitemap、inventory、body 與 artifact SHA-256。

## P2-002 — Single source presentation profiles

- Machine policy 明確區分 `create` 與 `rewrite_existing_body` profiles。
- Candidate schema、external schema、structural validator、quality validator、writer 與
  reviewer public contract 都由 loader 取得門檻。
- 動態 policy mutation regression 證明 validator 與 JSON schema 同步採用新值。
