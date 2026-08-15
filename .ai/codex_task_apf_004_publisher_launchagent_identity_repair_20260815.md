---
id: APF-004-PUBLISHER-LAUNCHAGENT-IDENTITY-REPAIR-20260815
title: 對齊 Publisher LaunchAgent runtime identity
status: ready
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: repair
cycle: 1
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
model_reason: 規格固定但涉及單一 production LaunchAgent reload 與 fail-closed rollback
parent_candidate: 891f3f4c1f
---

# APF-004｜Publisher LaunchAgent identity repair

## 使用者授權

- 使用者於 2026-08-15 明確授權修正 Gate B capacity blocker。
- 授權對象僅 `com.pantheon.agy-content-publisher`。
- 授權包含：修正其 runtime identity、bootout/bootstrap reload、失敗時自動恢復原 plist／loaded state、重驗 capacity。
- 不包含：發文、建立 run、select、transaction、tag、push、其他 LaunchAgent、排程擴量、production code 修改。

## 已確認 RED

- Gate B blocked evidence commit：`891f3f4c1f`。
- capability：四 lane PASS。
- capacity：恰好兩次 `NO-GO`，不得重播該舊失敗命令。
- live publisher：`not running`、PID absent、last exit `78: EX_CONFIG`。
- live configured actor／generation：`9d8573e9624d09748d029cab7d0209e1e14730c9`／`g2-9d8573e962-20260814T104149Z`。
- formal runtime actor／generation：`28b8b84b6dfa319d8151aac3bc1a6a819ae82aa1`／`g2-28b8b84b6d-20260815T024433Z`。
- formal manifest digest：`c57a95aa72d8e01c676e50a9a54156da04ef1f9c3b4c86fa788819200df586a2`。

## 目標／邊界

- 只把 publisher plist 與 loaded service 對齊 formal runtime manifest。
- 不修改 repository code／config／tests；只新增本卡 evidence。
- 不碰 coordinator、四 lane runner、capacity guard 或其他 service。
- 不碰使用者舊 dirty workspace。
- production publication mutation 必須維持 `0`。

## 執行契約

1. clean detached checkout exact `origin/main`，確認本卡與 blocked evidence 可讀。
2. 保存 live plist、private staged publisher plist、`launchctl print`、formal manifest、actor HEAD、queue/state 與 host capacity before snapshot；敏感值遮蔽。
3. RED-capable assertion：live publisher identity 必須不等於 formal manifest，且 blocker 可重現；不可第三次執行舊 capacity command。
4. 驗證 private staged publisher plist 已完整對齊 formal manifest、actor root、Python、queue/state/log paths、activation barrier、`max-runs` 有界；若不一致，`BLOCKED_NO_MUTATION`，不得手改 plist。
5. 鎖定 exact mutation plan與 digest：僅 publisher label。備份既有 target plist與 loaded-state evidence。
6. 以正式 macOS `launchctl bootout`／安裝已驗證 staged plist至 publisher target／`launchctl bootstrap` 執行一次 reload。不得 kickstart 重試。
7. 任一步失敗：停止；只允許一次自動 rollback，恢復原 target plist與原 loaded／unloaded 狀態；保存 failure receipt，不再 retry。
8. GREEN：`launchctl print` identity、actor、generation、manifest digest全部等於 formal manifest；服務不得是 `EX_CONFIG`；PID／active state依 plist正式語義判定。
9. 以新的 correlation/evidence root執行一次 fresh capacity preflight。必須 `PASS`；失敗即 `STOPPED_NO_RETRY`。
10. 驗證 queue/state business writes=0、publication/create/run/select/transaction/tag/push/schedule=0、其他 service identity不變。
11. 保存 JSON、stdout/stderr/exit、before/after、rollback status、capacity receipt、mutation summary、sanitizer、artifact digests；`git diff --check`。
12. candidate commit，不 amend、不 push。回 `REPAIR_PASS`、`BLOCKED_NO_MUTATION` 或 `STOPPED_NO_RETRY`。

## Evidence root

`artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/publisher_launchagent_identity_repair_20260815/`

## 後續

- 本卡不授權發文。
- Repair Reviewer APPROVED、evidence整合推上主線後，才可回原 Gate B Executor 執行唯一一篇 `new --max-runs 1` canary。
