---
card_id: CARD-PANTHEON-I18N-REWRITE-4OF4-RUNTIME-TRANSPORT-IMPLEMENTATION-20260730
chain_id: pantheon-i18n-rewrite-4of4-runtime-stability-p0-20260730
parent_card_id: CARD-PANTHEON-I18N-REWRITE-4OF4-RUNTIME-STABILITY-P0-MAINLINE-20260730
role: implementation
cycle: 1
status: CARD_DRAFTED
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: Publisher runtime/content identity 與 provider retry budget 橫跨發布、翻譯與 outbox 邊界；錯誤會阻斷所有 production 內容線或造成重複副作用，需 strict 實作與獨立 Review。
project_id: local-0020d4379451d545eb08362962f1def0
repo_identity: github.com/bluemaple18-home/Pantheon
required_parent_base_ref: origin/main
required_parent_base_sha: 0e9870764b193d5d45e131c8b7ba284ab65a2862
ownership: P0-A Publisher runtime identity and P0-B provider transport retry semantics
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-RUNTIME-TRANSPORT-IMPLEMENTATION-20260730/
created_at: 2026-07-30 Asia/Taipei
---

# Pantheon Runtime／Transport P0 Implementation

## Root question

如何在不降低任何內容品質或發布閘門的前提下：

1. 讓 Publisher 使用 immutable runtime identity 執行最新 content head，避免
   content-only `origin/main` 前進後要求 actor checkout 或重裝 LaunchAgent。
2. 讓 provider transport／payload failure 使用獨立、bounded、可觀測且
   idempotent 的 retry budget，未取得 schema-valid payload前不消耗 semantic repair。

本卡不負責真實 provider call、正式發布、push、deploy 或 production scheduler
驗收；上述外部動作留在 P0 主線取得精確授權後執行。

## Known source state

- `scripts/agy_content_publisher.py` 已有 `TRANSACTION_RUNTIME_PATHS`、
  `deployment_preflight()` 與 `_assert_transaction_runtime_matches()`。
- 現有 preflight 允許 descendant content-only `origin/main`，並以 runtime paths
  阻擋 runtime drift；但 deployment contract 仍以 actor commit SHA 作主要 runtime
  identity，需補上封閉 manifest／digest 契約及完整 fail-closed 測試。
- `scripts/agy_gemini_outbox.py` 的 transport retry 目前只把
  `JSONDecodeError` 視為 retryable，且 retry namespace 加上 `-rN`，會改變 request
  identity。
- `scripts/agy_multilingual_pipeline.py::run_writer_reviewer()` 以 attempt loop 表達
  semantic repair；transport／schema-invalid payload 必須在進入下一 semantic
  attempt 前被明確分類並停止或由獨立 transport budget處理。
- CodeGraph prepare 因 sandbox cache／離線 pnpm 依賴失敗；source map 已依規則降級，
  以限域 `rg` 與原始碼確認上述 entry points。不得把此環境缺口改寫成產品 blocker。

## Traceability and slices

### SC-001 — Runtime identity

Content-only main advance 後，舊 actor 的 runtime manifest／digest仍有效；runtime
path bytes、manifest 或 digest 漂移時 deterministic fail closed。

### SC-002 — Transport budget

`CLI_NONZERO`、auth、quota、network、model unavailable、malformed／schema error
均有封閉分類與 operation receipt；schema-valid payload前不消耗 semantic repair。

### SC-003 — Idempotency and side effects

同一 logical request 的 bounded transport retry 保持同一 request identity，且失敗
不建立 candidate／queue approval／apply／publish side effects。

### SL-RUNTIME-IDENTITY

- `traces_to: [SC-001, SC-003]`
- 先寫 public-behavior RED tests，再做最小 runtime manifest／digest修復。
- 驗證 content-only advance、runtime change、manifest/digest mismatch，以及既有
  ledger／tag／push ordering不回歸。

### SL-TRANSPORT-BUDGET

- `traces_to: [SC-002, SC-003]`
- 先寫 public-behavior RED tests，再做最小 failure taxonomy、transport budget 與
  request identity修復。
- capability／model probe 只能使用 sanitized、無文章 payload的 request；本卡只實作
  與測試契約，不呼叫真實 provider。

Blocking edge：兩個 slice 都完成且 targeted suites 全綠後，才能形成單一
implementation candidate；P0-C production publication仍由主線持有。

## Allowlist

- `scripts/agy_content_publisher.py`
- `scripts/agy_seo_copy_pipeline.py`
- `scripts/agy_multilingual_pipeline.py`
- `scripts/agy_gemini_outbox.py`
- `scripts/agy_gemini_runner.py`
- `scripts/agy_gemini_transport_probe.py`
- `scripts/install_agy_content_publisher_launchd.sh` 與直接相關 LaunchAgent template，
  但僅在 runtime manifest契約確實需要時
- 直接受影響的 `tests/**`
- 本卡專屬 evidence／handoff

## Forbidden scope

- 不降低 deterministic、Reviewer、SEO、canonical、安全或 publication gate。
- 不手改 production candidate、review、queue、approval、apply、publish、ledger。
- 不修改 frontend、產品 UI、article registry、sitemap、feed 或 redirects。
- 不呼叫 provider、不 push、不 deploy、不安裝或重裝 LaunchAgent。
- 不 force push、不改寫歷史、不建立 replacement／重複 mainline卡。
- 不使用 hidden sub-agent；不得自行建立 Review 或 Repair task。

## Required workflow

1. Activation 前只做 formal task／project／worktree／HEAD／clean bootstrap。
2. Activation 後跑 capability preflight；CodeGraph若仍無法 prepare，記錄
   `CONTEXT_DEGRADED` 後只限域讀取本卡 entry points。
3. 依 `SL-RUNTIME-IDENTITY` 與 `SL-TRANSPORT-BUDGET` 各自執行
   RED → GREEN → targeted verification。
4. 跑受影響 publisher、SEO、multilingual、outbox、runner／probe suites及
   `git diff --check`。
5. changed files 必須完全落在 allowlist；保存完整 commands／results／diff summary。
6. 只交付單一 candidate commit SHA 與 evidence；狀態只能是
   `DELIVERED_CANDIDATE`，不得宣稱 ACCEPTED／INTEGRATED／CLOSED。

## Acceptance

- `SC-001`、`SC-002`、`SC-003` 均有 red-capable public behavior tests。
- content-only commit可通過下一輪；runtime path／manifest／digest drift拒絕舊 actor。
- transport failure有明確 closed category、bounded retry與不變 request identity。
- provider payload未通過 schema前，semantic repair generation／budget不前進。
- transport failure不留下 candidate、approval、apply、publish或ledger副作用。
- affected targeted、publisher、SEO、multilingual、outbox與probe suites全綠。
- `git diff --check` PASS；candidate commit單一且可由主線獨立 Review。

## Delivery format

- Candidate commit SHA
- Changed files
- RED evidence
- GREEN／full-suite commands與結果
- `git diff --check`結果
- Remaining risks與未執行的 production actions
