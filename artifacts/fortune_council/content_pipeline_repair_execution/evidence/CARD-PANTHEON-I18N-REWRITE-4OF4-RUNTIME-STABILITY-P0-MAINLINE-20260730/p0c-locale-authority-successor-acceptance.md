---
id: CARD-PANTHEON-I18N-REWRITE-4OF4-RUNTIME-STABILITY-P0-MAINLINE-20260730-P0C-SUCCESSOR-ACCEPTANCE
status: LOCAL_ACCEPTED_EXTERNAL_AUTH_PENDING
type: mainline-acceptance-evidence
accepted_at: 2026-07-30 Asia/Taipei
---

# P0-C Locale Authority Successor Mainline Acceptance

## Root question

在不建立原 strict chain 的 Repair-3、不降低 locale quality gate 的前提下，重新
設計 ja／ko semantic-item authority，使純 ASCII 一般英文與未明列 topology
fail closed，同時保留自然日韓內容、合法日文純漢字與封閉 literal positives。

## Lineage

- Successor Implementation：
  `1f9b9359754d4f3959ee86afcb9d5c257605f9dd`
- Independent Review：
  `a5adb559e2f60ae5f8bd93183ec4aceaca7b78b7`
- Review verdict：`REVIEW_NO_GO`
- Blocking findings：
  - `LAS-REV-001` — P1 — tokenizer未驗證whole value。
  - `LAS-REV-002` — P1 — capitalization shape冒充authority。
- Repair-1：
  `1fbf58fa20ccfc54be1a433b0f6d039b2de6617d`
- Original Reviewer re-review：
  `ce50a911ab830602c158b74309020a91c63271c9`
- Re-review verdict：`RE_REVIEW_GO`
- Finding disposition：
  `LAS-REV-001`／`LAS-REV-002` 均 `CLOSED`
- Mainline merge：
  `63248a0b1c20e4975616cce722351247d165c8a0`

Implementation、Review與Repair各自使用正式可見 thread及隔離 worktree；
re-review沿用原Reviewer thread，未建立replacement。

## Accepted contract

- ASCII-only locale literal以anchored whole-value grammar判定。
- 未消費punctuation、separator、leading／trailing junk全部fail closed。
- standalone alphabetic authority不再只靠Title Case／UPPERCASE shape。
- 明列的`OpenAI`／`API`、bounded model code與number維持通過。
- `Strategy`、`SOURCE`、`Zorple`在ja／ko五類semantic fields全部拒絕。
- 自然日文／韓文、`実践方法`、混合目標語言內容中的
  `OpenAI`／`API`／`GPT-5`／`2026`維持通過。
- en行為與`P0C-REREV-001`、`P0C-REV-003..006`維持CLOSED。

## Mainline fresh verification

整合後執行：

```text
<shared-venv-python> -m pytest \
  <successor-independent-review-probes> \
  tests/test_agy_multilingual_pipeline.py \
  tests/test_agy_gemini_outbox.py \
  tests/test_agy_seo_copy_pipeline.py \
  tests/test_agy_content_publisher.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_gemini_v4_broker.py \
  tests/test_agy_gemini_reviewer_cutover.py -q
```

Result：`748 passed, 1 warning`。

另執行：

```text
<shared-venv-python> -m pytest tests/test_agy_gemini_transport_probe.py -q
```

Result：`15 passed`。

總計：`763 passed, 1 existing warning`。

另驗證：

- production compile：PASS
- changed-line debug scan：PASS
- mainline integration `git diff --check`：PASS
- Review／Repair direct parent與card blob：PASS
- changed-files／evidence boundary：PASS
- mainline worktree：clean

## Current state

- P0-A runtime identity：`LOCAL_ACCEPTED`
- P0-B transport／semantic budget separation：`LOCAL_ACCEPTED`
- P0-C locale-authority／native-outline repo implementation：
  `LOCAL_ACCEPTED`
- i18n-rewrite真實文章發布、live host與下一個scheduler週期：
  `PENDING_EXTERNAL_AUTH`

## Blocker

目前不再有未解repo內P0／P1。剩餘blocker是原卡明列的外部授權邊界：

- 尚未獲准push哪個exact branch／target ref；
- 尚未獲准對哪個既有deferred `fortune-0039` run執行哪個exact provider
  operation；
- 尚未獲准部署／publish與production `.work`變更；
- 尚未鎖定next scheduler／Publisher cycle觀察窗口。

## Next step

取得精確外部授權後，主線依序：

1. push已驗證mainline commit；
2. 部署immutable runtime；
3. 對唯一指定deferred run先做不含文章payload的capability／model probe；
4. 經Writer → deterministic gate → Reviewer → Publisher完成真實發布；
5. 驗證live URL、ledger／release／tag；
6. 觀察下一個scheduler／Publisher週期，證明不需人工同步runtime。

## Limits

- 本acceptance不等於push、deploy、provider成功或production ready。
- 未取得精確授權前，不呼叫provider、不讀寫production `.work`、不push、
  deploy或publish。
- 不降低deterministic、Reviewer、SEO、canonical、安全或publication gate。
