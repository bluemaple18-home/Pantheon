# Production stop receipt

- 判定：`NO-GO`，未進入 rewrite acceptance。
- Source／origin SHA：`b0d8b31ace6cb0c4c12b98c97129e1b97fd1b899`。
- Promotion plan：`READY_TO_APPLY`，plan digest `d8ef625cd1b5fd0e2297fef917f49aaa31484d4c5e39b67d3a329a2e109d58bd`。
- Production preflight：`publisher runtime digest 與 runtime manifest 不一致，拒絕部署`。
- 新 source 的正式 Publisher runtime digest：`0c68912d5c5f226ca65a40b2cfe057c829af2b827e0ceadda90230d5019ef4fa`。
- 錯誤 promotion input 沿用舊 digest：`77bf68e9f2dbcccbd6476a55f7ecb506d429e609ddf22dd35ce2bc105b9fa62b`。
- Rollback：同一 transaction 已回傳 `ROLLED_BACK`。
- Rollback 後 actor／manifest SHA：`387d73eef8cb525efced572f5aef772ee9a135e2`。
- 七服務：全部 `UNLOADED`。
- `transaction-ond6ep49`：仍保留，約 `106M`，未手動刪除。
- Rewrite run：selector dry-run 命中 `legacy-auto-sweep-v1-astrology-0003-astro-base-03`；未正式發布。

## 下一個唯一動作

以新 runtime digest 建立新的 exact promotion transaction；通過 Publisher deployment preflight 後，才可重新進入單筆 rewrite acceptance。
