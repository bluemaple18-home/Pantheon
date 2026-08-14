# APF-004 Gate 2 inert live plist authority integration evidence

- base：`d3f621d9849cfef1857b9765914243210ed12e79`
- candidate：`91c2c4c74a5827e6a06ef3f8994f1208c385ddc1`
- review：`REVIEW_GO`；無 P0/P1
- integrated repair commit：`4668178563`
- installer／test blobs與candidate完全一致
- affected coordinator：`59 passed, 113 deselected in 131.80s`
- targeted 34 cases由affected selector完整涵蓋，未重複執行
- runtime manifest：`42 passed in 2.25s`
- 三 installer `bash -n`：PASS
- `git diff --check`／`git show --check`：PASS
- binary numstat：全部文字檔
- production mutation／push／發文：false
- 結果：`INTEGRATION_PASS`
