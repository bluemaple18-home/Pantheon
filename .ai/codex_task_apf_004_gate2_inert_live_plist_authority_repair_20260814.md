# APF-004-GATE2-INERT-LIVE-PLIST-AUTHORITY-REPAIR-001

## 正式狀態

- 工作：修復 Gate 2 inert live plist authority
- 現在狀態：REPAIR_READY / production 停線 / 零 live mutation
- base：d3f621d9849cfef1857b9765914243210ed12e79
- finding：APF004-G2-P1-INERT-LIVE-PLIST-SET
- mutation_executed：false
- production_mutation_executed：false

## 契約邊界

- 沿用既有 Repair formal task；未建立 replacement。
- 不刪除、不搬移 production plist。
- 保留原「只有 capacity plist 存在」authority 與既有 negatives。
- 新增獨立、fail-closed 的 `legacy capacity loaded + complete inert six-plist set` authority。
- 不直接移除 `backup plist must be absent` 判斷；改為分流 `capacity-only` 與 `inert-six`。
- normal `--activate` 不得使用此 authority。
- 禁止 production install / activate / launchctl mutation、merge、push、發文。

## Source decision

- worktree 啟動時 clean。
- `origin/main` / `FETCH_HEAD` 已確認 exact base `d3f621d9849cfef1857b9765914243210ed12e79`。
- CodeGraph 查詢此 worktree 未初始化 `.codegraph`，依契約 fallback 限域讀：
  - `scripts/install_agy_gemini_coordinator_launchd.sh`
  - `tests/test_agy_gemini_coordinator.py`

## RED

建立 exact inert-six fixture：

- previous barrier missing
- 七份 live plist 均存在
- 只有 `com.pantheon.content-capacity-guard` loaded
- capacity `launchctl print` path 有正常縮排
- 六份 inert plist snapshot 時 unloaded

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_only_adopts_legacy_capacity_with_complete_inert_plist_set
```

Observed before fix:

- result：FAILED
- stderr：`legacy prior-loaded service 缺少 valid activation barrier，拒絕 activation。`
- phase：`previous_barrier_validation`
- mutation log 不存在，business child I/O 為 0

## 修復摘要

- `prepare_legacy_capacity_adoption()` 保留原 capacity-only branch。
- 新增 inert-six branch：
  - 六份 inert backup 必須全部存在；partial set 拒絕。
  - 六個 inert labels snapshot 時必須全部 unloaded。
  - 每份 inert target 必須 regular non-symlink、owner=current user、mode 600。
  - 每份 inert target canonical path 必須等於 expected target path。
  - snapshot backup bytes 必須等於 live target bytes。
  - 為每份 inert plist 保存 sha256 snapshot。
- 新增 `verify_legacy_capacity_adoption_pre_replace()`：
  - 只對 inert-six marker 生效。
  - replace 前再次確認六個 inert labels 仍 unloaded。
  - replace 前再次確認 live target 存在、非 symlink、bytes/hash 未 drift。
- marker / evidence 分流：
  - `legacy-capacity-adoption-mode`
  - `legacy-capacity-inert-six-adoption`
  - 原 `legacy-capacity-adoption`
- rollback 保留既有行為：恢復 backups；只重新 bootstrap snapshot 時 loaded 的 capacity。

## 驗證摘要

- exact inert-six positive：PASS
- original capacity-only positive：PASS
- inert-six negatives：PASS
- capacity existing 13 negatives：PASS
- inert-six rollback success/failure receipts：PASS
- capacity rollback success/failure receipts：PASS
- normal activate isolation：PASS
- affected coordinator suite：PASS
- runtime manifest suite：PASS
- final gates：見 `.ai/evidence/apf_004_gate2_inert_live_plist_authority_repair_001.md`

## Remaining risk

- Owner negative 透過 fixture `stat` shim 模擬非 current-user owner；未使用 privileged `chown`。
- 未宣稱 integration 或 production ready。
