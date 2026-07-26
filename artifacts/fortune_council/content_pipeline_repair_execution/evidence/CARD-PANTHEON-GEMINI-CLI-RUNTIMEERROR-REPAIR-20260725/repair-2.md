# Repair-2 evidence

## Card

- Repair card：`CARD-PANTHEON-GEMINI-CLI-RUNTIMEERROR-REPAIR-02-20260726`
- Parent candidate：`d4fa6d1a29721714b72b46f69050f5a0905a5580`
- Reviewer verdict：`NO_GO`

## Root cause

Failed receipt parse boundary 已收斂 I/O、encoding、`JSONDecodeError` 與 `ValueError`，但未包含 Python 標準 JSON decoder 對深巢狀合法 JSON 拋出的 `RecursionError`。約 20,000 層、約 40 KB、低於 64 KB size gate 的 payload 因而可逸出 consumer，讓 CLI 路徑產生 traceback，coordinator state 也只能記成 `RecursionError`。

## RED → GREEN

Public synthetic fixture：

- JSON 語法合法。
- 巢狀深度 20,000。
- UTF-8 byte size 小於 `MAX_FAILURE_RECEIPT_BYTES`。
- 內含 private path / credential marker。

RED：`3 failed`。

- Direct consumer 逸出 `RecursionError`。
- Operation/CLI seam 逸出 `RecursionError`，無法產生 fixed stdout/receipt。
- Coordinator state 記為 `RecursionError`。

GREEN：`3 passed`。

- Direct consumer 只回 `InvalidFailureReceipt`，`__cause__ is None`。
- CLI stdout 為固定 JSON；stderr 無 traceback，stdout/stderr 皆無 payload marker或 payload path。
- Operation receipt 無 payload marker。
- Coordinator state 為 `InvalidFailureReceipt`，無 marker或 `RecursionError`。

## Implementation decision

在既有 failed receipt `json.loads` parse boundary catch tuple加入 `RecursionError`，沿用 `raise ExternalJobFailed(..., InvalidFailureReceipt) from None`。

未新增自製 JSON parser或重複 nesting scanner。既有 64 KB size gate與標準 decoder recursion guard已提供明確資源邊界；在唯一 parse boundary fail closed是本 finding 的最小必要修復。

## Verification

- Privacy targeted：`26 passed in 0.10s`。
- 三個受影響 suites：`157 passed in 49.43s`。
- Content publisher：`41 passed in 3.20s`。
- Full pytest：`454 passed, 1 warning in 104.44s`。
- 真實 Gemini probe / 生成請求：未執行。
- 真實 queue / receipt / ledger / run state：未操作。
- Push / merge / deploy / reload：未執行。

- Python compile：pass。
- `git diff --check`：pass。
- Changed-file allowlist：pass。
- `[DBG-` diff scan：0 matches。
- Production diff secret/path/payload marker/traceback scan：0 matches。

Final clean check於候選 commit後另行執行。
