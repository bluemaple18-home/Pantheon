---
id: CARD-CONTENT-WRITER-VNEXT-CANARY-ACTOR-PROVISIONING-001
status: ready
chain_id: CONTENT-WRITER-VNEXT-RUNTIME-ACTIVATION
role: implementation
cycle: 1
execution_line_id: WRITER-VNEXT-PRODUCTION-CANARY-001-RETRY-1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: blocker 與正式入口已固定；需嚴格處理 Git actor identity、runtime manifest、exact selector 與 fail-closed host 邊界，但無未解架構 fork。
traces_to:
  - SC-production-canary-readiness
  - SC-production-actor-identity
  - SC-exact-run-selector
depends_on:
  - CARD-CONTENT-WRITER-VNEXT-PRODUCTION-CANARY-001-RETRY-1@f00115a9a784f65c5a0ca1a31347f340700e8c36
---

# Writer vNext Canary Actor Provisioning

## 目標

新增 repo-owned、deterministic、fail-closed 的 Canary actor 準備入口，使後續主線能建立／驗證 exact-SHA actor root、Python runtime、空白 publisher state roots、runtime manifest，以及 `--exact-run-id`＋`--max-runs 1` 的單次 Publisher 執行計畫。

本卡只交付 source candidate 與 sandbox 證據；不得建立或改動真正 production actor、launchd、queue、state、tag、remote 或文章。

## 已確認 blocker

- Canary RETRY-1 唯讀 preflight：`BLOCKED / PRE_CANARY_PREFLIGHT`。
- 設定中的 `<repo-root>-publish-actor`、Python 與 publisher state root 不存在。
- 現有 Publisher plist 使用 `--max-runs 3`，未綁定 exact run，不能作 bounded Canary 執行線。
- readiness、remote lineage、credential metadata、provider CLI、容量與候選 payload其餘皆通過。

## 行為契約

1. 提供單一正式 CLI，分成唯讀 `plan/preflight` 與明示 `prepare`；預設必須零 mutation。
2. actor source 必須是完整 40 字元 SHA、為指定 remote/main 的 descendant，且 actor root 不得等於使用者主 checkout 或現有 task worktree。
3. `prepare` 只能建立指定空白 actor/runtime roots與 repo worktree；不得載入／卸載 launchd、執行模型、讀寫 production queue、建立 run 或發布內容。
4. runtime manifest 必須綁定 actor root、actor HEAD、Python executable、queue/state/log roots、owner UID 與 digest；漂移即 fail closed。
5. 產生或驗證的 Canary Publisher plan 必須包含單一 `--exact-run-id <id>`、`--max-runs 1`、deployment preflight、runtime manifest digest與 fixed actor SHA。
6. 禁止接受空／重複 exact run、相對／symlink escape path、dirty actor、錯 HEAD、錯 remote lineage、已含資料的 state root或現存不相容 plist。
7. retry 必須 idempotent；部分建立失敗保留 evidence並停止，不得刪除未知既有資料。

## 可改檔案

- `scripts/prepare_pantheon_canary_actor.py`（新檔）
- `scripts/pantheon_content_runtime_manifest.py`
- `scripts/install_agy_content_publisher_launchd.sh`
- `ops/launchd/com.pantheon.agy-content-publisher.plist.example`
- `tests/test_prepare_pantheon_canary_actor.py`（新檔）
- `tests/test_pantheon_content_runtime_manifest.py`
- `tests/test_agy_content_publisher.py`
- `docs/pantheon_deployment_workflow.md`
- `artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/canary_actor_provisioning_001/**`

實際 changed files 必須是上述最小子集；不得為填滿 allowlist 而修改。

## 禁止範圍

- 使用者主 checkout 與其 dirty files。
- `launchctl`、`~/Library/LaunchAgents/**`、既有 production plist／manifest／actor／queue／state／log。
- 模型 provider 呼叫、run 建立、Publisher transaction、tag、push、deploy、正式產文。
- ai-core、reservation DB、Codex global state、其他 task/worktree。
- 修改 Canary payload、article ID、locale、release version或既有 readiness evidence。

## TDD／驗證

1. RED：不存在 actor root與缺 exact selector時，正式 preflight 回明確 blocker。
2. GREEN：只用 temp Git repo／temp roots完成 plan→prepare→re-preflight，manifest與單次 Publisher plan完全綁定 fixed SHA／exact run。
3. 負向：dirty／錯 SHA／non-descendant／same checkout／symlink escape／state 非空／max-runs≠1／缺或重複 exact run／manifest digest drift／retry partial failure全數 fail closed。
4. 主機 no-op：測試與驗證前後 `launchctl`、正式 plist、production roots與 remote refs不得改變。
5. 必跑 targeted tests、相關 runtime manifest／Publisher tests、`py_compile`、shell syntax、JSON parse、`git diff --check`、changed-files allowlist。

## Evidence

寫入 `artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/canary_actor_provisioning_001/`：

- `red.txt`
- `green.txt`
- `negative-matrix.json`
- `host-noop.json`
- `changed-files.txt`
- `verification.md`

## 交付

- 單一 candidate commit SHA。
- 結論只可 `DELIVERED_CANDIDATE` 或具證據的 `BLOCKED`。
- 不得宣稱 production actor 已建立、Canary 已執行或原 preflight blocker 已關閉；須經獨立 Review、主線整合與後續正式 provisioning 後才能重跑 Canary。
