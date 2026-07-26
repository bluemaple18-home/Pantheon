# Pantheon Policy v2 Repair-1 Contract

- Chain: `PANTHEON-SEO-GEO-AEO-POLICY-V2-20260725`
- Repair round: `1`
- Base candidate: `20b1c20f0ef892af98773f03630d095d4c5c6cd9`
- Review verdict input: `REVIEW_NO_GO`
- Policy version: `pantheon-article-publication-v2.0.0`
- Status boundary: `CANDIDATE_ONLY`

本修復只處理 `P1-001`、`P1-002`、`P1-003`、`P2-001`、`P2-002`。不得由
Repair thread 宣稱 review accepted、integrated、deployed 或 production fixed。

驗收證據必須包含 red-capable regression、targeted tests、完整三檔 pytest gate、454 篇
deterministic audit、allowlist check、`git diff --check` 與 candidate commit。
