---
id: CARD-PANTHEON-G8-CYCLE17-PREFLIGHT-NO-GO-PARAMETER-RCA-20260821
chain_id: PANTHEON-G8-PRODUCTION-READINESS-20260820
parent_card_id: CARD-PANTHEON-G8-CYCLE17-FORMAL-PREFLIGHT-CONTRACT-REPAIR-20260821
role: diagnostic
cycle: 2
status: ready
type: readonly_diagnostic
thickness: minimal
risk: medium
model: gpt-5.6-luna
reasoning: medium
model_reason: blocker與既有成功證據都已固定，只需限域比對argv、TMPDIR、plist與launchd狀態契約。
ownership:
  - .work/CARD-PANTHEON-G8-CYCLE17-PREFLIGHT-NO-GO-PARAMETER-RCA-20260821/**
forbidden_scope:
  - 修改source、tests、cards、rules、runtime manifest、plist、LaunchAgent、queue、state或logs
  - 執行public preflight、direct module、capacity exercise、launchctl mutation或production動作
  - Gate A、push、promotion、restaging、activation、canary、lane、Publisher、tag、publish
verification:
  - CodeGraph-first；失敗才限域rg
  - 對帳本次NO-GO與既有TMPDIR=/private/tmp PASS證據
  - plist blocker與loaded_service_pid_missing因果分開判定
  - 只交一個root cause與一個exact recovery argv，或BLOCKED
  - production mutation=0、git diff --check、evidence commit
evidence_path: .work/CARD-PANTHEON-G8-CYCLE17-PREFLIGHT-NO-GO-PARAMETER-RCA-20260821/
---

# Cycle 17 preflight NO-GO parameter RCA

## 工作名稱 → 正在做什麼 → 現在狀態

診斷 Cycle 17 public preflight NO-GO → 判定是否為缺少`TMPDIR=/private/tmp`及current service狀態契約 → `READY / READ ONLY`

## Root Question

唯一一次 public installer preflight 為何同時回報`plist canonical realpath or owner mismatch`與`loaded_service_pid_missing:com.pantheon.agy-content-publisher`；是否存在不改source、不改manifest、只修正正式argv/gate ordering的唯一安全恢復路徑？

## 鎖定證據

- NO-GO evidence commit：`ef2cdf9e47`。
- 本次 invocation 未設定`TMPDIR`。
- 既有卡片記錄：`TMPDIR=/private/tmp`後正式preactivation transition曾回`accepted/PASS`。
- current manifest digest：`db6cc697831947734c86b76e3e0054309d0854aacb7d55044cc559e02f1e24bb`。
- current actor：`88c6c0a95a013d0e9e8ab84c1a0f75a58ada1ff5`。
- 本次 public preflight count已是1；本卡不得再執行。

## 執行契約

1. 只讀比對installer、manifest validation、capacity telemetry tests及既有accepted transition證據。
2. 判定plist mismatch是否由temp plist路徑非canonical/owner造成，並以source/test證據支持或否證。
3. 判定Publisher no-PID是同一根因的下游結果，或是必須先完成合法activation/reload才可取得RSS的獨立gate-order狀態；不得把兩者混成一個修補。
4. 若為parameter/gate-order recovery，交唯一exact argv與前置狀態，標明下一次正式preflight應在何時執行；本卡不執行。
5. 若需要source或runtime mutation才能判定，交`BLOCKED / SOURCE OR RUNTIME REPAIR REQUIRED`與最小allowlist；不得自行擴scope。
6. 保存假說、證據定位、verdict、invocation/mutation counts；`git diff --check`後提交candidate。

## 停損

- 禁止試跑第二次preflight。
- 禁止`launchctl load/bootstrap/kickstart`或修改plist ownership/mode。
- 只可交`PARAMETER RECOVERY`、`GATE ORDER RECOVERY`或`SOURCE OR RUNTIME REPAIR REQUIRED`其中一種。
