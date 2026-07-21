---
card_id: CARD-CONTENT-GEMINI-REVIEWER-TRANSPORT-DESIGN-001
chain_id: CONTENT-GEMINI-REVIEWER-TRANSPORT-DESIGN-001
status: RUNNING
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: Gemini CLI strict JSON 的失敗已跨兩代 Repair 重現；本卡涉及模型能力、CLI transport、schema 邊界與三條內容線的恢復條件，屬核心架構 fork
ownership: Gemini CLI Reviewer transport 的能力探索、bounded prototype 與恢復建議
allowlist:
  - scripts/agy_gemini_transport_probe.py
  - tests/test_agy_gemini_transport_probe.py
  - docs/pantheon_gemini_reviewer_transport_strategy.md
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_transport_design_001/**
forbidden_scope:
  - app/**
  - scripts/agy_seo_copy_pipeline.py
  - scripts/agy_gemini_outbox.py
  - scripts/agy_gemini_runner.py
  - 正式文章、registry、metadata、prerender、sitemap、feed、redirects
  - Gemini CLI 安裝、登入、OAuth、token、全域設定或模型 alias 修改
  - merge、push、deploy、publish、production
verification:
  - probe unit tests
  - sanitized Gemini CLI bounded matrix
  - strict parse/schema/content-quality result matrix
  - secrets/raw-output/path scan
  - git diff --check and changed-file allowlist
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_transport_design_001/
source_kind: commit
source_sha: 7afe5f792af1c87cd983af2f1be6dafb634650e1
source_branch: main
source_clean: true
main_cwd: <repo-root>
worktree_path: <codex-worktree>/87fe/Pantheon
cwd: <codex-worktree>/87fe/Pantheon
worktree_exists: true
thread_id: 019f824b-949e-71d3-be96-1e830bdeba51
thread_status: RUNNING
thread_host_id: local
rollout_path: <codex-sessions>/2026/07/21/rollout-2026-07-21T09-30-19-019f824b-949e-71d3-be96-1e830bdeba51.jsonl
previous_card_id: CARD-CONTENT-GEMINI-REVIEWER-JSON-REPAIR-002
previous_thread_id: 019f8224-7f16-7461-9b00-16793ecd9c80
previous_worktree_path: <codex-worktree>/ec5e2828-70a0-4fe5-a08c-c99bb5c433d5/Pantheon
previous_candidate_sha: f74d3654bfe0377c34ade128b131d42cf6bb8e41
---

# CARD-CONTENT-GEMINI-REVIEWER-TRANSPORT-DESIGN-001｜Gemini Reviewer transport 重設計

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-TRANSPORT-DESIGN-001`；這是新 architecture chain，不是 Repair 3。
派工對象｜`gpt-5.6-sol`、`high`；先證明 Gemini CLI 的 task-model fit，不修改正式 pipeline。
任務目的｜用 sanitized 代表性 Reviewer 輸入，找出至少一個可連續穩定通過 strict JSON、schema 與內容 rubric 的 CLI transport 方案，或以證據判定 Gemini CLI 不適任 machine gate。
可改範圍｜獨立 probe、probe tests、策略文件與本卡 evidence；既有 pipeline、文章與發布檔全部禁止修改。
驗收證據｜能力盤點、bounded matrix、每次呼叫的 sanitized fingerprint、3/3 穩定門檻、成本／風險比較與明確 GO／NO-GO。

## 固定事實

- Repair 002 diagnostic candidate：`f74d3654bfe0377c34ade128b131d42cf6bb8e41`；只讀檢查，不整合、不修改。
- Repair 002 已證明：Reviewer 首次 parse failure 後唯一一次 fresh retry 仍為 `StrictJsonParseFailure`；candidate SHA 不變且 Writer 未重跑。
- Current CLI transport 使用 `--output-format json` envelope，但 Reviewer response text 仍須本地 `json.loads`；不得把 envelope JSON 誤認為 response schema 已受 CLI 強制。
- 本卡必須實際使用既有 Gemini CLI，但只允許 read-only／dry-run 推理；不安裝、不登入、不變更任何外部或全域設定。

## 研究問題

1. 目前可用 Gemini CLI 的實際 command、版本、output mode 與 model routing 是什麼？只保存版本／capability 與 command SHA，不保存本機絕對路徑或憑證。
2. 失敗主因是長 prompt、深層 schema、Reviewer 模型／thinking 模式、CLI envelope，還是 response 被截斷／包裝？
3. 下列候選中，哪一個能達成 3/3 strict parse + schema + rubric：
   - current single-pass strict JSON baseline；
   - 縮小為 verdict/findings 的 minimal schema；
   - 兩階段 reviewer：Gemini CLI 產生受限 judgment，再由 deterministic local mapper 建構正式 review JSON；不得由 mapper 猜測缺失判斷；
   - 同一 CLI 可用的另一 Reviewer model／thinking 設定，但不得修改全域 alias。
4. 若全部失敗，Gemini CLI 是否應降級為 advisory reviewer，由 deterministic gates 擔任 machine gate？

## 執行上限與停損

- 最多測 3 個 configuration，每個最多 3 次 fresh process；總 Gemini CLI 呼叫上限 9。
- 先跑一個 public/sanitized representative case；未通過不得擴大文章數或接正式文章。
- 同一 blocker 3 次即停；不得建立第 4 次相同嘗試。
- 禁止保存 raw model output、prompt、stderr、秘密、個資或本機絕對路徑。只保存 request/config SHA、output SHA、byte length、parse/schema/rubric 結果與必要 error position。
- CLI 不存在、未登入或缺可驗證 capability 時，立即 `BLOCKED`，不得安裝、登入或改設定。

## 成功條件

- 至少一個 configuration 在 3 個 fresh process 全數通過：CLI exit 0、response strict JSON parse、schema validation、rubric validation。
- 三次輸出可不同，但 verdict 與 hard-failure 判定不得互相矛盾。
- 產出推薦架構、拒絕方案、剩餘風險與下一張 implementation 卡的精確 interface；本卡不得直接修改 production pipeline。
- 若無方案達標，交付 `NO_GO_GEMINI_CLI_MACHINE_GATE`，建議 advisory-only 邊界；不得恢復新文、舊文修復或 GSC 調整線。

## Gate 1–5

- Gate 1：實體卡與完整 prompt 契約存在，main source commit clean。
- Gate 2：正式側邊欄 thread、獨立 worktree、rollout 與卡片可讀皆驗證後才執行。
- Gate 3：只交付設計／probe candidate commit 與完整證據，不宣稱 production 修復。
- Gate 4：若產生 GO recommendation，再由獨立 Reviewer 固定 candidate commit 審查。
- Gate 5：主線接受設計後，另開 implementation chain；本卡不整合 production code。
