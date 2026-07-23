# Gemini V4 Output Binding Repair｜Independent Review

## Findings

未發現阻塞問題；未識別 P0–P3 具體 finding。

## Spec axis

Candidate `4e04e82506c4a1c2a3846640f9504fca972ae9fd` 符合 Repair contract：

- `scripts/agy_gemini_v4_broker.py:986-993` 先將 control replay、process count、
  final anchor、byte count與stdout SHA-256和收到的`raw_result`逐項核對；不符即
  回傳 fail-closed failure result。
- `scripts/agy_gemini_v4_broker.py:994-1015` 只在`COMPLETE/1/SUCCESS`且JSON為
  object、通過response schema後，才把已驗證的原始bytes放入`result_json`。
  malformed與schema-invalid output仍為`caller_contract_satisfied=false`、
  `result_json=None`。
- `scripts/agy_gemini_v4_broker.py:294-315` 的`.result`重新解析JSON；
  `normalized_trace()`只放解析後的`result` object，不暴露`result_json`或
  `raw_result`。
- `scripts/agy_gemini_runner.py:91-117` 先核對receipt與caller contract，再把
  `broker_result.result`寫入inbox；flag-on失敗不進legacy branch，也不持久化raw
  output。
- ledger、anchor、replay、concurrent-create與transport選擇程式碼未被candidate
  修改；相關回歸均通過。

## Standards axis

- Base到candidate只有8個檔案，精確等於Repair evidence所列清單，且全部位於
  Repair allowlist。
- Production改動只有一個expression；沒有修改runner、ledger、anchor、fallback、
  publishing或privacy policy。
- Changed Python diff沒有debug marker、credential pattern或raw-output持久化欄位。
- `py_compile`與`git diff --check`通過。

## Independent reproduction

- Pretty-JSON binding targeted test：`1 passed`。
- V4 focused三檔：`74 passed`。
- Legacy publishing：`57 passed`。
- Coordinator：`6 passed`。
- 唯一pytest總數：`137 passed`；targeted pretty test已包含在focused 74中，不重複
  計數。
- 額外synthetic harness確認：
  - pretty JSON原始bytes的length／SHA與control一致；
  - malformed與schema-invalid output fail closed；
  - normalized trace與runner inbox只含parsed object；
  - flag-on路徑legacy fallback calls為0。

## Open questions

無。

## Remaining risks

- 本Review沒有也未獲授權執行新的外部Gemini／agy canary；external invocation為0。
- GO只表示Repair candidate可交回主線考慮整合。Blocked rollout的既有real
  evidence不可被本次synthetic驗證取代；整合後仍須新的明確外部呼叫授權與canary
  evidence。
- Provider internal model-call provenance仍為`UNKNOWN`。
