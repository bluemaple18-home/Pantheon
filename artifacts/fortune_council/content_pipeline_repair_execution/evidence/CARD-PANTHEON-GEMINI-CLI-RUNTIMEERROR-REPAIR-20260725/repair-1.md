# Repair-1 evidence

## Card

- Repair card：`CARD-PANTHEON-GEMINI-CLI-RUNTIMEERROR-REPAIR-01-20260726`
- Parent candidate：`ed8147bafb11a6948ba19eec95d5e5c745da6a49`
- Reviewer verdict：`NO_GO`

## Root cause

P1：failed receipt consumer 在建立 `ExternalJobFailed` 前，直接將 `error_type` 轉成字串，未驗證 fixed enum、outer schema、job id 或 request hash。任意文字因此可進 exception message、CLI stdout 與 coordinator state。

P2：operation receipt 直接對任意 `error_code` 做 set membership；list/dict 等不可 hash 值會在原 exception handler 中再拋 `TypeError`，遮蔽原始失敗且無法寫下安全 receipt。

## RED → GREEN

初始 synthetic command 同時涵蓋：

- sensitive / overlong / list / dict / integer / null `error_type`
- CLI stdout、coordinator state、downstream operation receipt
- list / dict / non-string / unknown string `error_code`

RED：`10 failed, 3 passed`。

修復後相同核心 regressions：`13 passed`。

追加 receipt schema/binding regressions：

- job id mismatch
- request hash mismatch
- extra / missing field
- invalid或 unhashable error code
- invalid或 unhashable broker diagnostic
- invalid timestamp
- non-object與 invalid JSON

上述 malformed cases 一律收斂成固定 `InvalidFailureReceipt`；不可信值不進 exception、stdout、state 或 operation receipt。來源 malicious fixture 僅作為 consumer 輸入，不被複製至任何 downstream artifact。

## Implementation

- Failed receipt 外層 schema 嚴格限制既有 required/optional fields。
- 綁定 `schema_version`、`job_id`、`request_sha256` 與 closed timestamp。
- `error_type` 僅接受固定 enum；其他值 fail closed。
- `error_code` 僅接受 exact string、fixed enum，且只與 `GeminiCliFailure` 配對。
- V4 broker diagnostic 僅接受固定欄位、enum、數量、深度與 path token。
- Invalid JSON、oversized receipt、讀檔/編碼錯誤不回顯原始內容。
- Operation receipt 先確認 `type(error_code) is str`，再做 enum membership。

## Verification

- 核心 GREEN：`13 passed`。
- Malformed/binding targeted：`9 passed`。
- 三個受影響 suites（final）：`154 passed in 50.25s`。
- Content publisher：`41 passed`。
- Full pytest：`451 passed, 1 warning in 103.89s`。
- 真實 Gemini probe：未執行。
- 真實 queue / receipt / ledger / run state：未操作。
- Push / merge / deploy / reload：未執行。

- Privacy targeted：`23 passed`。
- Python compile：pass。
- `git diff --check`：pass。
- `[DBG-` diff scan：0 matches。
- Production diff sensitive marker / secret pattern scan：0 matches。
- Changed-file allowlist：pass。

Final clean check 於候選 commit 後另行執行。
