# Pantheon runtime digest correction

- Root question：能否只修正 promotion 的 runtime digest，讓 Publisher deployment preflight 轉綠。
- Blocker：新 source digest 是 `0c68912d5c5f226ca65a40b2cfe057c829af2b827e0ceadda90230d5019ef4fa`，前次 promotion 誤用舊值 `77bf68e9f2dbcccbd6476a55f7ecb506d429e609ddf22dd35ce2bc105b9fa62b`。
- 唯一改動：新 transaction 使用新 digest。
- 不重跑：capability package、兩週期容量、測試、其他 lane。
- 驗收：promotion `POSTCHECK_PASSED`，Publisher exact rewrite deployment preflight `PASS`。
- 停止：若上述 preflight 再失敗，立即 rollback；不啟動服務、不發布。
