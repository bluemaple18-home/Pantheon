---
id: APF-004-PUBLISHER-INSTALLER-MANIFEST-AUTHORITY-REPAIR-20260815
title: 修正 Publisher installer 的 promoted actor authority 契約
status: ready
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: repair
cycle: 2
thickness: core-bounded
risk: high
model: gpt-5.5
reasoning: high
model_reason: 規格固定，需修正 fail-closed runtime identity 契約並補回歸測試
parent_candidate: 30a3335b73
---

# APF-004｜Publisher installer manifest authority repair

## 已核准 finding

- Reviewer 已 APPROVED candidate `a2662dd97c14e59ba21e0fdc52a1d7957621e02c`，無 P0/P1。
- Formal runtime actor HEAD：`28b8b84b6dfa319d8151aac3bc1a6a819ae82aa1`。
- Formal manifest digest：`c57a95aa72d8e01c676e50a9a54156da04ef1f9c3b4c86fa788819200df586a2`。
- Promoted actor 是乾淨、detached、且 HEAD 等於 manifest `actor_head`；其 remote-tracking `origin/main` 為較新的 `79bdc809...`。
- `scripts/install_agy_content_publisher_launchd.sh --preflight` 目前要求 `HEAD == origin/main`，在 staged plist 產生前錯誤拒絕已被 immutable manifest 鎖定的合法 promoted actor。

## 目標

- Publisher installer 的 actor authority 以 exact runtime manifest `actor_root + actor_head + runtime digest` 為準。
- 不再以可漂移的 remote-tracking `origin/main` 作為 promoted runtime 的部署等值條件。
- actor dirty、HEAD 與 manifest `actor_head` 不同、runtime digest 不符、manifest digest 不符時仍須 fail closed。

## 可改檔案

- `scripts/install_agy_content_publisher_launchd.sh`
- 直接相關的 `tests/test_agy_content_publisher.py`
- 如契約測試確有必要：`tests/test_pantheon_content_runtime_manifest.py`
- 本卡指定 evidence：`artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/publisher_installer_manifest_authority_repair_20260815/`

## 禁止範圍

- 不修改其他 installer、runtime manifest schema、promotion implementation、plist template、排程或其他 LaunchAgent。
- 不執行 install、bootout、bootstrap、kickstart、capacity、publish、create run、select、transaction、tag、push。
- 不碰 production runtime、queue/state、使用者舊 dirty workspace。

## 驗收

1. 先建立 RED：乾淨 detached actor 的 `HEAD == manifest.actor_head`，但 `origin/main != HEAD`；舊 installer 必須失敗。
2. 最小修正後該案例 PASS，且不需要改寫或 fetch remote-tracking ref。
3. 負向矩陣至少包含：dirty actor、HEAD != manifest actor_head、缺失／無效 actor_head、runtime digest mismatch；全部 fail closed。
4. installer 仍只 stage private plist，不自行 bootstrap。
5. 執行受影響測試、`bash -n scripts/install_agy_content_publisher_launchd.sh`、`git diff --check`。
6. Evidence 記錄測試命令／結果、變更 allowlist、production mutation `0`、sanitizer 與 digests。
7. candidate commit，不 amend、不 push；回 candidate SHA、測試、diff、clean。

## 後續

- Reviewer APPROVED 並整合上主線後，才回原 Repair thread 重新執行已授權的單一 Publisher identity repair。
- 本卡不授權任何 production mutation 或發文。
