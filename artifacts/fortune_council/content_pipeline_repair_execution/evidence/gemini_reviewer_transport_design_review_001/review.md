# Gemini Reviewer transport design 001｜Independent review

## Findings

- [P1] 重複 JSON key 可穿透 contradictory-verdict gate — `scripts/agy_gemini_transport_probe.py:164`
  - 觸發條件：response 同時包含兩個 `verdict`（例如先 `APPROVE`、後 `REJECT`），其餘欄位符合代表案例的 REJECT rubric。
  - 證據：離線負向探針得到 `strict_parse=true`、`schema_valid=true`、`rubric_valid=true`。Python `json.loads` 採最後一個同名 key，前一個矛盾值被靜默覆蓋。
  - 風險：candidate 宣稱會拒絕矛盾 verdict／hard_failure，但實際可把含矛盾判斷的模型輸出接受為 machine-gate success；strict-mapper 契約不可證明。
  - 建議：parse 階段以 `object_pairs_hook` 對每層 object 拒絕 duplicate keys，再進 schema/rubric；補 duplicate `verdict`、`hard_failure`、nested finding key 的 fail-closed 測試。

- [P1] 固定 interface 無法表示文件要求的 APPROVE judgment — `scripts/agy_gemini_transport_probe.py:56`
  - 觸發條件：下一階段 corpus 送入文件定義的合法 judgment：`verdict=APPROVE`、`hard_failure=false`、`findings=[]`。
  - 證據：離線驗證回傳 `$.findings:minItems`；但 `docs/pantheon_gemini_reviewer_transport_strategy.md:53` 明定 APPROVE 必須 findings 為空。
  - 風險：若下一張 implementation 卡採用此「精確 interface」，所有合法 APPROVE case 都會 fail closed，無法完成卡片要求的 APPROVE/REJECT corpus gate，且 Reviewer 會被結構性偏向 REJECT。
  - 建議：讓結構 schema 接受空 findings，並用 deterministic cross-field rubric 強制 APPROVE/false/empty 與 REJECT/true/non-empty；為兩個方向及所有矛盾組合建立參數化測試。

- [P1] 9 次上限只證明 CLI process 數，不能排除 CLI 內部 silent retry／multi-call — `scripts/agy_gemini_transport_probe.py:244`
  - 觸發條件：CLI transport 因暫時性 provider/network failure 在單一 `subprocess.run` 內自行 retry，或單次命令對 provider 發出多個 request。
  - 證據：`calls` 僅在外層 runner 每次啟動前遞增（`scripts/agy_gemini_transport_probe.py:271-275`）；receipts 沒有 provider request ID、attempt count 或 no-retry capability。`artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_transport_design_001/decision.md:12` 因此只能證明九個 fresh CLI processes，不能證明「九次模型呼叫、沒有第十次」。
  - 風險：review card 明定 9-call／無靜默重試契約不可證明即 `NO_GO`；現有 evidence 可能低估真實模型呼叫與成本，也無法稽核上限。
  - 建議：取得可驗證的 no-retry transport capability，或保存 sanitized provider request/attempt receipts 並逐次計數；在此之前把結論限縮為「9 CLI invocations」，不得宣稱 exact model-call budget。

- [P2] finding message 的 non-empty 契約沒有被 schema/rubric 強制 — `scripts/agy_gemini_transport_probe.py:45`
  - 觸發條件：兩個 finding code 正確，但 `message` 都是空字串。
  - 證據：離線負向探針仍得到 `strict_parse=true`、`schema_valid=true`、`rubric_valid=true`，與 `docs/pantheon_gemini_reviewer_transport_strategy.md:48` 的 `<non-empty text>` 不符。
  - 風險：machine gate 可接受沒有可讀理由的 finding，讓 review evidence 不足以供後續修復或人工稽核。
  - 建議：schema 增加 `minLength: 1`，並在 deterministic rubric 拒絕 trim 後為空的文字；補空字串與純空白測試。

## Fixed scope

- Review card: `CARD-CONTENT-GEMINI-REVIEWER-TRANSPORT-DESIGN-REVIEW-001`
- Base: `7afe5f792af1c87cd983af2f1be6dafb634650e1`
- Reviewed candidate: `d15df4b1e892f3b9854f42dc067d89af7ee37cd3`
- Provisioning commit: `51ce46dc4cdd82a1e18d65cc2d5bd48d48a8f292`（只用於提供 review card，未納入 candidate diff）
- Reviewer 未呼叫 Gemini CLI、未修改 candidate，僅新增本 review evidence。

## Spec axis

`FAIL`。固定 diff 有遵守 sanitized input、未把 prompt/raw stdout/stderr/秘密/PII/本機絕對路徑寫入 repo evidence，`matrix.json` 的 3×3 rows 與 summary/decision 也可由 sanitized receipts 重算。然而 contradictory JSON 可被接受、APPROVE interface 自相矛盾，且 exact 9 model-call/no-retry 契約不可由 evidence 證明；未滿足 review card 的必要條件。

## Standards axis

`FAIL`。既有 6 個單元測試與 `py_compile` 通過，fixed diff 的 `git diff --check` 通過；但測試缺少 duplicate-key、APPROVE/empty-findings、cross-field contradiction、empty/blank message 與 transport retry-accounting 等核心 fail-closed cases。現有 parser/rubric 不足以作高風險 machine gate。

## Verdict

`NO_GO`

依 review 卡契約，任何 P1 或 9-call／strict-mapper 契約不可證明即必須 `NO_GO`。本 verdict 只退回主線安排獨立 Repair；Reviewer thread 不修 candidate。三條 production 內容線繼續保持停止。

## Verification evidence

- Fail-closed preflight：PASS；獨立 worktree、clean tree、卡片可讀，`HEAD=51ce46dc4cdd82a1e18d65cc2d5bd48d48a8f292`、`HEAD^=d15df4b1e892f3b9854f42dc067d89af7ee37cd3`。
- Fixed diff：只審查 `7afe5f792af1c87cd983af2f1be6dafb634650e1..d15df4b1e892f3b9854f42dc067d89af7ee37cd3`。
- `py_compile scripts/agy_gemini_transport_probe.py`：PASS（pycache 導向暫存區）。
- `pytest -q -p no:cacheprovider tests/test_agy_gemini_transport_probe.py`：PASS，`6 passed`。
- Matrix recomputation：PASS；9 rows，三個 config 各 3 rows，stored summaries 與 receipts 重算一致，stored/recomputed decision 均為 `GO_GEMINI_CLI_MACHINE_GATE`。
- Privacy/static scan：PASS；candidate evidence 未發現 secret、PII、本機絕對路徑、raw response、prompt 或 stderr payload；只出現描述性文字、hash/byte count 與 typed gate fields。
- Reviewer 負向探針：duplicate-key 被錯誤接受；合法 APPROVE 被 `minItems` 拒絕；空 message 被錯誤接受。
- `git diff --check base..candidate`：PASS。

## Remaining risks and required implementation gates

- 本 review 未呼叫 Gemini CLI，未重新驗證外部 CLI capability 或原 9 次實際執行；依卡片只審查封裝 evidence 與 deterministic code。
- Repair 必須先封閉上述 P1，再由新的固定 candidate 重新做獨立 review。
- 後續 implementation/corpus gate 至少需涵蓋 APPROVE、REJECT、所有 cross-field contradiction、duplicate keys、unknown/duplicate codes、空白訊息、長 prompt、timeout/nonzero 與可稽核 retry accounting。
- 即使後續 architecture GO，也只代表可進 implementation/corpus；不代表 production recovery、merge、deploy、publish 或三條內容線恢復。
