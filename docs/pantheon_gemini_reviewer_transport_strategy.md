# Pantheon Gemini Reviewer transport 策略

## 決策

`SUPERSEDED_AS_CONTENT_GATE`（V4 transport 改為獨立技術改善）

本文件保留 Reviewer transport probe 的歷史證據與 V4 implementation 契約，但不再作為受監督產文的恢復 Gate。現行決策見
[`pantheon_content_transport_decoupling.md`](pantheon_content_transport_decoupling.md)：
新文、舊文修復與 GSC 調整可使用既有 CLI transport 以小批次恢復，仍須通過
deterministic gate、獨立 Reviewer 與人工 approval；發布與部署維持既有授權邊界。

推薦 transport 為 `minimal_mapper_pro_low`：Gemini 3.1 Pro Low 只產出最小 judgment，local deterministic mapper 在 judgment 通過 strict parse、schema 與 rubric 後，才搬移成正式 review object。Mapper 不得補欄、猜 code、改 verdict 或推導模型未明示的 hard failure。

## Probe 結果

使用兩個公開且 sanitized 的 corpus case，以 Gemini 3.1 Pro Low minimal judgment＋mapper 各執行三個 fresh Reviewer process，共六個 external CLI process invocations。每次只保存 request/config/output SHA-256、輸出 byte length、exit/parse/schema/rubric、必要錯誤位置與 verdict 一致性；未保存 prompt、raw response、stderr、秘密或本機絕對路徑。

這個 evidence 只能觀測外層 CLI process。`provider_model_calls` 固定標記為 `unobservable/unknown`；不得由六個外部 process 推導 vendor 內部 provider request 次數、retry 次數或精確成本。

| Configuration | Model | Transport shape | Strict parse | Schema | Rubric | 一致性 |
|---|---|---|---:|---:|---:|---:|
| `minimal_mapper_pro_low_reject` | Gemini 3.1 Pro Low | REJECT minimal judgment + mapper | 3/3 | 3/3 | 3/3 | 3/3 |
| `minimal_mapper_pro_low_approve` | Gemini 3.1 Pro Low | APPROVE minimal judgment + mapper | 3/3 | 3/3 | 3/3 | 3/3 |

REJECT corpus 為 3/3 `REJECT + hard_failure=true` 且辨識兩個固定 hard-failure code；APPROVE corpus 為 3/3 `APPROVE + hard_failure=false + findings=[]`。完整 sanitized fingerprints 位於 repair evidence 的 `matrix.json`。

## 為何選 Pro Low minimal mapper

- Pro Low minimal mapper 的 REJECT 與 APPROVE corpus 均為 3/3，且輸出範圍小；模型不負責合成可由本地程式確定的 envelope、case identity 與 summary。
- Mapper 的輸入已先通過封閉 schema；缺少或額外欄位都 fail closed，不能把 malformed response 修成通過。
- 本 Repair 沒有擴 scope 重跑 Pro High 或 baseline；仍不應直接恢復 nested production prompt。

## 拒絕與保留方案

- 拒絕將 CLI 的 output envelope 當作 response schema enforcement；machine gate 必須對 response text 自行 strict parse。
- 拒絕用 tolerant parser、fence stripping、substring extraction、JSON repair 或 LLM repair 把不合法 response 轉成通過。
- 拒絕 mapper 補猜 findings、hard failure 或 verdict。
- 暫不採 Pro High；只有更困難的 sanitized corpus 顯示 Pro Low rubric 不足，才另卡比較。
- Baseline nested single pass 保留為診斷對照，不作首選 implementation。
- 任一 parse/schema/rubric failure 都應 fail closed；Gemini 若未通過後續 corpus gate，降級 advisory-only，deterministic gates 維持 machine gate。

## 下一張 implementation 卡的精確 interface

### `ReviewerJudgmentV1`（Gemini 唯一輸出）

```json
{
  "verdict": "APPROVE | REJECT",
  "hard_failure": true,
  "findings": [
    {"code": "<allowlisted policy code>", "severity": "HARD", "message": "<non-empty text>"}
  ]
}
```

契約：單一 strict JSON object；`additionalProperties=false`；verdict、hard_failure、findings 全部 required。Policy code 必須來自 request 內的 allowlist。若 verdict 是 `APPROVE`，`hard_failure` 必須為 false 且 findings 必須為空；若任何 HARD finding 存在，verdict 必須為 `REJECT` 且 hard_failure 為 true。這些交叉條件由 deterministic rubric 驗證，不能由 mapper修正。

### `ReviewV1`（local mapper 輸出）

Mapper 只接收已通過 `ReviewerJudgmentV1` 的 object，並由本地可信 input 注入 `schema_version`、`run_id/case_id`、article identity 與 deterministic summary；judgment 的 verdict、hard_failure、findings 原樣搬移。任一欄位缺漏、額外欄位、未知 code 或交叉條件矛盾都回 typed failure，不產生正式 review。

### Process 與 evidence

每次 reviewer 使用 fresh CLI process、明確 model label、plan mode、sandbox、temporary cwd/log、固定 timeout；不得使用 conversation continue 或全域 alias。Evidence 僅保存 command/version/capability fingerprint、request/config/output SHA、byte length 與 typed gates，不保存內容原文或 stderr。計數欄位是 `external_cli_process_invocations`；`provider_model_calls` 必須維持 `unobservable/unknown`。

## 下一階段 Gate

1. 由原 Reviewer thread 固定本 Repair candidate commit 重新審查；本卡不得自行宣稱 `GO`。
2. 另開 implementation chain；不得在本卡修改 production transport。
3. Implementation 先用多個 sanitized case（包含 APPROVE、REJECT、混合 code、較長 prompt）做 fresh-process corpus gate。
4. Corpus gate 未達每個 case 3/3 strict parse + schema + rubric + consistency 前，不得把 V4 設為預設 transport，也不得啟用無人值守大量送出；此條不阻擋使用既有 CLI transport 的受監督小批次產文。

## 剩餘風險

- 本卡只有各一個短 sanitized REJECT 與 APPROVE case，未涵蓋長內容、實際深層 policy 或多文章 payload。
- CLI 與 server-side model routing 可能更新；binary SHA、version 與 model capability 必須在 implementation/release gate 重驗。
- 每個 corpus 的 3/3 是小樣本 capability gate，不是長期可靠度或 production SLO。
- Vendor 內部 provider model calls、silent retry 或 multi-call 不可由外層 CLI process receipts 觀測。
- CLI transport 仍未提供 response-schema enforcement；所有強制性來自 prompt 後的 local strict validation。
