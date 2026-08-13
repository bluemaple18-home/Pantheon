---
id: APF-001-REPAIR-001
status: ready
type: implementation
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: repair
cycle: 1
thickness: standard
risk: medium
model: gpt-5.6-terra
reasoning: medium
model_reason: 固定 P1 的 bounded Repair；只修 campaign-version dedupe 與回歸測試，不改架構或 production。
traces_to:
  - APF-001
  - US-002
  - FR-017
  - SC-001
---

# APF-001 Repair-001｜修正跨版本 rewrite 去重

## Root Finding

`P1-APF001-CAMPAIGN-DEDUPE`：候選 `f0770c24b68f323df9843f1988d7f1bfa0e7938f` 在 `scripts/agy_gemini_coordinator.py:1769-1771,1807-1812` 只用 `article_id` 判定既有 rewrite。任何舊 campaign run 都會永久排除該舊文；新 `campaign_version` 無法建立新的全量 rewrite workset。

主線重現：queue 含 `LEGACY-001 / campaign_version=rewrite-v0 / completed`，要求 `rewrite-v1` 時輸出 `rewrite_items=[]`、`rewrite_registered_or_unavailable=1`。

## 目標

讓 rewrite 與 i18n dedupe 綁定 current campaign version：同版本重跑不重複；舊版本或 legacy 無版本 run 不得阻擋新版本 campaign。保留 create/new 永久 article identity 去重。

## Source

- candidate：`f0770c24b68f323df9843f1988d7f1bfa0e7938f`
- parent card：`.ai/codex_task_pantheon_writer_vnext_apf_001_source_campaign_contract_20260813.md`

## Allowlist

- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`
- `docs/pantheon_writer_vnext_auto_source_campaign_contract.md`
- `artifacts/fortune_council/content_writer_vnext_execution/apf_001/**`

其餘唯讀。禁止修改 Publisher、multilingual、LaunchAgent、scheduler、production、V9、SEO/GEO、queue/state/ledger。

## Acceptance

- `AC-R1-01`：舊 rewrite run 的 campaign version 不同或缺失時，current campaign 仍列出該 eligible article。
- `AC-R1-02`：同 campaign version 已有 rewrite run 時排除；同版本雙跑 stable。
- `AC-R1-03`：translation dedupe 至少包含 `campaign_version`；舊版本 translation 不阻擋 current campaign，current campaign 同 locale 不重複。
- `AC-R1-04`：new/create 去重維持原 article identity 行為。
- `AC-R1-05`：`campaign_version` 必須為 trimmed non-empty single-line 值；不得讓空白形成不同 identity。
- `AC-R1-06`：新增明確 regression test，先 RED 後 GREEN；原 APF focused test 與全檔通過。
- `AC-R1-07`：更新 committed dry-run evidence／receipt，不保留錯誤的跨版本宣稱。

## Verification

- focused regression：old campaign／missing campaign／same campaign rewrite；old／same campaign translation。
- `.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -q`
- `git diff --check`
- changed files 僅 allowlist；worktree clean；candidate commit 完整 SHA。

## Stop

- 需要改 queue schema、Publisher、multilingual 或 allowlist 外檔案。
- 需要 production mutation／外部 provider。
- 同一 blocker 第三次失敗。

交付只能是 `DELIVERED_CANDIDATE` 或 `BLOCKED`；不得 push、deploy、開新 task。
