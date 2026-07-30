---
card_id: CARD-PANTHEON-LEGACY-REWRITE-SEMANTIC-BOUNDARY-INTEGRATION-20260730
chain_id: pantheon-legacy-rewrite-semantic-boundary-integration-20260730
role: integration
cycle: 1
status: CARD_DRAFTED
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 已核准的 rewrite approval 核心契約需跨最新 main、production actor、LaunchAgent 與真實 non-publishing retry 驗證；錯誤整合會阻斷或誤放舊文發布。
project_id: local-0020d4379451d545eb08362962f1def0
repo_identity: github.com/bluemaple18-home/Pantheon
required_base_ref: origin/main
required_base_sha: 9a853081c66769234871f1821c4e5e89ac76855b
implementation_candidate: 6235afea4a22153cc1f436a3143557086d64d377
review_evidence_commit: 15e3e718d0db31cfd00a15ef14055a69e66f2fb3
ownership: approved semantic-boundary candidate integration, verification, push, actor sync, service reinstall, and one non-publishing production retry
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-LEGACY-REWRITE-SEMANTIC-BOUNDARY-INTEGRATION-20260730/
---

# Pantheon Legacy Rewrite Semantic Boundary Integration

## 目標

把已獨立 `REVIEW_GO` 的 rewrite semantic/objective boundary 修復整合到最新
`origin/main`，完成 fresh gate、push、production actor 對齊與服務重裝，最後只做一次
不發布的真實 provider retry，確認舊文流程能正確消化既有 receipt。

## 已知證據

- Implementation：`6235afea4a22153cc1f436a3143557086d64d377`
- Reviewer evidence：`15e3e718d0db31cfd00a15ef14055a69e66f2fb3`
- Reviewer verdict：`REVIEW_GO`，273 個不重複測試通過，無 P0/P1。
- 指派時 production main：`9a853081c66769234871f1821c4e5e89ac76855b`。
- Implementation parent `3ee7b2d3...` 是指派時 main 的 ancestor；整合需保留其後所有內容 release。

## 可改／可操作範圍

- `scripts/agy_seo_copy_pipeline.py`
- `tests/test_agy_seo_copy_pipeline.py`
- 本卡 implementation/review/integration evidence
- 以乾淨 worktree 整合上述兩個核准 commit 到最新 `origin/main`
- fresh 驗證通過後 push `HEAD:main`
- 對齊 production publish actor 到推送後 SHA
- 以既有 production 設定重裝 coordinator／lane／publisher LaunchAgents
- 執行一次 non-publishing rewrite provider retry，保存 evidence

## 禁止範圍

- 不修改 policy 閾值、禁詞表、文章 registry、共享 metadata、生成頁、sitemap、feed 或 redirects。
- 不手改 queue、receipt、approval、ledger、文章內容或 provider 回覆。
- 不新增替代 Implementation／Reviewer／Repair 卡；不使用 sub-agent。
- 真實 retry 不得 publish；只有 Publisher 既有週期可依既定 gate 發布其他已核准項目。
- 任一 fresh gate 失敗時不得 push／deploy；同一 blocker 三次即停止。

## 驗收

1. Candidate 與 review evidence 可乾淨套用到最新 `origin/main`，無遺失後續 release。
2. Fresh targeted、SEO pipeline、coordinator、publisher、multilingual 與 `git diff --check` 全綠。
3. 推送後 `origin/main`、production actor HEAD 與 LaunchAgent expected runtime SHA 完全一致。
4. 一次 non-publishing retry 保留 deterministic authority：客觀 machine-owned finding 不造成假 semantic REJECT；真正語意／未知／malformed finding 仍 fail closed。
5. 保存 changed files、測試數量、整合 SHA、push／runtime／retry evidence；不得用狀態文案代替證據。

## 交付

- 若全部通過，回報 `INTEGRATED`、完整 SHA、fresh test 數量、actor/service 對齊與 retry 結果。
- 若任何 push 前 gate 失敗，停在 `BLOCKED`，不得部署。
- 不自行清理或封存本正式 thread；交回主線驗收。
