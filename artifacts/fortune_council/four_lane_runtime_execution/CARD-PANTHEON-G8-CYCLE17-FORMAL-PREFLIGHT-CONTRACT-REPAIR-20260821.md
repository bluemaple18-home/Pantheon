---
id: CARD-PANTHEON-G8-CYCLE17-FORMAL-PREFLIGHT-CONTRACT-REPAIR-20260821
status: ready
chain_id: PANTHEON-G8-PRODUCTION-READINESS-20260820
role: repair
generation: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 正式 runtime manifest、interpreter authority 與 production gate ordering 的固定契約修復。
---

# 修復 Cycle 17 正式 capacity preflight 契約

## 工作名稱 → 正在做什麼 → 現在狀態

`Cycle 17 formal preflight contract repair` → 消除錯誤 direct-module preflight 與 interpreter／manifest 循環依賴 → `READY / NO PRODUCTION MUTATION`

## RED 證據

- Cycle 17 evidence：`.work/CARD-PANTHEON-G8-REPAIRED-SOURCE-PROMOTION-STAGING-CYCLE-17-20260821/`
- 已執行 RED：direct module formal preflight → `RuntimeManifestError: formal runtime environment is incomplete`。
- Cycle 16 bounded exercise 已 PASS；不得重跑。
- current manifest：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json`。
- current manifest digest：`db6cc697831947734c86b76e3e0054309d0854aacb7d55044cc559e02f1e24bb`。
- current actor/head：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor` / `88c6c0a95a013d0e9e8ab84c1a0f75a58ada1ff5`。
- current manifest python：`/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/bin/python3.14`。
- target task python：`/Users/mattkuo/Documents/Pantheon/.venv/bin/python` → Python 3.12.12。
- public seam：`scripts/install_pantheon_content_capacity_guard_launchd.sh --preflight`；它會完整建立 formal runtime env，且測試鎖定 preflight 無 target/control-plane mutation。

## 目標

以 source/tests/manifest/installer 證據判定 canonical gate ordering 與 interpreter authority；更新 Cycle 17 卡，鎖定 exact public argv。若不存在同時滿足 formal manifest 與 Python policy 的合法命令，交付 authority conflict；禁止繞過。

## 可改

- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-REPAIRED-SOURCE-PROMOTION-STAGING-CYCLE-17-20260821.md`
- 本卡專屬 `.work/CARD-PANTHEON-G8-CYCLE17-FORMAL-PREFLIGHT-CONTRACT-REPAIR-20260821/` 文字證據。

## 禁止

- 禁止修改 source、tests、scripts、config、manifest、plist、runtime actor、queue/state/logs。
- 禁止重跑錯誤 direct-module RED、capacity exercise。
- 禁止 Gate A、push、promotion、restaging、activation、canary、lane、Publisher、tag、publish。
- 禁止使用 system Python 執行 repo Python module；禁止改寫 current manifest 迎合 target venv。
- 禁止把 Cycle 16 bounded exercise 與 formal runtime identity preflight 混稱同一 gate。
- 禁止第二次 public preflight；首次非 PASS 即停，不換入口。

## 執行契約

1. CodeGraph-first，確認 `validate_runtime_tick`、capacity installer `--preflight`、promotion plan/apply 的 public seam 與測試。
2. 驗證 RED evidence hashes、current manifest digest/head/python、target venv 3.12.12。
3. 列出兩個可證偽假說：
   - H1：current formal preflight 必須用 current manifest-bound interpreter，與 target tooling venv 是不同 authority。
   - H2：Cycle 16 已完成 pre-promotion capacity gate；formal identity preflight 應在 candidate manifest/plan 形成後執行，原卡順序造成循環依賴。
4. 只依 source/tests/observable CLI 證據判定；不得憑命名猜。
5. 若找到合法 canonical public command，僅執行一次 `install_pantheon_content_capacity_guard_launchd.sh --preflight`，必須直接要求宿主 escalation；證明無 persistent target/control-plane mutation。
6. 更新 Cycle 17 卡：寫入 exact argv/env、gate 順序、interpreter authority、單次限制與 fail-closed 條件。
7. 若 H1/H2 無法安全收斂，Cycle 17 卡不改；交付 `BLOCKED / AUTHORITY CONFLICT`。

## 驗收

- `CONTRACT READY / NO PRODUCTION MUTATION` 或 `BLOCKED / AUTHORITY CONFLICT`。
- direct-module invocation count=0；capacity exercise=0；public preflight ≤1；production mutation=0。
- Cycle 17 卡不再允許模糊的 `current capacity preflight`。
- 有 exact argv/env 或明確不可成立證據。
- `git diff --check`；只含允許檔案。

## 交付

- candidate commit、diff、hypothesis verdict、preflight count/status、evidence manifest SHA256。
- 主線驗收後，回原 Cycle 17 thread；不得建立 Cycle 18 production retry。
