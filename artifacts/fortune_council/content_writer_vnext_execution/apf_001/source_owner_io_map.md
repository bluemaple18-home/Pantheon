# APF-001 Source Owner / I-O Map

| Source | State owner | Stable identity | Input | Dry-run output | Downstream seam |
| --- | --- | --- | --- | --- | --- |
| Matrix new | `agy_seo_copy_pipeline` + coordinator | `matrix/article_id/zh-TW/campaign_version` | Matrix backlog、create run states | `new` item | `seed_new_matrix_runs` |
| Legacy rewrite | Existing Publisher + coordinator | `legacy/article_id/zh-TW/campaign_version` | Legacy registry、rewrite inventory、Publisher ledger | `rewrite` item | `seed_legacy_rewrite_runs` |
| Translation of new | Multilingual pipeline + coordinator | `matrix/article_id/locale/campaign_version` | Source publication candidate、translation run states | `i18n-new` item | multilingual enqueue |
| Translation of rewrite | Multilingual pipeline + coordinator | `legacy/article_id/locale/campaign_version` | Source publication candidate、translation run states | `i18n-rewrite` item | multilingual enqueue |

`work_id` 為上述 identity 的 canonical JSON SHA-256 前 24 碼。dry-run 不呼叫 Publisher mutation 或 enqueue；i18n 項目僅描述候選，不預先配置 production run。
