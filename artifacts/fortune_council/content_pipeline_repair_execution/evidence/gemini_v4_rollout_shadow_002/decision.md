# Gemini V4 Shadow-002｜Decision

## Status

`DELIVERED_CANDIDATE / READY_FOR_LIMITED_ROLLOUT_REVIEW`

## Evidence

- 新chain lineage與舊blocked rollout隔離：`PASS`
- Flag-off legacy與flag-on no-fallback：`PASS`
- V4 focused、legacy publishing與coordinator：`137 unique passed`
- 三種precommitted stdout encoding：`3/3 accepted`
- Mutation controls：`13/13 rejected`
- Recorder／verifier `py_compile`：`PASS`
- Privacy、allowlist、debug marker與diff gates：`PASS`
- External Gemini／agy generation：`1`
- Real shadow：`COMPLETE/1 / SUCCESS`
- Output encoding：`canonical-json-newline-v1`
- Reconstructed stdout：`59 bytes`／
  `28c08d3d33806babce80bb457b636b41c9ab97595b7ff1c300a2a71440e152f5`
- Ledger SHA-256：
  `0d5130546f7c70f56e64c742eecb097205cdb2aae276db3865c31b5e65bc04b9`
- Final anchor：
  `03c56ce06e79c45c1e5e6a3d036ec871e8db1ee55066b62e61aadc70f875e621`
- Independent real verifier：`PASS`

## Authorization consumption

主線完整展示`preflight.md`固定包後，使用者明確回覆「繼續」。該授權只綁定到
Shadow-002本次production `run_single_shot`，現已消耗`1/1`。沒有retry、fallback、
automatic resend或第二次呼叫。

## Boundary

- Delivery：`DELIVERED_CANDIDATE / READY_FOR_LIMITED_ROLLOUT_REVIEW`
- External invocation allowance consumed：`1/1`
- Real bundle：privacy-safe，未保存raw stdout
- Retry／fallback：`0`
- Push／deploy／publish／default promotion：`0`
- Not claimed：rollout ready、已整合、已放量或已上線

## Remaining risk

- 本卡只有一次real canary，尚未經獨立limited rollout Reviewer裁決。
- Provider internal model-call provenance仍為`UNKNOWN`；process count只證明broker
  啟動一個已確認target process。
- Task shell的PATH未直接解析`agy`；本次使用的是固定包中已驗version與digest的既有
  executable，未修改全域PATH或CLI設定。
- 本candidate不授權promotion、push、deploy、publish或任何後續external invocation。
