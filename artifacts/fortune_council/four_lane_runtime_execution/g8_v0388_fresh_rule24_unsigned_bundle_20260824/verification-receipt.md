# V0388 fresh Rule24 unsigned bundle 驗證

- 正式入口：`<repo-root>/.venv/bin/python -m scripts.pantheon_writer_vnext_runtime_activation_capacity bundle ...`，exit `0`。
- Baseline：`d4b3921151d5b4d0cfe6f4a5c538d79d521c4b48`；V0387 source integration：`6868151310`。
- Fresh correlation：`20260825T000000Z-pcD2QO`；量測 epoch 範圍 `1787588081.8679612` 至 `1787588105.027563`。
- Summary：`status=PASS`、`cycle_count=2`、`signed=false`、`production_mutation=false`、`canary_created=false`。
- Semantic verifier：PASS；兩 cycle 皆為完整七 capability、相同 actor/runtime identity、固定 cycle-specific execution/correlation，cleanup root 不存在且回收 bytes/files 皆大於零。
- Rule24：policy bounded、host reserve、retention projection、RSS/swap growth、reclaim、cleanup、stop-loss 全部 PASS。
- Exact-byte copy：三個 bundle artifacts 與 task-root 原檔 `cmp` PASS；SHA-256 與 byte length 均和 CLI summary 一致。
- Capacity pytest：`25 passed in 0.15s`。
- Production mutation count：`0`；未建立 canary，未簽署，未執行 remote、promotion、apply、deploy、push 或 tag。
- Task root lifecycle：`/private/tmp/pantheon-v0388-20260825T000000Z-pcD2QO` retained；final evidence retained，final sandbox 已清空 cycle descendants。輸入 brief 被 validator 拒絕的前次 local attempt 保留於 task-owned `attempts/attempt-2-input-blocked/`，不構成本次 PASS bundle。
