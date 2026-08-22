---
id: REVIEW-PANTHEON-G8-ACTIVATION-ONLY-EXIT-78-CONTRACT-CLARIFICATION-20260822-RESULT
card_id: REVIEW-PANTHEON-G8-ACTIVATION-ONLY-EXIT-78-CONTRACT-CLARIFICATION-20260822
status: review_no_go
date: 2026-08-22
reviewed_base_sha: a8878602c0fcf658622e6ec365821f00a73c06c9
reviewed_candidate_sha: 39f2b29cfa4e71ea9133e42754b9b59de09ca074
---

# G8 Activation-Only Exit 78 Contract Independent Review Result

## Verdict

`REVIEW_NO_GO G8-EXIT78-P1-001`

## Findings

- `[P1] G8-EXIT78-P1-001`：normative `78` 邊界未由 production validator 執行。
  - State Contract 在 `PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821.md:236` 將 `78` 限定於 `TE-TARGET-STAGED-TO-QUIESCED`、target generation 明確 newer than live，並在 `:237` 要求 current `RR-PUBLISHER-RESET`／`RR-LIVE-AO` 與 target-stage receipts。
  - production validator `scripts/pantheon_content_capacity_guard.py:775-852` 會驗 live plist aggregate、launchctl exact path、state、no-PID 與 exit set，但沒有輸入或驗證 formal Publisher reset receipt，也沒有比較 live 與 target generation 以證明 target newer；`:850` 因此可在上述 provenance 未成立時接受 `[78]`。
  - candidate suite 內的 `_capacity_transition_installer_env` 在 `tests/test_pantheon_content_capacity_guard.py:804-833` 使用同一 manifest／generation 建立 live 與 target stage，fake launchctl 預設回 `78`；`test_capacity_installer_stages_during_manifest_bound_preactivation_transition` 在 `:1227-1252` 仍要求 installer 成功。此 positive case 直接證明 same-generation、無 formal reset receipt 的 `78` 可通過 executable contract。
  - 影響：未證明經合法 Publisher reset edge 的 activation-only state 可被 Capacity transition 接受並寫入 target Capacity stage，違反本 candidate 宣告的 fail-closed ordering 與 transition authority。修復需讓 validator 消費並驗證 current reset receipt／unchanged-service proof，且明確證明 target generation newer than live；同時把 same-generation 與 receipt 缺失加入 negative regression。

## Axis Result

- Spec：`NO-GO`；State Contract／Edge Map 與 Capacity executable contract 不一致。
- Correctness：absent／`0`／`78`、其他 nonzero、PID、path drift assertions 確實命中 production validator，但 `78` 的 generation／receipt provenance 未被命中。
- Boundary：`child_policy=forbidden` 的 production workload child 語意清楚；本 finding 不涉及放寬 normal mode或其他 nonzero。
- Regression：既有 same-generation positive fixture 抵銷 candidate 宣告的 target-newer negative boundary。
- Scope：candidate 僅四個允許檔案；未發現 runtime、installer 或 production mutation diff。

## Verification

- `.venv/bin/python -m pytest tests/test_pantheon_content_capacity_guard.py -q`：`52 passed in 18.39s`。
- `.venv/bin/python -m pytest tests/test_pantheon_g8_production_preactivation.py -q`：`41 passed in 9.93s`。
- `.venv/bin/python -m pytest tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_stages_during_manifest_bound_preactivation_transition -q`：`1 passed in 1.14s`。
- `git diff --check a8878602c0fcf658622e6ec365821f00a73c06c9..39f2b29cfa4e71ea9133e42754b9b59de09ca074`：PASS。
- CodeGraph：已先查詢；此 worktree 未初始化 index，依卡片改採固定 range 與直接關聯 validator／tests 的限域讀取。

## Residual Risk

- 未建立 Cycle 35／36 symptom card；本 finding 保持在同一 transition edge repair unit。
- 未修改 candidate、未做 Repair、merge、push 或 production 動作。
