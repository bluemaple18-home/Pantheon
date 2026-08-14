# APF-004-GATE2-LAUNCHCTL-PATH-INDENT-REPAIR-001

## 正式狀態

- 工作名稱：修復 Gate 2 launchctl path 縮排 authority
- 現在狀態：REPAIR_READY / production 停線 / 零 production mutation
- chain_id：pantheon-writer-vnext-apf004-gate2-production-realignment
- card_id：APF-004-GATE2-LAUNCHCTL-PATH-INDENT-REPAIR-001
- base：2a073ad57e6799383236d743bcc0567f0a2d3d72
- finding：APF004-G2-P1-LAUNCHCTL-PATH-INDENT
- mutation_executed：false

## 契約邊界

- 沿用既有 Repair formal task/thread，不建立新 Repair task。
- 修復 macOS `launchctl print` 正常縮排的 `path =` 欄位被誤拒。
- 只允許 key 前 indentation。
- key / equals / value strict spacing 不放寬。
- value 仍必須是單一 absolute non-whitespace path。
- raw / canonical / target exact equality 不變。
- 不改 parser/policy/rollback/manifest/runtime/publisher/capacity budget。
- 不放寬 extra-whitespace、duplicate、prefix/suffix、relative、noncanonical、symlink、owner、mode、running negatives。
- 零 production install / activate / launchctl mutation。
- 不 merge、不 push、不發文。

## Source decision

- `origin/main` / `FETCH_HEAD` 已唯讀 fetch 並確認 exact `2a073ad57e6799383236d743bcc0567f0a2d3d72`。
- CodeGraph 查詢此 worktree 未初始化 `.codegraph`，依規則 fallback 限域讀：
  - `scripts/install_agy_gemini_coordinator_launchd.sh`
  - `tests/test_agy_gemini_coordinator.py`

## RED

先只改 positive fixture，讓 fake `launchctl print` 輸出真實縮排：

```text
    path = <absolute-capacity-target>
```

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_only_adopts_exact_legacy_capacity_guard
```

Observed before fix:

- result：FAILED
- stderr：`legacy prior-loaded service 缺少 valid activation barrier，拒絕 activation。`
- phase：`previous_barrier_validation`
- fake mutation path 未被觸發。

## 修復摘要

- 只改 `scripts/install_agy_gemini_coordinator_launchd.sh`：
  - `STRICT_PATH_FIELD_COUNT` 允許 key 前 indentation。
  - `LOADED_PATH` extractor 允許 key 前 indentation。
  - strict spacing 仍要求 `path = /...`。
  - value 仍為單一 absolute non-whitespace path。
  - raw/canonical/target equality 保持不變。

## GREEN / 驗證

- exact positive：PASS
- 13 zero-mutation negatives：PASS
- rollback success/failure + normal authority isolation：PASS
- targeted regression：PASS
- runtime manifest suite：PASS
- affected coordinator suite：PASS
- final gates：見 `.ai/evidence/apf_004_gate2_launchctl_path_indent_repair_001.md`

## 風險

- 此修復只接受 macOS `launchctl print` 常見 key 前縮排；沒有放寬 key/value spacing 或 path equality。
- 未宣稱 integration 或 production ready。
