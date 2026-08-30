# EN Gen03 failed-translation replacement boundary 獨立審查

## 唯一裁決

`NO_GO_EXISTING_BOUNDARY_NOT_EXACT_PLAN_ONLY`

不得用目前既有的 failed-translation replacement 自動 sweep 直接處理 EN run
`auto-i18n-en-aa637e1bf05d3ad21429`，也不得新增 Repair 或新架構。

RCA 對原 run 的內容根因與 terminal boundary 判定成立；內部
`enqueue_translation_replacement()` 也具備 bounded fresh identity、source digest
revalidation、一次性 lineage 與正負測試。但是 production 可呼叫的唯一入口只在
unscoped `--lane-mode cycle` 中自動 sweep。它沒有：

- 指定 source terminal run 的 selector；
- failed-translation replacement 的 plan-only 模式；
- 只建立 replacement、不推進其他 lane 的 mutation boundary；
- 以 exact run selector 建立 replacement 的路徑。

更關鍵的是，`cycle --exact-run-id ...` 會明確關閉 replacement seeding。因此現有
CLI 無法同時滿足「exact EN」、「zero-write plan」、「不碰 KO／JA」三項 acceptance。
不得以 Python private/internal function call 冒充正式 operator 入口。

## Findings

- [P1] 正式入口缺少 exact plan-only replacement boundary —
  `<runtime-root>/actor/scripts/agy_gemini_coordinator.py:5638`

  `seed_failed_translation_replacements()` 只在 `lane_mode=true`、`new_only=false`、
  `selected_run_ids is None` 時執行。換句話說，能觸發 replacement 的 production
  命令必須放棄 exact-run selector；只要指定 EN run，replacement 就不會建立。

- [P1] 唯一可觸發入口的 mutation scope 超出本卡 —
  `<runtime-root>/actor/scripts/agy_gemini_coordinator.py:5687`

  unscoped lane cycle 在 replacement seeding 後，會選取各 lane active state、呼叫
  `_advance()`，只要形成 pending job，還會呼叫 runner `process(root)`。目前 KO 與 JA
  各有一個 active `i18n-rewrite` run，因此此入口不能證明不碰 KO／JA，也不能保證
  plan-only 或 provider=0。

- [P1] CLI 沒有 failed-translation replacement 子命令 —
  `<runtime-root>/actor/scripts/agy_gemini_coordinator.py:6098`

  parser 只有 `replace-failed-external-job` 提供 `--plan-only`；該命令處理的是同一
  run 中 failed external job identity，不是 terminal translation run 的 fresh
  replacement。把兩個 boundary 混用會違反本 RCA 的 semantic-budget 與 lineage
  邊界。

## Spec axis

### 原 run terminal／budget：PASS

- registry：`status=failed`、`error_type=LocalePlanValidationError`、
  `last_job_id=7af8867e8b2684434d8efde7f6b74cba93c6a613`。
- attempt 03 `planning-result.json`：
  `EXTERNAL_PLAN_AVAILABLE / PLANNING_CONTRACT_FAILURE / terminal_stage=PLANNING`。
- exact terminal reason：
  `locale plan rebuild reused prior outline topology for article-01`。
- attempts 只有 `01`、`02`、`03`；`attempts/04` 不存在。
- current fresh loop 是 initial generation 加 `max_repairs=2`，Gen03 已是 repair 2/2、
  generation 3/3 的最後 allocation。

因此不得 resume、不得 retry same Gen03 job、不得建立 Gen04。RCA 的
`GEN03_AUTHORITATIVE_TOPOLOGY_REUSE` 裁決與 current topology guard 相符。

### 內部 replacement invariant：PASS

`enqueue_translation_replacement()` 已證明：

- 只接受 `status=failed` 與 closed recovery reason；
- 拒絕 base run 本身已是 `-replacement-01`，禁止 replacement 鏈膨脹；
- fresh run ID 固定為 `<base-run-id>-replacement-01`；
- fresh run directory、brief、registry state 與原 run 分離；
- `replacement_of` 與 `replacement_reason` 明確保留 lineage；
- 逐 article 重新載入 current source，要求 current `source_sha256` 精確等於 base
  brief；source drift fail closed；
- replacement brief 只替換 run ID，來源 article identity／locale／source SHA 保持
  不變；不猜 source mapping，也不複製 Gen03 external plan 或 fact-to-section mapping；
- fresh run 沒有舊 `attempts/`，因此由 generation 01 取得獨立 semantic budget；
- idempotent replay 只得到同一 replacement identity；第二層 replacement 被拒絕。

### 正式 operator boundary：FAIL

以上 invariant 目前只有 internal callable 與 automatic lane sweep。沒有 exact、
plan-only、single-terminal-run 的正式 CLI，所以不足以對 production 給 GO。

## Standards axis

正向／負向 source-level 測試存在且本次在 live actor `f456a4d8...` 實跑：

```text
13 passed in 0.53s
```

涵蓋：

- replacement identity bounded、idempotent、原 terminal bytes不變；
- source drift 拒絕且不建 replacement；
- 每條 i18n lane 最多建立一個 replacement；
- lane cycle 確實會自動 seed；
- skip decision 可持久化且不重複；
- recovery reason closed；非 eligible failure 不建立 replacement。

但沒有測試能證明「用正式 CLI 對 exact EN 做 plan-only replacement，且 KO／JA
bytes不變」，因為 public CLI 根本沒有這個行為。這不是單純缺測試，而是 acceptance
要求的 operator seam 不存在。

## Exact command／參數審查

### 合格 plan-only command

```text
NONE
```

current CLI 沒有 `plan-failed-translation-replacement` 或等價子命令。

### 最接近但禁止執行的正式命令

```sh
<actor-python> -m scripts.agy_gemini_coordinator \
  --queue-root <runtime-root>/queue \
  --repo-root <runtime-root>/actor \
  --lane-mode \
  cycle
```

Mutation boundary：

1. 掃描全部 failed translation states；
2. 每個 i18n lane 最多建立一個 eligible replacement；
3. 重新讀取全部 active states；
4. 每條 content lane 最多推進一個 run；
5. 若產生 pending job，runner 可處理 queue，存在 provider mutation；
6. 不提供 plan-only、source run selector 或 EN-only mutation seal。

因此此命令不符合本卡，未執行。

### 看似 exact 但不會建立 replacement 的命令

```sh
<actor-python> -m scripts.agy_gemini_coordinator \
  --queue-root <runtime-root>/queue \
  --repo-root <runtime-root>/actor \
  --lane-mode \
  cycle \
  --exact-run-id auto-i18n-en-aa637e1bf05d3ad21429
```

`selected_run_ids` 非空時，source 明確令 `translation_replacements=None`；原 run 又是
failed，不會被 active-state selection 推進。這不是 plan-only preflight，只是關閉
replacement 功能，亦未執行。

## Live authority 與 current scope

- actor HEAD：`f456a4d8c21ce0a237254d31e6662339a1d522fb`。
- runtime generation：
  `g73-f456a4d8-four-lane-legacy-brief-repair-20260830`。
- EN replacement `auto-i18n-en-aa637e1bf05d3ad21429-replacement-01`：不存在。
- active KO：`auto-i18n-ko-bc1ce017b4ac2657a133`。
- active JA：`auto-i18n-ja-278fce6e38a85de996dd`。
- 本審查 provider／coordinator／publisher calls：0。
- production mutation：0。
- publish／tag／push：0。
- production queue 全檔案 snapshot digest：
  `before=after=0e87602e66aff435d9bdb70642044c1bde2b673b638212de3eb98b5e07a3a68c`。

## Acceptance mapping

| Requirement | Result | Evidence |
|---|---|---|
| 原 run Gen03 repair 2/2 terminal | PASS | failed registry、Gen03 planning contract failure、無 attempt 04 |
| 不 resume/retry same job | PASS（裁決） | same bytes會重現同一 validator failure；未執行 |
| 不建 Gen04 | PASS | current attempts只有01..03；fresh loop上限3 |
| fresh run identity | PASS（internal seam） | deterministic `-replacement-01` identity |
| 獨立 semantic budget | PASS（internal seam） | fresh run沒有既有 attempts，從generation 01開始 |
| 精確 source lineage | PASS（internal seam） | brief copy + current source SHA revalidation |
| 不猜 mapping | PASS（internal seam） | 不帶入 prior external/locale plan；只保留source brief |
| 不碰 KO／JA | FAIL（formal entry） | 觸發 replacement 必須 unscoped lane cycle |
| 不碰 publish | PARTIAL | replacement code不publish；unscoped cycle仍可推進其他工作 |
| 正式 exact plan-only入口 | FAIL | parser無此子命令；exact selector反而關閉seeding |
| 正負測試 | PASS（internal seam） | live actor targeted suite 13 passed |

## Final gate

```text
status: NO_GO
verdict: NO_GO_EXISTING_BOUNDARY_NOT_EXACT_PLAN_ONLY
rca_root_cause_accepted: true
source_repair_required_by_this_review: false
new_architecture_authorized: false
provider_calls: 0
production_mutation: 0
publish_calls: 0
blocking_condition: missing formal exact plan-only failed-translation replacement entry
git_diff_check: PASS
```

下一步回主線裁決；本 review 不授權 production、provider、coordinator、publisher、
Repair 或新架構。若維持「不得新增 Repair」，則 EN run 保持 terminal failed，不能用
現有 automatic lane cycle 繞過 acceptance。
