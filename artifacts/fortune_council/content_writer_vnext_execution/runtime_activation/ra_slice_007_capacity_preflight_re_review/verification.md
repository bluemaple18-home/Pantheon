# RA007 P1 Repair Re-review 驗證

## PASS

- JSON parse：resource snapshot、inventory、cleanup plan。
- interval：`11:53:58Z - 11:53:55Z = 3` 秒，符合 `1..300`。
- 四個 runtime 欄位：兩個 sample 全部非空。
- formal reserve：`max(20 GiB, ceil(host total * 10%))=24,510,719,591` bytes；兩筆 deficit 都是 0。
- deltas：host free=`+1,085,440`、RSS=`-87,883,776`、swap=0，與 receipt 一致。
- inventory：7 rows、sum bytes=`2,124,804,096`、eligible sum=0、reclaimable=0。
- cleanup：`actions=[]`、`delete_authority=none`。
- portable path、allowlist 與 `git diff --check e7bb39fd..1f7f1daa`：PASS。

## FAIL：digest 可重算

對每個 sample 移除 `measurement_digest` 後，以 stable JSON（sorted keys、UTF-8、compact separators）計算 SHA-256：

| sample | computed | committed |
| --- | --- | --- |
| 11:53:55Z | `sha256:90ee05cbab769ea5fe906ce9d79e3ef7e0cfc82e3d09011c57e8edafdfe2489d` | `sha256:40f6977540af702a0af3f9b1393d105bc6432a289a023a9a25af28e5ed02358c` |
| 11:53:58Z | `sha256:7e6ed80314cf458d93c7470409e885739e0311e2c62851d991c2a45ed7ad1fbf` | `sha256:7b9f7e7c944bc15e3dc020762d671385177437d371786af0d632d26f2309de21` |

`<ai-core>/scripts/visible_thread_resource_guard.py` 的 canonical receipt algorithm uses a versioned domain plus the complete snapshot. The committed evidence does not retain that complete portable projection or state an alternate measurement digest algorithm, so neither digest can be reconstructed.
