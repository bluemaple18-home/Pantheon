# Pantheon 四線 EN legacy brief exact-cycle 停線 RCA

## 工作名稱

EN legacy flat brief exact-cycle production failure RCA（唯讀；不是 Repair）

## Locked incident

- exact run：`auto-i18n-en-aa637e1bf05d3ad21429`
- accepted source：`73180233275840b0ab0e101f246e495ee6815fc9`
- live actor：`6541693e929a20cbcffe8b070085b5f1caec7a92`
- runtime generation：`g72-6541693e-new-lane-current-acceptance-20260829`
- 第二次 legal exact no-sweep coordinator：回傳 `failed`，registry `active → failed`，`error_type=ValueError`
- observed mutation budget：Writer `0`、outbox `0`、provider `0`
- stop line：禁止第三次 production 嘗試。

## Root question

沿 actual current live actor code 還原 swallowed `ValueError` 的精確形成位置與 message；以 exact immutable brief/registry fixture 在隔離 temp root 重現。找最後會成功處理此 legacy flat brief 的版本／commit與第一個拒絕版本／機制，鎖 durable invariant、authoritative owner 與 promotion boundary，並裁決單一根因。

允許的主裁決：

- `INVALID_LEGACY_BRIEF_DATA`
- `LEGACY_BRIEF_CROSS_VERSION_CONTRACT_GAP`
- `COORDINATOR_ERROR_OBSERVABILITY_GAP_ONLY`
- 或證據支持且同等單一的裁決。

## Writable scope

- 本卡。
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_en_legacy_brief_exact_cycle_rca_20260830/RESULT.md`
- 同一 RESULT root 下最小 isolated reproduction evidence。

## Forbidden

- production root 任何 write／手改／刪檔。
- provider call、publisher、publish、promotion、commit、push、tag、deploy。
- 第三次 production exact cycle。
- 新 Repair、generic migration、registry、FSM 或 authority。
- source／tests 修改。

## Required evidence

- production failure receipt 與 current failed registry 的 immutable identity。
- current live actor exact source location與未吞例外的 isolated reproduction message。
- git history：最後成功處理同形 legacy flat brief 的版本／commit，以及第一個拒絕該形狀的變更點；若證據不足必須明列。
- 現有 terminalize／retry／reseed seam 對 exact preconditions 的適用性證明。
- durable invariant、authoritative owner、promotion boundary。
- 若需 code seam，只能鎖定最多 `1 source + 1 test` 的最小 frontier，不實作；若資料本來非法，只鎖正式 terminalization operational frontier。

## Acceptance

- 一條已執行、可重跑、能捕捉同一症狀的 isolated red-capable command。
- 單一根因裁決與一個 bounded next step。
- production/provider/publish mutation 全為 `0`。
- `git diff --check` PASS。

