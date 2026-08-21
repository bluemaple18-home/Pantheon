---
id: CARD-PANTHEON-G8-REPAIRED-SOURCE-PROMOTION-STAGING-CYCLE-17-20260821
status: ready
chain_id: PANTHEON-G8-PRODUCTION-READINESS-20260820
role: implementation
cycle: 17
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定 SHA 的 production push 與 runtime restaging；mutation authority 與停止條件必須嚴格鎖定。
---

# 推送 G8 修復版並重建 staging（Cycle 17）

## 工作名稱 → 正在做什麼 → 現在狀態

`G8 修復版 promotion staging` → 驗證 Gate A 後單次 fast-forward push 與 runtime restaging → `READY / NO CANARY`

## 已解除 blocker

- Cycle 16 receipt 是 **bounded synthetic capacity safety gate**，不是 formal runtime identity preflight，兩者不得混稱或互相替代。
- Cycle 16 capacity receipt：`.work/CARD-PANTHEON-G8-HOST-SWAP-CAPACITY-EXERCISE-CYCLE-16-20260821/capacity-receipt.json`
- receipt SHA256：`3773594ff3e3dea71902ff122b280818b91fb826659570606e45f34b6fc3f6ce`
- receipt `status=PASS`、兩輪 RSS/swap telemetry available、`production_mutation=false`。
- evidence 保存 commit：`53f5479449`。
- 本卡不得重跑 capacity exercise；只驗證上述 receipt。target formal public preflight 必須依下列獨立 authority、時點與單次契約執行。

## 鎖定 authority

- source SHA：`c05929f2a7dac86e94aaeaa5ab6c5455892f5f77`
- expected actor SHA：`88c6c0a95a013d0e9e8ab84c1a0f75a58ada1ff5`
- expected remote SHA：`88c6c0a95a013d0e9e8ab84c1a0f75a58ada1ff5`
- tooling Python source：`<repo-root>/.venv/bin/python`。此路徑只供 discovery，不是可寫入 plan、manifest、formal argv 或 receipt 的 runtime identity。任何 Gate A、plan/apply 與 promotion tooling 前，必須先以 `realpath(3)` 解析並保存 canonical executable evidence；不得放寬 source 的 canonical-realpath check。
- 本次 evidence 鎖定 canonical Python realpath 為 `/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12`、版本為 `Python 3.12.12`、executable SHA256 為 `d7e27bef360beb2146e27f6d7edf7dac70e5cbc3a800c15369a0eb73bcea33ae`。新 host/worktree 不得沿用字串猜測；必須由 `<repo-root>/.venv/bin/python` 重新解析並證明 realpath、版本與 digest，任一不符立即 `BLOCKED / NO CANARY`。
- Gate A public CLI：以 evidence 鎖定的 canonical Python literal 執行 `-m scripts.pantheon_gate_a_governance ...`；禁止把 `<repo-root>/.venv/bin/python` symlink 放入 exact argv artifact。
- transaction root：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/transactions/g8-repaired-source-promotion-staging-cycle-17-20260821`

### Target formal public preflight authority

- public seam 唯一為 authoritative actor 內的 `scripts/install_pantheon_content_capacity_guard_launchd.sh --preflight`；禁止 direct module、file-path Python module 或其他 wrapper。
- execution actor 必須已由 promotion postcheck 證明為 target SHA `c05929f2a7dac86e94aaeaa5ab6c5455892f5f77`，installer 必須來自該 actor root。
- manifest 必須是 promotion plan 的 `target_manifest_digest` 所指向、apply/postcheck 已 materialize 的 authoritative manifest；plan、postcheck 與 argv 三者 digest 必須完全相同。
- `PANTHEON_PYTHON_PATH` 必須等於該 target manifest 的 canonical `python_executable`，並與 plan request、apply argv、postcheck 及 canonical Python evidence 的 realpath literal 完全相同。`<repo-root>/.venv/bin/python` 只代表 tooling source；symlink 本身永遠不得成為 manifest-bound runtime authority。
- argv 必須含 canonical `TMPDIR=/private/tmp`；禁止省略、使用 `/tmp` 或讓 shell fallback。
- plan 後先產生 exact argv artifact；下列 `<target_manifest_digest>` 必須在建立 formal preflight authorization 前替換成 plan 輸出的 64 位 literal，execution artifact 不得保留 placeholder：

```text
/usr/bin/env
TMPDIR=/private/tmp
PANTHEON_USER_HOME_DIR=/Users/mattkuo
PANTHEON_PYTHON_PATH=/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12
PANTHEON_RUNTIME_MANIFEST_FILE=/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json
PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST=<target_manifest_digest>
/bin/bash
/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor/scripts/install_pantheon_content_capacity_guard_launchd.sh
--preflight
```

- formal preflight authorization 必須是本次修正後全新、單次且綁定 exact argv digest、target actor SHA、manifest path/digest、canonical Python realpath、`Python 3.12.12` 與 executable SHA256 的 artifact；先前 public preflight count=`1` 已消耗，不得重用其 authorization 或計數。

## 固定 gate order

1. 驗證 Cycle 16 bounded receipt 的 path、SHA256、payload、兩輪 telemetry、reclamation、stop-loss 與 `production_mutation=false`；不得重跑 exercise。
2. 先從 `<repo-root>/.venv/bin/python` 解析 canonical realpath，驗證 regular executable、`Python 3.12.12` 與 executable SHA256，保存 immutable evidence；再以該 canonical literal 執行 zero-write deterministic promotion plan，鎖定 `target_manifest_digest`、exact apply argv 與 exact formal preflight argv。舊的 symlink-path NO-GO plan 不得重用；新 plan 首次非 PASS 即停止。Gate A authorization 與 formal preflight authorization 必須分離。
3. 依原契約執行唯一 Gate A、單次 fast-forward push、promotion apply/postcheck/finalize；任一步非 PASS 立即停止。apply/postcheck 必須先 materialize 並證明 target actor、manifest、digest、Python、barrier 與 readiness tuple。
4. 使用 authoritative target actor 的既有 public installers，先依序 restage coordinator＋四 lanes，再 restage Publisher，形成與 target manifest 完全一致的六服務 stage、stage metadata、`publisher-max-runs=1` 與 exact Publisher run receipt；live 仍維持 coherent activation-only loaded/no-PID，禁止 activation/reload。
5. 在 capacity plist 尚未寫入 private stage 前，以全新 authorization 執行上述 exact `--preflight` **一次**。Publisher `loaded_service_pid_missing` 是 preactivation transition 的預期輸入；不得先 activation/reload 取得 PID。exit 非 `0`、JSON 非 `PASS/accepted`、tuple 或 telemetry 任一不符時立即停止，不換入口、不重試、不執行 capacity install。
6. 只有 formal preflight PASS 後，才可依原七服務 restaging authority 執行 capacity installer `--install`，寫入第七份 staged plist。`--install` 內建的 install-side 安全重驗是 mutation 前 fail-closed revalidation，不得用來重試或掩蓋第 5 步失敗。
7. 驗證七服務 staged coherent、live 未變、queue 完整且仍無 activation/canary/publish/tag；不得把 staged 狀態回報為 activated。

## 允許

1. 唯讀 current capability、Cycle 16 bounded receipt、remote/actor/manifest/stage/queue、release dry preflight。
2. deterministic promotion plan 與 exact apply argv。
3. 建立本卡全新的 Gate A authorization/state，以及彼此分離的單次 formal preflight authorization；只執行一次 Gate A module invocation。
4. Gate A `READY` 後執行一次普通 fast-forward push：`c059...:refs/heads/main`。
5. remote 精確成為 `c059...` 後，依「六服務 restage → 單次 formal public preflight → capacity install」順序執行正式 promotion apply/postcheck/finalize 與七服務 restaging；不得 activation。
6. 寫本卡專屬 evidence。主線負責保存 commit；task 不得因 git index 權限改用 alternate index/object store。

## 禁止

- 禁止 system Python、file-path Gate A 入口、新 venv、第二次 Gate A invocation；禁止把 `<repo-root>/.venv/bin/python` symlink 當作 plan、manifest、formal argv 或 receipt 的 executable identity。
- 禁止重跑 capacity exercise、mock telemetry、降低安全門檻。
- 禁止用 current actor/current manifest 的舊 preflight 代替 target formal public preflight；禁止省略 `TMPDIR=/private/tmp`。
- 禁止重用已消耗的 formal preflight authorization；第一次 formal preflight 非 PASS 即停止，不得以 `--install`、activation/reload、換入口或第二次 `--preflight` 重試。
- 禁止 force push、第二次 push、source/tests/config/workflow 修補。
- 禁止 activation、canary、lane run、Publisher transaction、tag、publish。
- 禁止 alternate index/object store、`git commit-tree`。
- 禁止重用舊 transaction root、authorization 或 state。
- 任一 current gate、receipt hash、remote/actor identity、plan、Gate A、push postcheck 或 promotion postcheck 非 PASS：立即停止，不換入口、不重試。

## 驗收

- Cycle 16 capacity receipt hash 與 PASS 契約精確符合。
- Cycle 16 bounded receipt 與 target formal public preflight 在 evidence/counts 中分欄，沒有混稱。
- 唯一 Gate A module invocation：exit 0、JSON `status=READY`、`apply_calls=0`、`production_mutation=0`。
- push：before=`88c6...`、after=`c059...`，一次普通 fast-forward。
- canonical Python evidence：tooling source 為 `<repo-root>/.venv/bin/python`，formal identity 為已驗證 realpath literal，版本精確為 `Python 3.12.12`，executable SHA256 與 plan/apply/manifest/preflight authorization 完全一致。
- formal public preflight：全新 authorization、exact argv 含 `TMPDIR=/private/tmp`、authoritative target actor/manifest/digest/manifest-bound canonical Python，invocation=`1`，exit `0` 且 transition `PASS/accepted`；若非 PASS，本卡交付 `BLOCKED / NO CANARY` 且 capacity install count=`0`。
- actor/manifest/private stage 轉為 target authority；七服務 staged coherent，live 保持 preactivation 狀態。
- queue 既有 run IDs 完整保留；無 activation、canary、publish、tag。
- `git diff --check`。

## 交付

- `STAGED / NO CANARY` 或 `BLOCKED / NO CANARY`。
- evidence：`.work/CARD-PANTHEON-G8-REPAIRED-SOURCE-PROMOTION-STAGING-CYCLE-17-20260821/`
- 回報 evidence manifest SHA256、remote before/after、actor/manifest/stage/generation、七服務 staged/live，以及 Cycle 16 receipt validation、formal preflight、Gate A、push、promotion、capacity install、production mutation 的分離 counts。
