# Pantheon Acceptance B：Release Tag Namespace RCA

## 工作名稱

Gen06 正式發佈重試的 release tag namespace 根因分析。

## 事故邊界

- run：`auto-i18n-ja-1414b75a404721e95e74`
- publisher base：`1e46c46426cf1662c1089cbf33dcf2ee54d437c4`
- 暫時 release commit：`042e2e52db6aa08170f075c2c38858ea18c721f2`
- 碰撞 tag：`v0.3.373`
- 本卡只分析 release version、tag namespace、preflight／transaction boundary 與 retry idempotency。

## 必答問題

1. 最後能成功 release／tag 的版本與行為。
2. 哪個 commit／機制先占用 `v0.3.373` 卻未同步 `package.json`／`pyproject.toml`，以及本次 publisher 為何仍選到相同版本。
3. durable invariant：release version authority、tag uniqueness、preflight／transaction boundary、retry idempotency。
4. 一條 exact RED-capable test／harness：必須在內容生成、大規模 prerender、commit 前抓到碰撞，並證明 provider、production／public、queue、ledger、candidate bytes 不變，tag／push 為零。

## 允許修改

- 本任務卡。
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_release_tag_namespace_rca_20260829/` 下的 RCA evidence 與 `RESULT.md`。

## 禁止範圍

- 不改 source、tests、runtime production。
- 不 commit、push、tag、publish。
- 不再執行 publisher。
- 不以單純改成 `v0.3.374` 代替根因分析。

## 驗收

- 沿 source／history／既有 evidence 還原 formation chain。
- 鎖定一個主裁決，區分 root cause 與 secondary factor。
- 提出 minimum bounded Repair frontier，列明 `why_not_less`、`why_not_more`、`do_not_absorb`。
- 交付精簡、可重現的機器證據與繁中 `RESULT.md`。
