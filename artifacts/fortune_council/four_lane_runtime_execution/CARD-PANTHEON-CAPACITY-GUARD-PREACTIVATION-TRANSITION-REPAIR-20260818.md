---
id: CARD-PANTHEON-CAPACITY-GUARD-PREACTIVATION-TRANSITION-REPAIR-20260818
chain_id: PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-20260818
parent_card_id: CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-PRODUCTION-CANARY-20260818
role: repair
cycle: 1
status: ready
type: repair
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
model_reason: Production capacity fail-closed 與 LaunchAgent 過渡期契約交界；需固定邊界修復，避免用 5.6，採 GPT-5.5 high。
base_source_sha: 2e8d4776725f75208ebf49d12a48924f538ab031
blocked_canary_evidence_sha: 7d4030608be8c36ca68b57d0a121277bec62ec09
g5_source_sha: 35cfdd52739f3e2896bf151ed6434a5e6d6ab95e
g5_blocked_canary_evidence_sha: 29f69e9e237ad94a44d3c86baac6f39e572b410e
ownership:
  - scripts/install_pantheon_content_capacity_guard_launchd.sh
  - scripts/pantheon_content_capacity_guard.py
  - tests/test_pantheon_content_capacity_guard.py
  - tests/test_install_pantheon_content_capacity_guard_launchd.py
  - .work/CARD-PANTHEON-CAPACITY-GUARD-PREACTIVATION-TRANSITION-REPAIR-20260818/**
forbidden_scope:
  - production activation、runtime promotion、LaunchAgent reload、發文、transaction、tag、push
  - 改 Publisher selection、queue、Writer、lane、文章、prerender 或其他六服務功能
  - 接受任意 loaded/no-PID 服務、略過容量閘門、把 unknown 改判 PASS
  - 手改 production plist、receipt、manifest 或 barrier
verification:
  - RED 重現：新版 manifest 已 promotion，但舊 activation-only Publisher 仍 loaded/no-PID，capacity installer stage 被循環鎖死
  - GREEN 僅允許具有完整舊 activation-only live identity 與新 manifest/generation/digest 證據的 preactivation transition
  - stale barrier、錯 generation/digest、normal/malformed live plist、缺 service identity 全部在 launchctl mutation 前 NO-GO
  - stage 成功不得執行 bootout/bootstrap，不得啟動 Publisher
  - 受影響 pytest、bash -n、git diff --check 全過
evidence_path: .work/CARD-PANTHEON-CAPACITY-GUARD-PREACTIVATION-TRANSITION-REPAIR-20260818/
---

# Capacity Guard preactivation transition Repair

## 工作名稱 → 正在做什麼 → 現在狀態

修 Capacity Guard 過渡期循環鎖死 → 建立限域、fail-closed transition contract → `READY / REPAIR-1`

## Root Question

如何讓 capacity guard installer 在「新版 runtime manifest 已 promotion、舊 activation-only LaunchAgent 尚未換代且 loaded/no-PID」時安全完成純 staging，同時不放寬正常 runtime 的 RSS/PID 容量驗證？

## 固定事實

- Production canary source：`2e8d4776725f75208ebf49d12a48924f538ab031`。
- G3、G4 都在 capacity guard installer preflight 失敗：`rss_telemetry_unknown / loaded_service_pid_missing:com.pantheon.agy-content-publisher`。
- G4 已把 manifest 校正為 activation-only identity；相同 blocker 仍存在，因此「manifest target identity 單點錯誤」假說已推翻。
- 七個舊 live labels 均 loaded、無 PID、status 78；Publisher 尚未啟動。
- Production mutation：publish/transaction/tag/public artifact 全為 0。
- G4 evidence commit：`7d4030608be8c36ca68b57d0a121277bec62ec09`。

## G5 follow-up 固定事實

- G5 source/main/origin：`35cfdd52739f3e2896bf151ed6434a5e6d6ab95e`。
- Promotion 已 `COMMITTED`；final manifest digest：`46c37d3440d5938a1022b99dec8779ecc02168ba0c00fd7c05418fc4191912ac`。
- G5 identity：`gate2-actor:35cfdd52739f3e2896bf151ed6434a5e6d6ab95e:activation-only`。
- G5 generation：`g12-35cfdd5273-20260818T120632Z`。
- G5 actual `config_version`：`formal-runtime-v3-model-route-v1`。
- G5 blocker：`preactivation manifest mismatch`，隨後仍是 `rss_telemetry_unknown / loaded_service_pid_missing:com.pantheon.agy-content-publisher`。
- G5 stage topology：六個新 staged plists 與 Publisher exact markers 已存在，capacity guard 第七張 staged plist 尚未寫入；七個舊 live activation-only plists 仍 loaded/no-PID。
- G5 evidence commit：`29f69e9e237ad94a44d3c86baac6f39e572b410e`。

## 執行契約

1. 先讀 `AGENTS.md`、本卡、G4 evidence commit；BOOTSTRAP_ONLY 時只核對契約，不改檔。
2. 啟動後先建立最小 RED fixture，精確模擬 promoted manifest + 舊 activation-only loaded/no-PID live plist。
3. 找到最小 source seam。偏好明確的 preactivation/stage contract；不得在一般 preflight 中吞掉 missing PID。
4. transition 必須綁定新 manifest identity/generation/digest，以及舊 live plist 的完整 activation-only inert shape；證據不足即 NO-GO。
5. installer 純 stage 成功不得呼叫 `launchctl bootout/bootstrap/kickstart`，不得啟動任何服務。
6. 補負向測試：stale barrier、wrong generation/digest、normal/malformed live plist、missing identity、unknown service。
7. 跑受影響 tests、既有 capacity/runtime manifest 回歸、`bash -n`、`git diff --check`。
8. 交付 candidate SHA、changed files、RED/GREEN、負向證據、production mutation=`0`、evidence path。

## 停損

- 同一 blocker 本次再失敗即停止，不做第三種補丁。
- 若安全修復必須移除容量閘門、接受 unknown/no-PID 或改 production runtime，回 `BLOCKED / UNSAFE_SCOPE_EXPANSION`。
- Repair 不得自稱 GO；完成後必須開獨立 Reviewer 卡。
