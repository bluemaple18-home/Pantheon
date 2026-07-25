---
card_id: CARD-CONTENT-GEMINI-V4-AUTH-HARDENING-001
chain_id: CONTENT-GEMINI-V4-MAINLINE-001
status: READY_FOR_REVIEW
ownership: v4_auth_hardening_only
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
base_candidate: 3cb36a175146d217346609b2c54d59d2eed3c5fd
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_001/auth-hardening-001/
---

# Gemini V4 authentication hardening

## Root question

在不破壞已通過 Review 與真實 canary 的 structured transport、ledger、
exactly-once accounting、no-retry、no-redirect與fail-closed契約下，確認現有
API key風險，並建立可長期遷移至正式OAuth／ADC的最小邊界。

## Locked facts

- Structured code candidate：
  `df6a33a8ce4af784ca6bfe6c2453de6eb7355f94`
- Canary evidence commit：
  `3cb36a175146d217346609b2c54d59d2eed3c5fd`
- 獨立 Review：`GO`
- Affected suites：`224 passed`
- Real structured canary：`COMPLETE/1/SUCCESS/VALID`
- 現有三把Gemini key來自owner-only檔案；canary只使用第一把，沒有保存、
  輸出、輪替或重送credential。
- 目前本機沒有active gcloud account、configured project或ADC；
  `google-auth`也不在專案runtime。
- `AIza...`前綴不足以判斷standard key或authorization key；沒有Google
  control-plane identity時不得猜測。

## Requirements

- `AUTH-001`：短期保留已驗證的owner-only API key transport，不改request
  body、schema projection、provider response parsing或model allowlist。
- `AUTH-002`：不得讀取／代理agy或Gemini CLI私有OAuth session。
- `AUTH-003`：不得在argv、environment、evidence或log保存API key、access
  token、refresh token或OAuth client secret。
- `AUTH-004`：未具備正式project、identity與runtime dependency前，不得宣稱
  ADC可用或切換production認證。
- `AUTH-005`：未來ADC只可替換HTTP Authorization header來源；model POST
  仍維持一次、禁止retry／redirect／fallback。
- `AUTH-006`：Google key政策期限與現有key型別必須形成明確release blocker；
  無法確認時維持`UNKNOWN`，不得推論。

## Scope

允許：

- 本卡與 `auth-hardening-001/` evidence
- `docs/pantheon_gemini_reviewer_v4_architecture.md`
- `docs/pantheon_gemini_v4_agy_cli_compatibility.md`
- 如RED測試證明必要：
  - `scripts/agy_gemini_v4_structured_target.py`
  - `scripts/agy_gemini_v4_broker.py`
  - `scripts/agy_gemini_runner.py`
  - 對應focused tests

禁止：

- 讀取或匯出CLI token cache
- 建立Google Cloud project、OAuth client、service account或IAM binding
- 執行 `gcloud auth`、OAuth login或修改ADC
- 新增package dependency而未另行Review
- retry、fallback、credential pool或key rotation
- 修改文章、queue、registry、SEO pipeline、app、publish、deploy或default
  promotion
- push或deploy

## Slices

### AUTH-S1 — Candidate integration

- `traces_to`: `AUTH-001`
- dependency：none
- acceptance：主線以fast-forward包含reviewed code與canary evidence；無merge
  commit；worktree clean。
- verification：ancestry、changed files、`git diff --check`。

### AUTH-S2 — Credential/type inventory

- `traces_to`: `AUTH-002`, `AUTH-003`, `AUTH-006`
- dependency：none
- acceptance：只記錄key數量、來源權限、雜湊識別與control-plane可用性；
  不保存key內容。
- verification：privacy scan；key type只能是`STANDARD`、`AUTHORIZATION`或
  `UNKNOWN`。

### AUTH-S3 — Stable boundary decision

- `traces_to`: `AUTH-001`, `AUTH-004`, `AUTH-005`, `AUTH-006`
- dependency：AUTH-S1、AUTH-S2
- acceptance：明確決定短期transport與ADC migration gate；若無實證需求，
  不修改production code。
- verification：source／docs／evidence一致，受影響tests與
  `git diff --check`通過。

## Gate 1

`PASS`

- 實體卡已建立。
- base candidate、Review與canary identity已鎖定。
- key type確認缺少正式control-plane identity，狀態固定為`UNKNOWN`。
- 當前frontier：`AUTH-S1`、`AUTH-S2`。

## Gate 2

`PASS`

- 主線已由 `c01cfba1650a7cd6d666deb6b715d3d435694972`
  fast-forward至 `3cb36a175146d217346609b2c54d59d2eed3c5fd`。
- 沒有merge commit；reviewed code與real canary evidence ancestry保持不變。
- 三把source key只盤點數量、權限與雜湊識別；value未輸出或保存。
- Pantheon專用單key檔已以owner-only `0600`建立；未寫入repo、environment、
  argv或evidence，也未啟用。

## Gate 3

`PASS`

- Production code change：0。
- 五套affected suites fresh rerun：`224 passed in 67.19s`。
- Evidence JSON parse：PASS。
- Credential／token／absolute-path privacy scan：PASS。
- `git diff --check`：PASS。
- Google API、login、OAuth、IAM、project mutation：0。
- deploy、publish、default promotion：0。

## Decision

`READY_FOR_REVIEW`

短期維持reviewed owner-only API-key FD path。現有key型別為`UNKNOWN`，在取得
control-plane證據確認authorization key，或另卡完成OAuth／ADC／Vertex workload
identity migration前，V4不得切為default transport。
