# Pantheon Acceptance B：Release Tag Namespace Bounded Repair

## 任務目的

修復 `RELEASE_VERSION_AUTHORITY_SPLIT`：正式 publisher 必須在 ready selection 後、任何 mutation 前，以對齊的 `package.json`／`pyproject.toml` 與 fresh local／remote SemVer tag namespace 形成單一 frozen release plan；promotion 不得再占用 `vX.Y.Z` release namespace。

## 根因與 RED 契約

- RCA：`pantheon_acceptance_b_release_tag_namespace_rca_20260829/RESULT.md`
- formation evidence：`formation-chain.json`
- exact RED：`exact-red-harness-contract.json`
- fixture：版本檔皆為 `0.3.372`，local／remote 已有 `v0.3.373`，必須選 `0.3.374`。
- boundary：ready selection 後、`MutationJournal.begin()`／內容套用／prerender／commit 前。

## 可改範圍

- `scripts/agy_content_publisher.py`
- promotion/helper 中實際建立或規劃 control tag 的最小既有 seam
- `tests/test_agy_content_publisher.py`
- 對應 promotion tests
- 本卡與專屬 RESULT／machine receipts

## 禁止範圍

- 不改 JA candidate、queue/state、provider、Reviewer。
- 不新增 registry、FSM、database、version service 或第二套 ledger。
- 不改 deploy config。
- 不執行 production publisher、promotion、commit、push、tag。
- 不移動、刪除或覆寫既有 `v0.3.373`。

## Strict fact gate

- 受影響 public seam：publisher create／rewrite／translation ready selection、版本 bump、commit/tag/push transaction；promotion control-tag helper。
- authoritative inputs：`package.json.version`、`pyproject.toml project.version`、local `refs/tags/vX.Y.Z`、remote `refs/tags/vX.Y.Z`。
- frozen output：selected version/tag、基準版本、occupied namespace 與可重驗 identity；同一 transaction 後續版本檔、CHANGELOG、commit message、annotated tag、atomic push共用。
- rollback：捨棄本卡未提交 diff 即可；本卡不得觸及 production 或 Git refs。

## 驗收

1. exact RED 先實跑，失敗必須命中缺少 early frozen namespace plan 的目標症狀。
2. planner 對齊兩份版本檔，讀 local + remote SemVer tags，first-free 選 `0.3.374`；輸出 immutable plan。
3. publisher 在 `journal.begin` 前完成 plan；commit 前重驗 drift；已知 collision 不產生 provider/coordinator、內容、prerender、commit、tag、push 或 retry mutation。
4. promotion/helper 拒絕 `vX.Y.Z`，只允許既有非 SemVer control namespace或不建 tag。
5. exact test、affected publisher/promotion suite、`py_compile`、`git diff --check` 全綠。
6. RESULT 記錄 candidate diff、allowlist、測試、production immutability、`why_not_less`／`why_not_more`／`do_not_absorb`，交獨立 Reviewer。

## 狀態

`RE_REVIEW_REQUESTED`
