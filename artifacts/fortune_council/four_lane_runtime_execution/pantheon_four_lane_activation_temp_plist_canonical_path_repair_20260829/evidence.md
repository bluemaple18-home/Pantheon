# Bounded Evidence

- Base: `origin/main=6541693e929a20cbcffe8b070085b5f1caec7a92`。
- RED: `test_capacity_installer_canonicalizes_var_tmp_plist_for_preactivation_transition` 在移除 canonicalization 的暫態版本失敗，錯誤為 `plist canonical realpath or owner mismatch`。
- GREEN: 同測試於最終版本通過，並驗證 `/var` alias 與 `/private/var` canonical directory 同 inode、stage 檔存在、fake launchctl mutation log 不存在、temp residue 為零。
- 回歸：capacity 69/69、runtime manifest 50/50、合計 119/119；shell syntax、Python compile、diff check 均通過。
- 外部狀態：未呼叫 production/install/activate/canary；無 commit/push/tag/deploy。
