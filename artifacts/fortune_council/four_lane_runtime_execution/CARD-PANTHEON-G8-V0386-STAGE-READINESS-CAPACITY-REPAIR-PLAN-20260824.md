# PANTHEON G8 V0386 stage readiness and capacity repair plan

## 工作名稱

V0386 stage readiness and capacity repair plan

## 前因

- V0385 main evidence：`0ef95c134b`。
- remote main、target/ref、source clone、actor before、Rule25 均 PASS。
- exact apply invocation=0、production mutation=0。
- blockers：target readiness path missing；Rule24 缺本次 fresh current receipt。

## 目的

以零 production mutation 釐清 promotion contract：target readiness 是 apply 前必要輸入、apply 內建立輸出，或另有正式 stage entrypoint；同時鎖定 Rule24 fresh measurement 的正式入口與最小證據，產出可供使用者核准的 exact repair／apply authorization packet。

## 必做

- coding／workflow source decision 前查 CodeGraph；無結果才限域 `rg`。
- 讀 V0383 plan/argv、V0385 gate summary、promotion script與受影響測試。
- 追蹤 readiness path 在 plan、apply、postcheck、rollback 的 create/read/write順序。
- 找出正式且可重現的 stage/readiness 產生入口；禁止用臨時 shell 手造 production artifact。
- 釐清 missing readiness 是 drift、過早 gate、plan bug或真實前置缺口。
- 找出 Rule24 fresh baseline／budget／monitor／stop-loss 的正式 sensor/gate入口，列出會寫的 evidence 路徑與最大容量。
- 僅執行 read-only、dry-run或 task-owned `/private/tmp` rehearsal；不得寫 production paths。
- 產 exact next-step argv、machine bindings、預期 writes、rollback/failure contract與 authorization digest；若無安全正式入口， verdict=`BLOCKED`。

## 禁止

- 禁止建立或修改 `/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage`。
- 禁止修改 actor、manifest、queue、state、barrier、transaction root或任何 production runtime。
- 禁止 apply、finalize、rollback、reset、deploy、canary、activation、launchctl mutation。
- 禁止 remote query/write、push、tag、安裝工具、改 source/workflow/tests或既有 artifact。
- 禁止沿用 V0383 authorization 冒充新 repair 授權；禁止派下一卡。

## Evidence ownership

- `CARD-PANTHEON-G8-V0386-STAGE-READINESS-CAPACITY-REPAIR-PLAN-20260824-RESULT.md`
- `g8_v0386_stage_readiness_capacity_repair_plan_20260824/`

## 驗收

- source evidence 精確指出 readiness contract與正式入口。
- Rule24 fresh gate所需 inputs/outputs、容量預算、停損與 evidence locator完整。
- exact argv canonical digest、authorization payload digest與所有 locator可重算。
- mutation allowlist／forbidden list完整；production mutation=0、remote access=0。
- JSON parse、受影響 tests、`git diff --check` PASS。
- repo只改本卡 ownership；單一 commit、clean、不 push。

## Verdict

只能是 `READY_FOR_REPAIR_AUTHORIZATION` 或 `BLOCKED`。
