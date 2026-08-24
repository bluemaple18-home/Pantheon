# Command receipt

## Git / source authority

- remote query 命令層 invocation 共 `2` 次：第一次在 DNS resolution 失敗，第二次成功回傳 `refs/heads/main = 5a9103785ebfc8d5a28fa8188def6069beb12d88`。
- 因卡片上限為一次，`bounded-query contract = FAIL`；不以「只有一次連線成功」改寫為 PASS。
- 第二次成功後未再執行 remote query、fetch、pull、push、tag 或 ref mutation。
- release `v0.3.370^{}` = `b0950d4c436cc902e17ac110b579b35b84aa53e4`。
- current local main / task HEAD = `a0391c298a4eff80be113c2a06c03529cd2dcbf6`；local `origin/main` = remote query SHA，僅作交叉佐證。
- production actor / manifest actor = `db9fb4343df212fd3b65546b017aba159620a058`。
- release 到 remote main 只有三個 docs/handoff paths，runtime-affecting 與 unknown 均為空。
- remote main 與 local main 互不為 ancestor；兩組已知重放 commits patch-id 等價，但 patch-id 沒有被升格為 remote authority。

## Formal reconciler

- 使用 local-only detached source worktree，HEAD 精確等於 remote main；未修改主工作區 HEAD 或 refs。
- 正式入口：`python -m scripts.pantheon_g8_production_preactivation`。
- `required_source == origin_main == 5a910...`，actual changed paths 為 `[]`，因此 exact/minimal allowlist 也是 `[]`；無需且不得新增擴權 pattern。
- 結果：`BLOCKED / ACTOR_MANIFEST_AUTHORITY_MISMATCH`，已越過 `ALLOWLIST_REQUIRED`、`LOCAL_HEAD_MISMATCH`、`REMOTE_DIVERGED`、`SOURCE_DRIFT`。
- formal internal mutation tripwire：`PASS`，changed `[]`。

## Promotion plan

- 入口與 deterministic receipt 見 `promotion-plan-command.md`。
- target runtime digest = current manifest runtime digest = `5554e075b0a6dcf97dd1cf431544c3456677b5d81174dcb8d660566dd82d5c92`。
- 既有 capacity receipt 通過 `_validate_capacity_receipt`；digest `7fa0036a4ce81a173bc1f16c964829d82822d9fa6a3bb4c92793b222d4954f34`。
- plan 結果 `READY_TO_APPLY`，plan digest `e4d385214ccc09318be454e8c21a8c213d1cb1d126ed41a7e08a1c3a08422f1c`。
- `READY_TO_APPLY` 只表示技術 plan 可審查；沒有 human authorization，也未產生 transaction receipt、rollback bundle、barrier 或 production file。

## Tool classifications

- `.venv/bin/python` 不存在：`TOOLCHAIN_PATH_MISSING`；改用 runtime manifest locator，未建環境。
- bounded `rg` exit `1`：`NO_MATCH`；未把它當 runtime failure，也未盲測同一查詢。
- plan `/tmp` path alias：`PLAN_INPUT_PATH_ALIAS`；改為 canonical `/private/tmp` 後固定成功。

## Verification

- 受影響 tests：formal reconciler 與 promotion plan 兩個 test files，`68 passed in 19.36s`。
- runtime Python 與 PATH 均沒有 pytest；未下載依賴，改用已存在的 main workspace `.venv`。
- 所有 task-owned JSON parse、helper AST parse、evidence digest 與 staged `git diff --check` 由 `verification-receipt.json` 鎖定。
