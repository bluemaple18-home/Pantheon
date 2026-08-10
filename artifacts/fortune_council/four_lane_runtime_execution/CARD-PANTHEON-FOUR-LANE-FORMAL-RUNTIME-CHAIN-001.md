---
card_id: CARD-PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN-001
status: RUNNING
execution_authorized: true
production_authorized: false
chain_id: PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN
role: implementation
cycle: 1
required_base_ref: codex/four-lane-formal-runtime-source-20260810
required_base_sha: f31ef017170c69543528708fd1314dc87ff7528a
formal_thread_id: 019fea5c-d188-7ed3-a669-315b6aed0952
dispatch_key: v1:b251b8a0fec688b8074a4c26b61bedeff95c837d8a9189efa1f2797653c769cc
activation_status: BOUND
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 跨 coordinator、四個 lane、publisher、capacity guard 的正式 runtime 核心重構，涉及身份一致性、啟動 barrier 與 rollback；錯誤會同時影響四軌，需用 Sol high 做單一嚴格實作。
ownership: 4lan 正式 runtime 串接、每輪身份驗證、七服務啟動 barrier 與可重現驗證
traces_to:
  - FR-001
  - FR-002
  - FR-003
  - SC-001
  - SC-002
  - SC-003
  - SC-004
allowlist:
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN-001.md
  - scripts/agy_content_publisher.py
  - scripts/agy_gemini_coordinator.py
  - scripts/agy_gemini_runner.py
  - scripts/install_agy_content_publisher_launchd.sh
  - scripts/install_agy_gemini_coordinator_launchd.sh
  - scripts/install_pantheon_content_capacity_guard_launchd.sh
  - scripts/pantheon_content_actor_recovery.py
  - scripts/pantheon_content_capability_adapter.py
  - scripts/pantheon_content_capability_probe.py
  - scripts/pantheon_content_capacity_guard.py
  - scripts/pantheon_content_runtime_manifest.py
  - ops/launchd/com.pantheon.agy-content-publisher.plist.example
  - ops/launchd/com.pantheon.agy-gemini-coordinator.plist.example
  - ops/launchd/com.pantheon.agy-gemini-lane.plist.example
  - ops/launchd/com.pantheon.content-capacity-guard.plist.example
  - tests/test_agy_content_publisher.py
  - tests/test_agy_gemini_coordinator.py
  - tests/test_agy_gemini_runner.py
  - tests/test_pantheon_content_capability_probe.py
  - tests/test_pantheon_content_capacity_guard.py
  - tests/test_pantheon_content_runtime_manifest.py
  - artifacts/fortune_council/four_lane_runtime_execution/evidence/formal_runtime_chain_001/**
forbidden_scope:
  - Writer vNext 契約、prompt、內容政策、SEO metadata、Schema、前端
  - production queue、正式文章、正式發布、tag、push、deploy、launchctl 安裝或服務重啟
  - merge 舊 4lan repair/review branch
  - 第二套 queue、lock、approval、publisher 或 control plane
  - 以模擬器、手寫 PASS receipt、mock stage result 代替正式實作呼叫
---

# 4lan 真實 Runtime 串接重構

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：4lan 真實 Runtime 串接重構
- 正在做什麼：把正式 coordinator → 四個 lane → publisher → capacity guard 接進同一條可驗證執行鏈，補齊每輪身份驗證與七服務啟動 barrier。
- 現在狀態：READY_FOR_DISPATCH；production 仍為 NO-GO。

## 為什麼是新 root chain

舊鏈 final review 已判定 `REVIEW_NO_GO / BLOCKED`。本卡不是 Repair-3，也不得把 Repair-2 視為完成證據。只以 `f31ef017...` 作來源基線，保留已關閉的共用修正：四軌拒絕 `new-only`、容量未知 fail-closed、逐服務 stop-loss 確認、actor recovery runtime provision。所有被本卡碰到的行為仍須重新驗證。

## 根問題

在完全隔離、無正式外部副作用的測試環境中，是否能證明真正的：

`coordinator → new / rewrite / i18n-new / i18n-rewrite → publisher → capacity guard`

且七個正式服務在每次工作前使用同一份 runtime identity，只有 7/7 ready 才開始碰 queue？

&gt; 「七個服務」是 coordinator、四個 lane、publisher、capacity guard。
&gt; 「七個生命週期步驟」是 create、run、select、publish、transaction、tag、push；兩者不得混為一談。

## 必做需求

### FR-001 正式實作鏈，不接受模擬成功

1. Capability harness 必須 import／呼叫 production 實際使用的公開入口或 CLI，不得複製其結果。
2. 可在暫存 root 與隔離 provider boundary 使用 fixture，但 coordinator、lane runner、publisher validation／transaction dry-run、capacity guard 必須走正式程式碼路徑。
3. 每一步證據至少包含：correlation ID、實際入口、輸入雜湊、輸出雜湊、return code、runtime identity digest。
4. correlation ID 由 coordinator 建立，必須一路保留到 lane、publisher、guard 與 transaction evidence。
5. `pantheon_content_capability_adapter.py` 只能刪除或收斂為薄呼叫器；不得再成為另一個結果模擬器或權威來源。
6. tag／push 只能驗證正式入口的 fail-closed dry-run，不得寫 git remote 或正式 repo。

### FR-002 七服務每輪身份一致

建立單一版本化 runtime identity contract，至少包含：

- manifest digest
- queue root
- state root
- actor／service identity
- code 或 runtime digest
- config version／generation

coordinator、四個 lane、publisher、capacity guard 每次 tick 都必須在第一次 queue/state read/write 前驗證；publisher 在任何發布或 transaction mutation 前再驗一次。任何缺值或不一致均須 fail-closed，且證明 queue/state 尚未被修改。安裝時驗證不能取代 runtime 驗證。

### FR-003 7/7 ready 才放行，rollback 要核對實際舊身份

1. 啟動分成「配置／等待」與「原子放行」兩階段。
2. 七服務各自提交帶 generation 與 identity digest 的 readiness acknowledgement。
3. 少於 7/7、任一 identity 不同、任一服務讀不到 manifest 時，barrier 保持關閉；任何 lane 都不得碰 queue。
4. 只有 activation owner 驗證 7/7 完整一致後，才可原子釋放該 generation 的 barrier；服務在 I/O 前仍要重驗 generation。
5. activation 失敗時，rollback 必須核對七服務實際載入的舊 control-plane identity，而不是只核對設定檔；核對失敗明確回 `ROLLBACK_FAILED`，不得宣稱恢復成功。

## 成功與負向情境

- SC-001：隔離環境正向走過正式 coordinator、四個 lane、publisher、guard，產生同一 correlation chain；沒有 network、production queue、tag、push 或 deploy 副作用。
- SC-002：七個服務任一個 identity mismatch，均在第一次 queue/state mutation 前 fail-closed。
- SC-003：只有 6/7 ready、服務提早啟動或 generation 過期時，barrier 不釋放且 queue/state 無變化。
- SC-004：rollback 實際身份不等於預期舊 identity 時回 `ROLLBACK_FAILED`；完整一致時才回復成功。

## 實作限制

- 先閱讀舊 final review 與 `f31ef017...` diff，但不得修改舊 review/evidence。
- 不要新增新的固定流程模板；本卡只處理 runtime 邊界。
- 若正式 production 入口根本不存在，應在 allowlist 內建立最小可重用入口；不得用測試專用平行實作冒充。
- 若必要變更超出 allowlist，停止並列出「檔案、理由、最小範圍」，不得自行擴張。
- 不得碰主工作區使用者既有 dirty files；只在本卡獨立 worktree 工作。
- 禁止 merge、push、deploy、production canary 或 launchctl mutation。

## 必跑驗證

1. 針對 FR-001～FR-003 的正向及負向 deterministic tests。
2. 既有 4lan、publisher、capacity、runtime manifest 受影響測試。
3. repository 全測試；若有與本卡無關的既有失敗，附完整分類與可重現指令，不得隱藏。
4. 所有 shell：`bash -n`；所有 plist：`plutil -lint`。
5. `git diff --check`。
6. 產出 evidence：正式入口呼叫 trace、七服務 identity matrix、barrier 6/7 與 7/7 matrix、rollback 正負例、測試 receipt。

## 交付契約

只交付候選 commit，不 merge。回報必須包含：

- candidate commit SHA 與 `git status --short`
- allowlist 內實際變更檔案
- FR／SC 對應的測試與 evidence 路徑
- 是否仍存在 simulator-only、identity split-brain、early barrier release
- targeted／full suite／bash／plist／diff-check 結果
- 唯一結論：`CANDIDATE_READY_FOR_REVIEW` 或 `BLOCKED`，不可宣稱 production ready

完成候選後停下，等主任務另派獨立嚴格 review。
