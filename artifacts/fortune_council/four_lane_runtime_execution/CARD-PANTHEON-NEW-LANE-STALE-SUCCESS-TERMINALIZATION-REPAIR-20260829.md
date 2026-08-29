# Pantheon New Lane Stale Success Terminalization Repair

## 任務目的

以單一、hash-bound、receipt-first 的 terminalization seam，合法終結 RCA 指定的 `new` lane `succeeded-but-unconsumed` active run，並只釋放 scheduler frontier；保留 inbox/archive 原始 audit bytes。

## 根問題

當唯一 active `new` run 已有成功 result，但尚未被既有 lifecycle 消費時，operator 缺少可驗證且 fail-closed 的終結入口，scheduler 因而不能建立 fresh `new` run。

## 可改範圍

- 與 `new` lane active-run terminalization 直接相關的既有 coordinator/lifecycle source。
- 對應 unit/integration regression tests 與 exact RCA fixture。
- 本卡及本 Repair 的 RESULT、allowlist、immutability receipts。

## 禁止範圍

- 不做 production mutation、plist install/activation、provider、reviewer、publisher。
- 不 commit、push、tag、promotion。
- 不修改其他 lanes、registry FSM 或 database。
- 不刪除或覆寫 inbox/archive bytes。
- 不猜 job、不掃多 job、不提供 generic reset。
- 不跨越 candidate、reviewer、publish boundary。

## 行為契約

1. operator 必須提供 exact lane/run/job/request/prompt/schema/result hashes。
2. 只接受唯一 regular-file、非 symlink、完整 archive/inbox evidence 的 `new` run。
3. hash drift、ambiguity、第二 job、existing candidate/review、wrong lane、missing archive/inbox 一律 fail closed，且零 mutation。
4. 成功路徑先落 durable terminal receipt，再做 allowlisted queue/state transition；流程須 crash-safe、可重跑。
5. 第二次執行不得重複 receipt，亦不得造成 state drift。
6. 成功後 scheduler dry-run frontier 可建立 fresh `new` run，但不得實際呼叫 provider。

## TDD 驗收

- 先用 RCA exact fixture 建立單一 RED-capable test，證明目前入口拒絕或缺失。
- GREEN 證明 provider/reviewer/publisher 呼叫數均為 0。
- protected inbox/archive bytes before/after 完全一致。
- queue/state 只出現 allowlisted terminal receipt/status transition。
- 第二次執行無 duplicate receipt、無 state drift。
- scheduler dry-run frontier 可 create fresh `new` run，且 provider=0。
- 負向覆蓋：hash drift、second job、existing candidate/review、wrong lane、missing archive/inbox、symlink/regular-file boundary。
- 執行 affected coordinator/new lifecycle suites、`py_compile`、`git diff --check`、source budget。

## 交付

- 狀態固定為 `RE_REVIEW_REQUESTED`，不得自行宣告 production ready。
- 交付 RESULT、allowlist receipt、immutability receipt，列明 RED/GREEN 指令與結果、變更檔案、剩餘風險。

## 回退

移除本次 bounded operator seam 與對應測試／receipts；不需回復任何 protected inbox/archive bytes，因本修復不得修改它們。

## Task history

- 假說 H1：既有正式 CLI 沒有 succeeded-but-unconsumed 專用入口；若新增單一 exact-hash seam，RCA fixture 的 plan-only command 會由 argparse 拒絕轉為 `READY_TO_EXECUTE`。
- 假說 H2：可延伸 `terminalize-pending`；RCA 與 source 已證偽，該 seam 明確拒絕 inbox 與 production-attempt evidence，且它會搬移 request，違反本卡 protected archive/inbox immutable 契約。
- RED：`.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_stale_success_rca_exact_fixture_has_plan_only_operator_seam -q` 已執行，因正式 CLI 尚無 `terminalize-stale-succeeded-writer` 而失敗（pytest exit 1；CLI exit 2）。
