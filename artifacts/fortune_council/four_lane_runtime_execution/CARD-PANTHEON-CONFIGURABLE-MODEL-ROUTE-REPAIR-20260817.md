---
id: CARD-PANTHEON-CONFIGURABLE-MODEL-ROUTE-REPAIR-20260817
chain_id: PANTHEON-NEW-FLOW-PRODUCTION-PUBLISH-RECOVERY-20260817
role: implementation
cycle: 1
status: ready
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: production 四線共用模型路由、quota identity 與 installer manifest 的固定契約實作。
ownership:
  - config/**
  - scripts/agy_gemini_allocator.py
  - scripts/agy_gemini_outbox.py
  - scripts/agy_seo_copy_pipeline.py
  - scripts/install_agy_gemini_coordinator_launchd.sh
  - scripts/pantheon_content_runtime_manifest.py
  - tests/test_agy_gemini_allocator.py
  - tests/test_agy_gemini_outbox.py
  - tests/test_agy_gemini_coordinator.py
  - tests/test_agy_seo_copy_pipeline.py
  - tests/test_pantheon_content_runtime_manifest.py
  - artifacts/fortune_council/four_lane_runtime_execution/configurable_model_route_repair_20260817/**
forbidden_scope:
  - production runtime、queue、launchd、network、push、merge、tag
  - 文章生成、registry、sitemap、feed、redirects
  - 自動抓取 Gemini console quota、模型品質排名、UI
  - 建立第二個 Implementation、Reviewer 或 Repair task
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/configurable_model_route_repair_20260817/
---

# Configurable Model Route Repair

工作名稱 → 修復四線可設定模型路由
正在做什麼 → 用單一 versioned route config 取代 Python／installer 的特定模型 hardcode 與單一 fallback
現在狀態 → ready；未 activation 前只做 bootstrap

## P0 outcome

讓 new、rewrite、i18n-new、i18n-rewrite 四條 lane 共用同一模型路由契約；未來置換模型只需修改 route config、跑 deterministic preflight、promotion／reload，不改 Python。

## 正式初值

- Writer ordered route：
  1. `gemini-3.5-flash-lite`
  2. `gemini-3.5-flash`
  3. `gemini-2.5-flash`
- Reviewer ordered route：
  1. `gemini-3.1-flash-lite`
  2. `gemini-2.5-flash-lite`

四條 lane 共用以上 role route；同一時刻 Writer／Reviewer 必須是不同 exact model。

## Functional contract

1. 新增單一 versioned route config／manifest，至少表達 `writer`、`reviewer` ordered exact model IDs 與 schema version。
2. Python 不得再硬編碼本輪特定 Gemini model ID，也不得固定只有一個 fallback。
3. installer、coordinator、四 lane runner 與 Publisher／runtime manifest 的 relevant identity 必須讀同一 config，並保存同一 exact config digest；任何 missing／mismatch／drift fail closed。
4. config deterministic validation：安全 model ID、role route 非空、ordered list 內無重複、Writer／Reviewer 首順位不同、canonical digest 可重現；invalid schema／unsafe ID／duplicate／role collision fail closed。
5. quota block identity 固定為 `(credential slot, exact model)`；某 exact model 的 account-1/2/3 全部 `API_QUOTA` 後才走下一順位。
6. `API_RATE_LIMITED`、HTTP 429 transient、HTTP 503 只做既有 bounded retry／cooldown，不得觸發 model downgrade。
7. 每日 quota reset 後自動回到各 role ordered route 首順位。
8. 四 lane 使用相同 route config；不得各自 hardcode 或靜默混用 Writer／Reviewer role。
9. 保留現有 fail-closed production transaction、queue identity、manifest identity 與 activation barrier。

## Slice／blocking edge

- `SLICE-MODEL-ROUTE-CONFIG`（frontier）：schema、loader、canonical digest、invalid config gates。
- `SLICE-MODEL-ROUTE-ORDERED`（blocked by CONFIG）：ordered admission、per-model exhaustion、transient no-downgrade、daily reset。
- `SLICE-MODEL-ROUTE-RUNTIME`（blocked by ORDERED）：installer／coordinator／四 lane／manifest 共用 digest。
- Checkpoint（blocked by all slices）：targeted tests、受影響 suite、`git diff --check`、candidate receipt。

traces_to：`US-PUBLISH-RECOVERY-001`、`FR-PUBLISH-RECOVERY-001`、`SC-PUBLISH-RECOVERY-003`。

## TDD／驗證

先 RED、最小 GREEN；至少實證：

- 500-RPD model 位於各 role 首順位，20-RPD models 只作後順位。
- exact model 三 slots 全 `API_QUOTA` 才前進；已 blocked 中間 model 會跳過。
- 一個 Flash quota block 不影響 Flash-Lite admission。
- transient 429／503 不降級。
- daily reset 回首順位。
- 四 lanes 共用相同 config digest，Writer／Reviewer 不混角色。
- installer staged plist 與 runtime manifest 對 config path／digest 一致；exact model/config drift NO-GO。
- 既有 allocator、outbox、coordinator、pipeline、manifest 受影響測試與 `git diff --check`。

## 交付

- 回報 RED、GREEN、受影響 suite、candidate SHA、clean status、evidence path。
- 列出 config path、schema version、canonical digest、所有 consumer。
- 不得碰 production；主線另建唯一 Reviewer 並取得 GO 後才整合 main。
