---
id: CHECKPOINT-A-REPAIR-1
title: 修復私有 E2E 自動來源與驗收證據
status: ready
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: repair
role_slot: repair
cycle: 1
generation: 1
thickness: standard
risk: medium
model: gpt-5.6-terra
reasoning: medium
model_reason: 兩個 finding 已固定且 allowlist 不變；使用既有唯一 Repair 責任線做 bounded 修復
parent_candidate: 0c19166855c2c5d50589b0cda5304daee81952bd
traces_to:
  - US-001
  - US-002
  - US-004
  - FR-012
  - SC-001
findings:
  - CHECKPOINT-A-P1-001
  - CHECKPOINT-A-P1-002
---

# CHECKPOINT-A-REPAIR-1｜修復私有 E2E 自動來源與驗收證據

## 任務五行卡

- 目標：修復 CHECKPOINT-A 候選未真正串接 APF-001 source campaign，並補齊 partial resume 與可保存 receipt。
- 可改：既有 coordinator 組合 seam、對應測試、專屬文件與 checkpoint receipt；不得擴大功能。
- 禁止：不得改 Publisher／multilingual production code，不得 publish、push、deploy、schedule、V9、SEO／GEO。
- 驗收：單一入口自行呼叫 APF-001 workset builder，deterministic 選出 new／rewrite 與 matching ja lanes；partial resume 不重做完成 lane。
- 證據：兩個 finding regression、完整 416-test suite、receipt、git diff --check、clean、單一 repair candidate。

## 固定 Findings

### CHECKPOINT-A-P1-001｜入口跳過 APF-001 自動來源

`execute_private_campaign_e2e` 目前要求 caller 先手工建立精確四 lane `workset`；測試也直接組 dict。這只串 APF-002／003，違反 CHECKPOINT-A「APF-001→003 單一全自動入口」與禁止人工逐篇觸發。

修復要求：公開 checkpoint 入口以 `repo_root / queue_root / state_root / campaign_version / locale` 呼叫既有 `build_campaign_dry_run_workset`；從完整結果 deterministic 選一個 new、一個 rewrite，並綁定相同 article identity 的 `i18n-new-ja`、`i18n-rewrite-ja`。不得另造 source scanner 或 queue。

### CHECKPOINT-A-P1-002｜resume 與 receipt 證據不足

現有測試只有完整成功後整體重跑，沒有 seeded partial state 的 resume；候選也沒有交付卡片指定的 checkpoint receipt path。

修復要求：新增 public-behavior regression，先保存一個完成 lane／中斷狀態，再由同一入口續接；已完成 Writer／Reviewer／translation 不得重做，最終仍為四 lane且無 duplicate。新增 `artifacts/fortune_council/content_writer_vnext_execution/checkpoint_a/verification_receipt.json`，內容只記可重現命令、結果、candidate/self、零外部動作，不得放本機絕對路徑。

## Allowlist

- scripts/agy_gemini_coordinator.py
- tests/test_agy_gemini_coordinator.py
- docs/pantheon_writer_vnext_auto_vertical_chain.md
- artifacts/fortune_council/content_writer_vnext_execution/checkpoint_a/**

## 驗證

1. RED→GREEN：測試必須證明 workset builder 被單一入口呼叫；caller 不傳手工 workset。
2. source 結果缺 lane、matching translation、identity 漂移或超出 checkpoint selection contract 時，在 Writer／Reviewer／collector 前 fail closed。
3. seeded partial resume：完成 lane call count 不增加，未完成 lane安全完成；queue/run 唯一。
4. 保留原 retry、translation rollback、capacity 與 published=0 assertions；補第三個 translation capacity negative。
5. `uv run pytest tests/test_agy_gemini_coordinator.py tests/test_agy_multilingual_pipeline.py tests/test_agy_content_publisher.py -q`，必須以可續接 PTY取得 exit 0。
6. `git diff --check`；worktree clean。

## 交付

- 回報 repair candidate SHA、changed paths、兩個 finding regression、完整 suite 與 receipt path。
- 明示未 publish、tag、push、deploy、schedule、production activation。
- 不得新增 finding、改 spec 或進 APF-004。
