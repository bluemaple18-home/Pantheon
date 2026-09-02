# Pantheon C-C/T Continuous Authority Root｜Fresh GPT Review

## Verdict

`FRESH_FINAL_REVIEW_NO_GO`

本文件是 Repair-2（2/2）後的獨立唯讀審查結果。它不代表候選可合併，也不宣告 `C-C_T_REVIEW_GO`。

## Lineage 與審查邊界

- accepted base：`4e68b28ed031bddafa898905880c68982944730b`
- review branch：`codex/pantheon-cct-continuous-authority-root-20260902`
- 審查範圍：Controller、focused tests、CARD／RESULT／RAW evidence。
- 未執行：真 launchctl、provider、Gate D/E、production/public mutation、deploy、merge。

## Blocking findings

### P1｜持有期間未持續重驗 owner-safe 權限

- category：security／path authority
- location：`scripts/pantheon_four_lane_disposable_acceptance_cohort.py:118`、`:195`
- evidence：`RetainedDirectory.verify()` 與 `RetainedFile.verify()` 只重驗類型與 device/inode；capture 後將 directory 改為 `0777` 或 file 改為 `0666` 仍會通過。
- risk：continuous authority 可在生命週期中失去 owner-safe 性質；mutable stdout/stderr 可能被其他使用者寫入同一 inode，再被 Controller 當成可信 read-back。
- required next-root seam：每次 directory/file verification 同時重驗 `st_uid == os.getuid()` 與 `mode & 0o022 == 0`，並以 capture 後 chmod/chown drift RED 證明。

### P1｜steps cleanup 仍有 verify→delete rebind race

- category：correctness／security race
- location：`scripts/pantheon_four_lane_disposable_acceptance_cohort.py:429`
- evidence：cleanup 先驗 steps，之後才 rename generation、列舉 pinned steps fd，最後以名稱刪除 `steps`；若期間移走 pinned steps 並補入空 rebound steps，流程可刪除 rebound、遺失 pinned authority，卻回報成功。
- risk：違反 rebound／external 不刪與 residue-free 契約，可能產生錯誤 PASS。
- required next-root seam：先用 dirfd 原子 quarantine steps、核對 quarantine identity，再只清除 pinned subtree；原名稱 rebound 必須 fail closed 且保持不動。

### P1｜UID home 之前的 ancestor chain 未逐層固定

- category：security／path authority
- location：`scripts/pantheon_four_lane_disposable_acceptance_cohort.py:87`
- evidence：`open_absolute()` 對完整 UID-home path 單次使用 `O_NOFOLLOW`，只保護最後 component；ancestor symlink 下的普通 home leaf 仍可被接受。
- risk：production `Library/LaunchAgents` authority 可建立在非 canonical ancestor chain，違反完整 non-symlink root invariant。
- required next-root seam：從 filesystem root 以 retained dirfd 逐 component、`O_NOFOLLOW` 開啟 UID home，或提供等價且無 path-resolution race 的完整 ancestor-chain 證明。

## Verified evidence

- focused cohort：`46 passed`
- manifest＋runner affected：`118 passed`
- `py_compile`：PASS
- `git diff --check`：PASS
- frozen source SHA256：`51fef38e8a91a3b81223a850428239b0f7fd7f95fb19401bd4cd51cff0886951`
- frozen tests SHA256：`97730e399a964e8e7dd47139b99254207a13ad8344ed3a2106d8efb4637d68fa`

測試通過不抵銷上述三個 P1。Repair budget 已達 2/2，依卡片規則禁止 Repair-3；若要繼續，必須建立新的 architecture root。
