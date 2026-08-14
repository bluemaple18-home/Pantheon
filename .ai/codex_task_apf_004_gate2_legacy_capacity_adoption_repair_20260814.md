# APF-004-GATE2-LEGACY-CAPACITY-ADOPTION-REPAIR-001

## 正式狀態

- 工作名稱：APF-004-GATE2-LEGACY-CAPACITY-ADOPTION-REPAIR-001
- 正在做什麼：修復 activation-only 對單一 legacy capacity guard 的可驗證接管與回滾
- 現在狀態：REPAIR_READY / LOCAL ONLY / NO PRODUCTION MUTATION
- Base：e83ca791d0b86287e8e3a33c29f12f9cb2b7c6d0
- branch：codex/apf-004-gate2-legacy-capacity-adoption-repair
- mutation_executed：false

## 契約邊界

- 只在 exact legacy capacity-only state 適用：
  - 恰好 `com.pantheon.content-capacity-guard` loaded。
  - 六個非 capacity labels absent。
  - legacy capacity live plist 存在、不是 symlink、owner 為 current user、mode 0600。
  - snapshot backup bytes 與 live target bytes 一致。
  - loaded identity 可讀，且 `path = <capacity target>` 與 target path 一致。
  - loaded identity 不得是 `state = running`。
- normal `--activate` 不接受 legacy adoption authority，仍必須要求完整 previous manifest/barrier。
- adoption path 只適用 `--activate-only`。
- activation-only 成功後只完成 barrier ack / loaded post-check，不執行 coordinator/lane/publisher/capacity child I/O。
- rollback 無 previous manifest/barrier 時，只可在 repo-owned `legacy-capacity-adoption` marker 存在時恢復 exact legacy capacity guard。

## 禁止範圍

- live install / activate / launchctl
- production runtime / manifest / plist mutation
- push / merge / deploy
- external model
- create / run / select / publish / transaction / tag / schedule
- publisher / business logic、V9、SEO/GEO

## Source decision

- 主線 CodeGraph 已查詢但未命中 shell seam；依契約限域讀：
  - `scripts/install_agy_gemini_coordinator_launchd.sh`
  - `scripts/pantheon_content_runtime_manifest.py`
  - `tests/test_agy_gemini_coordinator.py`
  - `tests/test_pantheon_content_runtime_manifest.py`

## RED

Command:

```bash
<venv-python> -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_only_adopts_exact_legacy_capacity_guard
```

Observed before fix:

- returncode：1
- stderr：legacy prior-loaded service missing valid activation barrier
- phase：`previous_barrier_validation`
- interpretation：exact legacy capacity-only state 可安全採用，但現有程式仍 fail-closed。

## 修復摘要

- 新增 `prepare_legacy_capacity_adoption()`。
- 在 `previous-barrier-missing` 且有 prior-loaded label 時：
  - normal path 永遠拒絕。
  - activation-only path 只在 exact legacy capacity-only snapshot 驗證通過時建立 adoption marker。
- rollback 對沒有 previous barrier 的 prior-loaded state 仍預設 fail；只有 adoption marker 存在時允許 capacity-only rollback authority。
- rollback success/failure 仍使用既有 failure receipt status：`ROLLBACK_COMPLETE` / `ROLLBACK_FAILED`。

## 驗證摘要

- RED→GREEN positive adoption：PASS
- zero-write negative matrix：PASS
- rollback success/failure receipts：PASS
- normal authority isolation：PASS
- existing activation-only / legacy / P1 / normal success+rollback：PASS
- affected coordinator suite：PASS
- runtime manifest suite：PASS
- final gates：見 evidence。

## 後續

本 commit 只提供 repo-owned local repair。後續若要進 production，仍需獨立 review/integration 後，再走正式 live confirmation gates。
