# Gate C G3 wrong-mode result

`G3_GREEN`。baseline `1 passed in 0.35s`，test-only strengthening 後 target `1 passed in 0.36s`。`brief-wrong-mode` 得到 rejected receipt／returncode 1；fixture snapshot 僅容許 execute path 的單一 empty identity-lock，`atomic_write_json` spy 為零。provider/service/network/production mutation 均為 0。
