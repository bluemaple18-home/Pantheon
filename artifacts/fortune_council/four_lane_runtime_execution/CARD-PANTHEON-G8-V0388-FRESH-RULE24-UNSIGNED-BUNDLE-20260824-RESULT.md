---
id: CARD-PANTHEON-G8-V0388-FRESH-RULE24-UNSIGNED-BUNDLE-20260824-RESULT
verdict: DELIVERED_CANDIDATE
---

# V0388 fresh Rule24 unsigned bundle result

## 結果

以 baseline `d4b3921151d5b4d0cfe6f4a5c538d79d521c4b48`、V0387 source integration `6868151310` 的正式 CLI，在唯一 task-owned root `/private/tmp/pantheon-v0388-20260825T000000Z-pcD2QO` 實跑 fresh two-cycle bundle。CLI exit `0`，summary 為 `PASS`、兩週期、unsigned、零 production mutation、未建立 canary。

## Exact-byte artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `capacity-receipt.json` | 4685 | `776ae80fd611bb85b3693a1629176dc9d137c81b51d16fda62e6c3d200391ad4` |
| `cycle-1-measurements.json` | 1651 | `669c6fc5b23d0ce88462a6bdd558c915d182788c91e853c6e38ee9a41bcc15e3` |
| `cycle-2-measurements.json` | 1650 | `b1ab2cfe0d928a1d8de975c4912752117bea51fe5ae1507ce723fe874fd1441e` |

三份 artifact 已 exact-byte 複製至 `g8_v0388_fresh_rule24_unsigned_bundle_20260824/`，並以 `cmp`、SHA-256、byte length 對 CLI summary 完整核對。該目錄另保留 portable machine-readable argv、原始 inputs、summary、execution、digest manifest 與 verification receipt。

## 驗收

- Fresh correlation：`20260825T000000Z-pcD2QO`；量測 epoch `1787588081.8679612` 至 `1787588105.027563`。
- Bounded policy：`max_bytes=67108864`、`max_file_count=1024`、`sampling_interval_seconds=300`，retention、RSS/swap、host reserve、reclaim 與 stop-loss 欄位均保留並通過。
- Semantic verifier：兩 cycle 皆 PASS，七 capability 完整，actor/runtime identity 一致，固定 cycle-specific correlation；cleanup/reclaim 與 retention projection PASS。
- Capacity tests：`25 passed in 0.15s`。
- JSON parse、digest manifest、exact-byte comparison 與 `git diff --check`：PASS。
- Production mutation count：`0`。

## 邊界與 lifecycle

Task root retained；final evidence retained，final sandbox 的 cycle descendants 已清空。Detached worktree 缺 `.venv` 的 exit `127` 僅是 interpreter path preflight miss，非 Rule24 verdict；其後依監工指示使用 baseline-matched main venv interpreter、保持目前 worktree cwd。被 validator 拒絕的初始 brief attempt 保留在同一 task root 的 `attempts/attempt-2-input-blocked/`，未納入 PASS bundle。

本卡未簽署、未取得 production authorization，亦未宣稱可 apply；未執行 production actor／manifest／state／transaction、remote、promotion、deploy、canary、activation、LaunchAgents、push 或 tag。
