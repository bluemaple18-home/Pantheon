---
id: CARD-PANTHEON-G8-PUBLISHER-STAGE-RESTORE-CYCLE-26-20260821-RESULT
card_id: CARD-PANTHEON-G8-PUBLISHER-STAGE-RESTORE-CYCLE-26-20260821
status: blocked
terminal_state: BLOCKED / NO ACTIVATION
candidate_thread: 01a0224e-07e1-7512-abec-463ea7f38c11
---

# G23 Publisher exact-run private stage 重建結果

## 終局判定

`BLOCKED / NO ACTIVATION`

coordinator＋四 lanes 與 Publisher exact-run 的 private stage 各完成唯一一次安裝；首次 Capacity public preflight 回傳非零後依卡片停損，未執行 Capacity install，亦未 retry。因此目前是六服務的部分 stage，不符合七服務 coherent stage 的成功條件。

## 前置證據

- task HEAD：`09d6286859c8a1654c0d6129eee7918ebef6ed79`，worktree clean。
- CodeGraph：`577` files／`6,538` nodes，ready。
- runtime actor：`b1719c0d6243c7ec6372889405a846ccd1b666ed`，clean。
- manifest／identity／generation：`d1ec853fd1b32e4a77e9ab45a19a9482bad5a5c692cfc5c8396cf365a23cccbf`／`0152d79f9901b4000c43c70966907e5001846dc7792e865d9255ada62f91ebae`／`g23-b1719c0d-20260821T022959Z`。
- current readiness：capability `PASS`、Capacity `PASS`（兩週期、10 個 fail-closed cases）、official gate `READY`、missing-step fixture `BLOCKED`、`canary_created=false`、`production_mutation=false`。
- host free：`68,714,356 KiB / 239,362,496 KiB`，高於 10% 與 20 GiB 保留線。
- live 七服務：formal aggregate `PASS`，coherent G23、activation-only、全部 loaded／not running／no PID。
- Cycle25 後快照與本卡前快照：actor、origin projection、manifest、queue、exact run、translation run、state、barrier 與 live plists 全部不變。
- private stage 的七個 plist、generation、manifest digest、Publisher exact-run/max-runs 均已由 Cycle25 正常消耗；只保留 G23 readiness receipts，無未知 failure receipt。

## 執行計數

- coordinator＋四 lanes private-stage install：`1`，exit `0`。
- Publisher exact-run private-stage install：`1`，exit `0`；run=`auto-i18n-en-614aa4dc3542ab2c5637`、target=`ASTRO-BASE-01:en`、max-runs=`1`。
- Capacity public preflight：`1`，exit `1`，`preactivation_transition=rejected`。
- Capacity private-stage install：`0`。
- retry：`0`。
- activation／launchctl mutation／barrier publish／canary／Publisher child／transaction／tag／push：`0`。
- 其他六服務 business child I/O：`0`；期間僅既有 activation-only LaunchAgents 依排程輸出 G23 readiness PASS acknowledgement。

## 首次失敗與停損

Capacity transition 的第一個 fail-closed reason 為：

```text
plist canonical realpath or owner mismatch
```

同次 raw Capacity preflight 亦為 `NO-GO`，reason=`rss_telemetry_unknown`，因 Publisher 處於 loaded/no-PID 的 activation-only 安全狀態。

唯讀診斷確認目前 `TMPDIR` 是 `/var/folders/.../T/`，其 canonical realpath 為 `/private/var/folders/.../T`；Capacity installer 以 `TMPDIR` 建立暫存 plist，而 manifest validator 要求傳入 path 必須等於 canonical realpath。此 alias mismatch 足以觸發上述 transition rejection。依本卡「首次失敗停止、零 retry」契約，未用 canonical TMPDIR 重跑，也未執行 Capacity install。

## 失敗後狀態

- stage control：manifest／generation 正確，Publisher receipt 鎖定 exact run 與 max-runs=`1`。
- staged plist：六份存在；Capacity plist 不存在，因此 aggregate stage 未完成。
- Publisher staged plist formal validator：`PASS`。
- actor、origin、manifest、queue、exact run、translation run、state、barrier 與 live plists：前後不變。
- queue digest：`413a7393b3bf19d75fe45ba33d53d76bc4e42ecf4dcc3c3435b9df12ee791fab`；run count=`140`。
- state digest：`1e5ab9823ed9b333d2ab0a535f8b8fd8bc6bd9ea8b6613490b4b66a2e02bfac7`。
- live 七服務仍 coherent G23、loaded／not running／no PID。

## Evidence

- `.work/CARD-PANTHEON-G8-PUBLISHER-STAGE-RESTORE-CYCLE-26-20260821/current-readiness/readiness-summary.json`（sha256 `c9a94d3646c06dc05f3e21bad5683817e38d3968fbb28b44b804918a729c7e05`）
- `.work/CARD-PANTHEON-G8-PUBLISHER-STAGE-RESTORE-CYCLE-26-20260821/before-snapshot.json`（sha256 `929d9358265507cb4402521cafca939ac4d92b87a83597be01345962619fc3b7`）
- `.work/CARD-PANTHEON-G8-PUBLISHER-STAGE-RESTORE-CYCLE-26-20260821/capacity-preflight-output.json`
- `.work/CARD-PANTHEON-G8-PUBLISHER-STAGE-RESTORE-CYCLE-26-20260821/after-failed-capacity-preflight-snapshot.json`（sha256 `0451f6895076106f365af37685c703265baa16756984f759f522e81a26ad8b63`）

## 下一步邊界

本卡不可 retry。若主線要處理 canonical temp-path 契約，須另以新卡明確授權；在此之前保持 `BLOCKED / NO ACTIVATION`，不得以現有六服務 stage 進行 activation 或 canary。
