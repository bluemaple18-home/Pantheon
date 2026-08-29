# Pantheon New Lane Stale-Success Terminalization — 獨立 Review Card

## 目的

獨立審查 `terminalize-stale-succeeded-writer` bounded repair，判定是否可放行，並對 coordinator 完整 suite 的 `378 passed, 8 failed` 做 baseline/HEAD 歸因。

## 可讀範圍

- RCA 與 Repair `RESULT.md`、receipts、fixtures
- `scripts/agy_gemini_coordinator.py` 本次 diff 與關聯既有接縫
- `tests/test_agy_gemini_coordinator.py` 本次 diff 與 coordinator suite
- git history / baseline 只讀比較

## 可寫範圍

- 本 review card
- 同目錄下本 review 的 `RESULT.md` 與 evidence artifacts

## 禁止範圍

- 不修改 source/tests
- 不 commit、push、deploy、production、plist
- 不呼叫 provider、reviewer、publisher

## P0/P1 驗收問題

1. hash-bound、receipt-first、crash-safe、idempotent terminalization 是否只處理 succeeded-but-unconsumed 的 new Writer job，且 archive/inbox/attempt/writer-operation bytes 不變。
2. drift、ambiguity、wrong lane、missing files、symlink、candidate、reviewer、publish boundaries 是否 fail closed。
3. state transition 是否不猜 mapping、不建立 second authority；scheduler frontier 是否只 dry-run。
4. provider / reviewer / publisher invocation 是否為 0。
5. `378 passed, 8 failed` 的 8 failures 是否由 candidate diff 造成；任一 regression 即 `NO_GO`。

## 必跑驗證

- exact、negative、affected coordinator tests
- 完整 coordinator suite，並保存失敗 node IDs / traceback
- baseline/HEAD 或精準 history/fixture 比較
- `py_compile`
- `git diff --check`
- source budget

## 交付

- verdict：`GO` 或 `NO_GO`
- findings（依 P0/P1/P2/P3）
- acceptance mapping 與可重現證據路徑
- exact commit allowlist
- remaining risk / next step
