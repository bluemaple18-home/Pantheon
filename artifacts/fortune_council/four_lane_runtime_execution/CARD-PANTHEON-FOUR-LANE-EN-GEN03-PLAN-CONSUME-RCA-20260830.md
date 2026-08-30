# Pantheon four-lane EN Gen03 plan consume RCA

## 工作名稱

`EN-GEN03-PLAN-CONSUME-RCA-20260830`

## Root question

對 run `auto-i18n-en-aa637e1bf05d3ad21429` 的 consume-gen03-plan-writer failure 做唯讀 RCA：鎖定 last-good、first-bad mechanism／commit、exact `LocalePlanValidationError` 與 artifact formation chain，並判斷是否與既有 gen04/gen05 lifecycle seam 同根。

## 可寫範圍

- 本卡。
- `PANTHEON-FOUR-LANE-EN-GEN03-PLAN-CONSUME-RCA-20260830/RESULT.md`。
- `/tmp` 下的 isolated fixture／receipt；不得回寫 production。

## 禁止範圍

- 不得修改 source、tests、production runtime、queue、registry、run state、KO／JA artifacts、publisher或公開頁。
- 不得執行 provider、coordinator、publish、promotion、replacement、retry或 terminalization mutation。
- 不得建立第二張 RCA、Repair、新 authority、registry、FSM或 generic migration。

## 必答與驗收

1. CodeGraph first；無有效結果才限域 `rg`。
2. last-good與 first-bad exact mechanism／commit。
3. exact error message與 artifact formation chain。
4. registry／generation root／lane residue／repair budget durable invariant。
5. 已執行、provider=0、production bytes不變的 exact RED fixture。
6. 與 gen04／gen05 lifecycle seam的同根或內容 validator分類。
7. authoritative owner、跨版本 lifecycle、promotion／replacement boundary。
8. 單一裁決與 `why_not_less`／`why_not_more`／`do_not_absorb`。
9. `git diff --check` PASS。

## Stop conditions

- production identity或相關 bytes在取證中漂移。
- isolated fixture無法重現同一 exact error。
- 同一 blocker連續三次仍無法取得必要證據。
- 結論需要 production mutation、provider call或擴大成 Repair。
