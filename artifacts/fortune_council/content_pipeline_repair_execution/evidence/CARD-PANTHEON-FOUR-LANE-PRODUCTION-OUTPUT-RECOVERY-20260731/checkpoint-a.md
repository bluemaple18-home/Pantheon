# CHECKPOINT-A — Observation acceptance and repair slicing

## Status

```text
status: GO
scope: SLICE-OBSERVE-001 only
root_card_complete: false
candidate: 63979fa6e7b2ea88011011f1655e269013e65662
candidate_parent: de68b6b283493a3e9ca5f80286c682cb7846735e
```

## Evidence

- Candidate parent精確等於已凍結的 `v0.3.183` commit。
- Candidate worktree clean。
- Candidate 僅新增 `baseline.md`、`failure-matrix.md`、
  `observe-verification.md` 三份 allowlist evidence，共 637 行。
- `git diff --check de68b6b..63979fa` 通過。
- evidence 無單機絕對路徑、API key、credential、cookie、token 或 raw provider
  output。
- 主線另以 CodeGraph 核對 broker schema diagnostics、coordinator selection、
  Publisher retry／defer 與 multilingual validation seams。

## Acceptance mapping

| 條件 | 判定 | 證據 |
|---|---|---|
| 四 lane fresh baseline | GO | `baseline.md` 08:39–08:44 時間窗 |
| 每 lane success 或 red-capable failure | GO | new schema RED、rewrite release-gate RED、i18n-new hydration RED、i18n-rewrite expected quality RED |
| 八層 failure matrix | GO | `failure-matrix.md` |
| eligible backlog 與累積 count 分離 | GO | rewrite 179 unattempted vs current blocked、各 lane queue snapshot |
| 無 provider／production mutation | GO | `observe-verification.md` scope／command receipt |
| only allowlist files | GO | candidate diff |
| production 可發布 | BLOCKED | source `de68b6b…` 與 actor `dde0cd2…` SHA 不一致 |

## Facts and interpretation

1. `new` 在 v0.3.183 後有 52 筆 provider `SUCCESS`，但全部是
   `SCHEMA_MISMATCH`；本輪根因不是 credential outage。
2. `rewrite` 有 179 筆未嘗試 inventory，另有 5 筆 clean-approved candidate；
   coordinator `publish_ready_first` 與 Publisher exhausted retry selection
   形成 head-of-line deadlock。
3. `i18n-new` transport 與 response schema 成功，之後能在純記憶體 hydration
   重現 `locale plan coverage mapping differs for article-01`。
4. `i18n-rewrite` candidate persistence 成功，但 reviewer 以
   `NON_NATIVE_SEARCH_INTENT`、`AI_TEMPLATE_STYLE` 正確 fail-closed；修復不得
   放寬母語品質 gate。
5. runtime digest 與 installed contract 相符，但 actor SHA 落後 source；這是
   canary／發布 blocker，不否定離線 red→green repair 可在凍結 source 上進行。

## Accepted repair slices

### A2 — New output contract repair

- traces_to: `FR-4LANE-003`、`FR-4LANE-007`、`SC-4LANE-003`
- ownership: new prompt／normalization／closed schema classification
- code owner:
  - `scripts/agy_seo_copy_pipeline.py`
  - `scripts/agy_gemini_runner.py`
  - 對應的 new／outbox tests
- blocking edge: 本 Checkpoint A
- acceptance: red→green；不放寬 min／max；deterministic mismatch 不輪替
  credential；bounded repair／retry。

### A3 — Rewrite eligibility deadlock repair

- traces_to: `FR-4LANE-005`、`FR-4LANE-007`、`FR-4LANE-008`
- ownership: coordinator／Publisher rewrite eligibility single terminal state
- code owner:
  - `scripts/agy_gemini_coordinator.py`
  - `scripts/agy_content_publisher.py`
  - 對應 coordinator／Publisher tests
- blocking edge: 本 Checkpoint A
- acceptance: exhausted clean-approved candidate 不與 `publish_ready_first`
  互鎖；不重設 production retry、不新增無限重試。

### A4 — Multilingual contract and native-quality repair

- traces_to: `FR-4LANE-004`、`FR-4LANE-006`、`FR-4LANE-007`
- ownership: `agy_multilingual_pipeline.py` 唯一 owner；同一卡垂直驗證
  i18n-new hydration 與 i18n-rewrite quality liveness
- code owner:
  - `scripts/agy_multilingual_pipeline.py`
  - `tests/test_agy_multilingual_pipeline.py`
- blocking edge: 本 Checkpoint A
- acceptance: coverage mapping red→green；i18n-rewrite candidate path可驗；
  `NON_NATIVE_SEARCH_INTENT`／`AI_TEMPLATE_STYLE` 仍 fail-closed。

### A1 — Runtime actor identity alignment

- traces_to: `SC-4LANE-004`
- status: `PENDING_AUTHORIZATION`
- reason: 需要 deploy／reload production mutation；目前未獲授權。
- blocking edge: strict review GO 之前不阻擋離線 repair；production canary
  之前必須完成。

## Frontier

可立即平行開工：`A2`、`A3`、`A4`。三張卡 code allowlist 互斥。

不可開工：`A1`、strict review、production canary。

## Remaining risk

- Observation dependency preparation的 Python／Node sync 受 sandbox cache／DNS
  限制；這不影響唯讀 diagnosis acceptance，但 repair candidate 必須各自建立可
  執行測試環境並跑受影響 tests。
- Background LaunchAgent 可能繼續產生 runtime artifacts；所有 count 僅代表
  evidence 時間窗。
- 根卡仍未達 `SC-4LANE-001`～`SC-4LANE-005`。
