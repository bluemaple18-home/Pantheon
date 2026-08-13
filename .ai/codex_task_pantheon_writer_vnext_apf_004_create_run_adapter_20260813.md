---
id: APF-004-CREATE-RUN-ADAPTER
title: 建立四 lane exact production create-run adapter
status: ready
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: implementation
cycle: 1
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
model_reason: 規格已固定，但 adapter 會建立 production queue identity 並銜接 Writer／Reviewer／Publisher，需核心 fail-closed 契約
parent_candidate: cd52858d3989457062b10d8486fa5275b3235ddb
traces_to:
  - US-004
  - FR-012
  - FR-014
  - SC-001
  - SC-003
  - SC-008
---

# APF-004-CREATE-RUN-ADAPTER｜四 lane exact production create-run adapter

## 任務五行卡

- 目標：新增唯一正式入口，將已確認的四個 `work_id/article_id/locale` tuple deterministic 轉成 exact Writer／Reviewer／Publisher run/handoff identity。
- 可改：coordinator 的最小 adapter、既有 multilingual enqueue 接線、對應測試、契約文件與本卡專屬 synthetic evidence。
- 禁止：不得呼叫外部模型、寫 production runtime、publish、transaction、tag、push、deploy、schedule、LaunchAgent；不得手寫 queue JSON 繞過既有 validator/register boundary。
- 驗收：plan-only 零寫入；apply 使用既有正式 registration/enqueue boundary；四 lane identity 唯一、可重算、可 resume、重跑不重複；任一漂移在任何寫入前 fail closed。
- 證據：RED→GREEN tests、positive/negative matrix、兩次 idempotent synthetic apply、`git diff --check`、單一 clean candidate commit。

## 已確認 payload

| lane | work_id | article_id | locale |
|---|---|---|---|
| new | `apf-work-b1666341df10a14c1a586141` | `ASTRO-SCENARIO-BIG-THREE` | `zh-TW` |
| i18n-new | `apf-work-44bd155e28231d25d65f3394` | `ASTRO-SCENARIO-BIG-THREE` | `ja` |
| rewrite | `apf-work-0146edbbed78ec5debf138d4` | `ASC-AQUARIUS` | `zh-TW` |
| i18n-rewrite | `apf-work-1eeac7f0a8fff378eb65c190` | `ASC-AQUARIUS` | `ja` |

Campaign 固定 `apf-001-v1`。本卡實作通用 bounded adapter，但 acceptance fixture 必須鎖以上四 tuple。

## 核心契約

1. 新增 public production entrypoint；輸入至少含：validated campaign workset、exact 四 tuple、campaign version、queue/state/run roots、runtime identity/correlation、`plan_only`。
2. 入口先完整 preflight，再有任何寫入：
   - workset SHA／campaign version；
   - lane、work_id、article_id、locale 一致；
   - 剛好四 lane，各一筆；
   - new↔i18n-new、rewrite↔i18n-rewrite source pairing；
   - roots 安全、互不重疊、production allowlist 明確；
   - runtime identity、correlation、actor identity 不漂移；
   - queue/state 既有 identity 無衝突。
3. exact IDs 必須由 immutable tuple 重算，不接受 caller 自填 run ID。重跑相同輸入回相同 IDs；任一內容漂移 deterministic BLOCKED。
4. `plan_only=true` 全程零寫入，輸出四 lane exact IDs、stage dependency、正式 entrypoints 與預期 write set。
5. apply 不得直接寫 queue state：
   - new/rewrite 重用既有 brief validator 與 `register_run`；
   - translation ID 重用 `translation_run_id`；source candidate 未完成時只保存由正式 adapter 擁有、可驗證的 pending dependency，不可偽造 translation candidate；source 完成後重用 `enqueue_article_translations`；
   - Writer／Reviewer／Publisher 仍由既有 coordinator/publisher 入口執行，本 adapter 不取代它們。
6. 兩階段落盤：四 lane preflight 全過後才 apply；部分寫入失敗必須留下可 resume transaction receipt，重跑只補缺段，不產生第五個 run。
7. production execution 預設 fail closed：必須明示 confirmed payload digest、activation/authorization digest、runtime roots 與 `max_runs=1` downstream contract；缺一不得 apply。
8. 本卡只實作與 synthetic 驗證。不得在本卡執行 APF-004 production canary。

## Negative matrix

- 缺 lane／重複 lane／多第五筆。
- work_id、article、locale、campaign version、workset SHA 漂移。
- translation/source pairing 錯誤。
- caller 自填 run ID／status／verdict／ready。
- queue/state/run roots 重疊、越界、symlink escape。
- runtime/actor/correlation 漂移。
- 既有相同 identity 內容不同；部分 transaction receipt 損壞。
- plan-only 任何檔案變動。
- apply 第二次重跑產生重複 run。

所有 negative case 必須在不可安全 resume 的任何寫入前 `BLOCKED`。

## Allowlist

- `scripts/agy_gemini_coordinator.py`
- `scripts/agy_multilingual_pipeline.py`（只有確有必要的最小既有 enqueue 接線；優先不改）
- `tests/test_agy_gemini_coordinator.py`
- `tests/test_agy_multilingual_pipeline.py`（只有修改 multilingual 時）
- `docs/pantheon_writer_vnext_auto_vertical_chain.md`
- `artifacts/fortune_council/content_writer_vnext_execution/apf_004_create_run_adapter/**`

若需改 Publisher、Writer schema、scheduler、installer、LaunchAgent、文章、registry、release record 或 allowlist 外 production code，停止回報 scope change。

## 驗證

1. 先新增 public-interface RED tests，再最小 GREEN。
2. focused adapter tests；既有 coordinator 全檔測試。
3. 若改 multilingual，跑其 focused affected tests。
4. synthetic plan-only 連跑至少三次：output digest 相同、零寫入。
5. synthetic apply 連跑兩次：四 exact IDs 相同、無 duplicate；transaction receipt 可 resume。
6. negative matrix 全綠。
7. `git diff --check`；shared artifact `rg '/Users/|mattkuo|file://'` 零命中；worktree clean。

## 交付

- `READY_FOR_REVIEW | BLOCKED`
- candidate SHA、changed paths、正式 public entrypoint/signature。
- 四 lane exact IDs 與 dependency graph。
- 測試／plan-only／apply／negative evidence。
- 明示未 external model、production runtime、publish、transaction、tag、push、deploy、schedule、activation。
