---
id: CARD-AI-CORE-UV-CACHE-EXTERNAL-VOLUME-PERMISSION-REPORT-20260820
chain_id: AI-CORE-UV-CACHE-PERMISSION-20260820
role: report
cycle: 1
status: ready
type: environment_permission_report
thickness: minimal
risk: low
owner: ai-core
requester: Pantheon
production_mutation_authorized: false
config_mutation_authorized: false
---

# Ai Core：外接硬碟 UV cache 權限回報

## 工作名稱 → 正在做什麼 → 現在狀態

外接硬碟 UV cache 權限定性 → 查明 Codex sandbox 為何無法讀取共享 cache → `READY FOR AI-CORE READ-ONLY TRIAGE`

## Root Question

Codex 正式 task 內的 `UV_CACHE_DIR` 為何指向外接硬碟共享 cache，且 sandbox 無法讀取其中的 sdist Git metadata？這是近期系統／Codex 更新造成、既有環境注入契約，還是 Ai Core 本機設定漂移？

## 目前 blocker

Pantheon G8 current readiness 正式 task 執行唯一生成命令時，`uv` 在 Python generator 啟動前失敗：

```text
error: failed to open file <external-volume-root>/Caches/uv/sdists-v9/.git: Operation not permitted (os error 1)
```

因此本輪沒有生成 current capability／capacity receipt，沒有 candidate commit，也沒有 production mutation。

## 已確認事實

1. 正式 task runtime 具有 `CODEX_SANDBOX=seatbelt` 與 `CODEX_SANDBOX_NETWORK_DISABLED=1`。
2. runtime environment 注入 `UV_CACHE_DIR=<external-volume-root>/Caches/uv`、`UV_LINK_MODE=copy`。
3. `<ai-core-root>/config/toolchain_paths.sh` 與 `<ai-core-root>/config/ai_core_env.sh` 沒有設定 `UV_CACHE_DIR`；目前來源仍待定位。
4. 失敗點位於 `uv` cache 存取，尚未進入 Pantheon receipt generator，不能判定為四線 source、capacity 或 Publisher 邏輯故障。
5. Pantheon 在 2026-07-29 與 2026-07-31 的既有 evidence 已記錄同類「sandbox 不允許共用 uv cache」失敗，因此目前沒有證據支持「2026-08-20 最近一次系統更新才首次造成」。
6. 本機實際 mount path 為 local-only 診斷證據，不應成為跨機照抄的設定或命令基準。

## 請 Ai Core 回答

1. `UV_CACHE_DIR` 的 canonical owner 與實際注入來源是什麼：Codex Desktop、shell／launch environment、Ai Core local env、wrapper，或其他控制面？
2. Codex seatbelt sandbox 對外接 volume 的預期權限契約是什麼？目前行為是設計如此、設定漂移，還是 regression？
3. 是否有可驗證的更新紀錄、設定 diff 或版本證據，能支持或排除「近期系統／Codex 更新造成」？不得只憑時間相近推定。
4. canonical 修法應為哪一種：
   - 所有 sandbox task 預設使用 task-local／workspace-local uv cache；
   - Ai Core 提供 sandbox-safe shared cache；
   - 明確授權外部 runtime 讀取外接 cache；
   - 其他具體且 fail-closed 的方案。
5. 若採 task-local cache，應在哪一層宣告，才能避免每張派工卡重複踩坑，同時不污染 repo、artifact ownership 或跨機契約？
6. 修法如何以最小 red／green reproduction 驗證，並防止後續正式 task 在 generator／pytest 啟動前再次被 cache 權限阻斷？

## In Scope

- 唯讀定位 `UV_CACHE_DIR` 注入來源與 ownership。
- 核對 Codex sandbox、外接 volume 與 Ai Core toolchain 的權限契約。
- 提供可證偽的根因判定、canonical 修復建議與最小驗證方式。
- 判斷此問題應由 Ai Core 全域處理，或由個別 task 明確採用 task-local cache。

## Out of Scope

- 修改 Pantheon source、tests、receipt generator、四線流程或 production。
- 修改全域 Ai Core、Codex、shell、外接硬碟 ACL／privacy 設定。
- 在原 G8 task 重跑唯一生成命令。
- 為取得成功結果而降低 sandbox、capacity、readiness 或 fail-closed 門檻。
- 把既有 tracked READY summary 當作 current evidence。

## 驗收條件

- `SC-001`：指出 `UV_CACHE_DIR` 的實際注入來源與 canonical owner，附 repo-relative／控制面證據位置。
- `SC-002`：以證據回答「是否由近期更新造成」；無證據時明確標示 unknown，不得猜測。
- `SC-003`：明確區分 environment／permission blocker 與 Pantheon source blocker。
- `SC-004`：提出一個建議主方案與一個受控替代方案，列出權限、可移植性、cache reuse 與污染風險。
- `SC-005`：提供不觸碰 production 的最小 red／green 驗證命令或 harness，且一次只改一個變數。
- `SC-006`：若建議修改任何全域設定，先回報 exact target、影響面、rollback 與所需授權；本卡本身不授權修改。

## Evidence

- `handoff_20260820_g8_current_readiness_uv_cache_blocker.md`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-repair-1-20260729/reproduction.md`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-repair-2-20260729/reproduction.md`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731/observe-verification.md`
- `<ai-core-root>/config/toolchain_paths.sh`
- `<ai-core-root>/config/ai_core_env.sh`

## 停止條件

- 找不到注入來源時，保存已查範圍與證據，回 `BLOCKED / OWNER UNKNOWN`，不得直接改全域環境。
- 需要修改外接硬碟權限、macOS privacy、Codex sandbox 或 Ai Core 全域設定時，先提出變更提案並等待使用者明確授權。
- 同一假說連續三次無法取得新證據即停止，不以反覆重跑 Pantheon generator 代替診斷。

## 回報格式

1. Verdict：`CONFIGURATION / SANDBOX CONTRACT / UPDATE REGRESSION / UNKNOWN`
2. Injection source 與 canonical owner
3. 支持與排除證據
4. 建議主方案、替代方案與風險
5. 最小 red／green 驗證結果
6. 是否需要使用者另行授權變更
