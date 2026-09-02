---
id: RESULT-PANTHEON-OPEN2-PROVIDER-ADMISSION-CAP-IMPLEMENTATION-20260902
chain_id: PANTHEON-FOUR-LANE-RESIDENT-OPERABILITY-20260902
role: implementation_result
date: 2026-09-02
status: delivered_for_mainline_integration
---

# OPEN-2 provider admission cap 實作結果

## 結論

`DELIVERED_FOR_MAINLINE_INTEGRATION`

四 lane 共用既有 allocator state／lock：Asia/Taipei admission date 的整數 count 最多為
`102`。第 103 筆在 claim／marker／credential read／provider call 前回傳
`DAILY_PROVIDER_ADMISSION_CAP`。production-attempt marker 是唯一 replay identity：marker
仍在時 replay 不 commit、不呼叫 provider；marker 被明確刪除後，即使重用相同 job id，仍是新
attempt，會再次計數與呼叫 provider。

Runner 先無副作用 preflight，再 claim，並在既有 lock 中原子建立 marker 後才 commit。V4 broker
與 credential-pool transport 分離：有 production pool/state 的 V4 仍走 marker＋cap，但不讀取
credential；無 pool 的非正式測試 transport 保持不套 production cap。

Repair-2 將正式 coordinator 納入既有 formal transport gate：coordinator root queue 在正式環境缺
pool/state/model-route 時，於 claim 前回傳 `formal_production_transport_env_missing`；有完整 pool
contract 時仍先受 `102` cap，broker 不會在第 103 筆執行。

## Production source LOC

- `scripts/agy_gemini_allocator.py:21-34,355-492,513-537,644-709,829-933`：schema v4 只保存
  `cost_date`＋integer `daily_provider_admission_count`，在既有 lock 下判斷並 commit。
- `scripts/agy_gemini_runner.py:1405-1510`：pool 表示需要 cap；是否讀 credential 只決定
  transport。V4＋pool 也在 broker 前 commit。
- `scripts/agy_gemini_runner.py:413-440`：固定 formal service 集合含 coordinator 與四 lane，沿用
  既有 missing-env gate。

本 repair 相對候選 `5eda4f626b` 的 production source diff：`+40/-66` LOC；沒有新增
accounting engine、counter file、clock abstraction 或 Coordinator lifecycle。

## Test LOC 與驗證

- `tests/test_agy_gemini_allocator.py:28-128`：第 102／103、Asia/Taipei 午夜 rollover，及
  malformed count/date/schema fail-closed。
- `tests/test_agy_gemini_outbox.py:2558-2972`：marker deletion 的 same-job new attempt、marker
  replay 零 call/零 count、V4＋pool 第 103 筆 provider 前拒絕、四 lane 競爭最後一格唯一成功，與
  marker→commit／before provider／during provider／after response 四個 crash point；另有 formal
  coordinator root queue 的 provider／CLI／broker 零呼叫與 formal V4＋pool 第 103 筆。
- `tests/test_agy_gemini_runner.py:27-38`：missing、非整數、非 `102` config fail-closed。

本 repair 相對候選的 test diff：`+208/-17` LOC；新增的是每個要求的 RED-capable evidence，沒有
建立 test-only accounting helper。

實際命令與結果：

- `.venv/bin/python -m pytest -q tests/test_agy_gemini_allocator.py tests/test_agy_gemini_outbox.py tests/test_agy_gemini_runner.py`：`199 passed`。
- formal coordinator focused selection：`2 passed, 178 deselected`。
- focused repair selection：`12 passed, 175 deselected`。
- `.venv/bin/python -m py_compile scripts/agy_gemini_allocator.py scripts/agy_gemini_runner.py`：PASS。
- `git diff --check`：PASS。

Coordinator／installer source 未在本 repair diff 改動；未重跑 full coordinator suite，故本 RESULT
不對它作全量結論。

## Minimum sufficient

`why_not_less`：只有共用 allocator lock 能原子拒絕四 lane 的第 103 筆；marker 才能判定 exact
attempt replay。兩者缺一，會有跨 lane over-admission 或 crash replay 重呼。

`why_not_more`：allocator 不再保存 job-id list；schema v4 只有日期與 count，state size 回到
`4 KiB`。沒有 counter file、database、scheduler、價格／token service、generic cap 或 clock
abstraction。

Repair-2 source production LOC：`+2/-2`；test LOC：`+58/-0`。`why_not_less`：只把 coordinator
加入既有固定 service 判斷，才能使其沿用同一 fail-closed gate；不需新增 coordinator lifecycle 或
第二個 transport validator。

`do_not_absorb`：未觸及 Publisher success quota、Coordinator lifecycle、manifest、production
runtime、launchctl、provider、deploy、commit、push 或 merge。

## Mutation accounting

- provider call：`0`
- production runtime／queue／state mutation：`0`
- launchctl：`0`
- deploy／publish／commit／push／merge：`0`
