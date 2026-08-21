---
id: CARD-PANTHEON-G8-PUBLISHER-CANARY-FINAL-SHIP-20260821-RESULT
card_id: CARD-PANTHEON-G8-PUBLISHER-CANARY-FINAL-SHIP-20260821
status: blocked
terminal_state: BLOCKED / NO RETRY
candidate_thread: 01a01dc1-0e97-75d2-9baa-4b7f261f9c40
---

# G8 Publisher 單筆正式開通完整收尾 RESULT

## 終局判定

`BLOCKED / NO RETRY`

正式 promotion、finalize 與 ordinary fast-forward push 已完成，runtime actor 與 origin/main 均收斂到 `a07647309b9df89ed55cc000b65f151f9622b76b`。G32 coordinator、四 lanes 與 Publisher exact-run private stage 亦已建立。

停止點在 Publisher terminal reset 前的 pre-mutation contract：live Publisher plist 仍有 `StartInterval=60`。source authority `a076...` 的 `--reset-publisher-activation-only` handler 明文要求 terminal one-shot live Publisher 必須 `RunAtLoad=true` 且沒有 `StartInterval`／`KeepAlive`；focused success test 也先移除這兩個 schedule key 才呼叫 reset。依本次明示分支，正式契約不允許目前 legacy scheduled live Publisher 作為 reset input，因此未呼叫 reset、未執行 Capacity/readiness/activation，亦未產生 Publisher child。

## Bootstrap 與 authority

- 工作 worktree：clean detached `aa4fa7403848b8e9054fe07e0806e21f76efe617`。
- Source authority：共享 main `a07647309b9df89ed55cc000b65f151f9622b76b`；使用 clean detached temp clone，origin URL 精確相符。
- Card 與既有 RESULT blob：source commit 內可讀。
- CodeGraph：目前 session 無可用 CodeGraph tool，依授權退化為限域查詢；未掃全 repo、未跑 release suite。
- exact run：`auto-i18n-en-614aa4dc3542ab2c5637`，target `ASTRO-BASE-01:en`；promotion request 證明 preserved run count `140` 且授權 run 存在。

## Promotion

- Host capacity PASS receipt：重用既有正式 receipt，sha256 `3172bbaf48cb5c2dc34af6d4dedb9310324c18ad68a8c67fd7e627c00da0fe95`；兩個 cycle 均 `rss_available=true`、`swap_available=true`，reclamation PASS，stop-loss `STOPPED`。
- Promotion plan：`READY_TO_APPLY`，plan digest `e9a30408c098585aadb3979a3522e617b87945eb00ce9f43a88f0470e88efe1e`。
- Apply/postcheck/finalize：`POSTCHECK_PASSED / COMMITTED`。
- Target manifest digest：`170621da19d8ce1c6b29218d1a8ef56b7aa992668db1e19ec1b82b54b2b35509`。
- Target runtime identity digest：`a3100865affb23095e5681704882109fb44ddbd19dda1b38ce90b3d3a869bfea`。
- Target generation：`g32-a0764730-20260821T190500Z`。
- Queue snapshot digest 在 plan 與終態均為 `e4e2b5e42570953ce1b29117243f972bc170ef7b68ddc2353512533fa378aca2`。
- Ordinary fast-forward push：唯一一次成功，remote main `4c16a2f4... -> a0764730...`；終態 ls-remote 精確為 `a07647309b9df89ed55cc000b65f151f9622b76b`。

## Stage 與 reset 契約

- coordinator＋四 lanes private-stage install：`1`，PASS。
- Publisher exact-run private-stage install：`1`，PASS；`max-runs=1`、exact run 與 manifest/generation receipt 精確相符。
- Capacity staged plist：未安裝。
- 新 private stage 有六份 service plist，manifest digest 與 generation 為 G32。
- live Publisher plist sha256：`76b67acb55c5b980ecc8376f8f882ac0c620acc56818254ef85eabfa830b9bc5`。
- live Publisher mode：normal、`RunAtLoad=true`、`StartInterval=60`、無 `--activation-only`；launchctl service absent。
- Handler 證據：`scripts/install_agy_gemini_coordinator_launchd.sh` 在任何 live replacement/bootstrap 前，若 `StartInterval` 或 `KeepAlive` 存在即回報 `requires a terminal one-shot Publisher plist` 並 fail-closed。
- Focused test 證據：`tests/test_agy_gemini_coordinator.py::_write_publisher_terminal_live` 明確 `pop("StartInterval")` 與 `pop("KeepAlive")`；成功 reset test 只使用此 one-shot fixture。
- 因契約明文拒絕目前輸入，reset invocation count 保持 `0`，未以實際 invocation 製造 failure receipt。

## 七服務終態

- Publisher：service absent、PID `0`、child `0`、transaction/tag/push `0/0/0`。
- Coordinator、new、rewrite、i18n-new、i18n-rewrite、Capacity：均 loaded、`state=not running`、無 PID。
- 其他六服務 live plist sha256 與 bootstrap 前快照完全相同。
- 其他六服務 business child I/O：`0`；queue snapshot digest 與 run count `140` 均不變。
- Publisher scheduled plist 未載入；因此未執行額外 bootout，也未 bootstrap Publisher。
- Actor 終態：clean detached `a07647309b9df89ed55cc000b65f151f9622b76b`。

## Mutation accounting

- promotion plan/apply/finalize：`1 / 1 / 1`。
- ordinary fast-forward push：`1`。
- coordinator＋four lanes stage install：`1`。
- Publisher exact-run stage install：`1`。
- Publisher activation-only reset：`0`。
- no-PID 三連續取樣：`0`。
- Capacity public preflight/install：`0 / 0`。
- Rule25 readiness official gate/fail-closed fixture：`0 / 0`。
- Publisher-only activation entrypoint：`0`。
- Publisher child：`0`。
- exact-run transaction/release commit/annotated tag/push：`0 / 0 / 0 / 0`。
- 其他六服務 business child I/O：`0`。
- retry 或替代入口：`0`。

## Evidence

- `<repo-root>/.work/CARD-PANTHEON-G8-PUBLISHER-CANARY-FINAL-SHIP-20260821/capacity-receipt.json`
- `<repo-root>/.work/CARD-PANTHEON-G8-PUBLISHER-CANARY-FINAL-SHIP-20260821/promotion-request.json`
- `<repo-root>/.work/CARD-PANTHEON-G8-PUBLISHER-CANARY-FINAL-SHIP-20260821/promotion-plan-result.json`
- `<repo-root>/.work/CARD-PANTHEON-G8-PUBLISHER-CANARY-FINAL-SHIP-20260821/promotion-apply-result.json`
- `<repo-root>/.work/CARD-PANTHEON-G8-PUBLISHER-CANARY-FINAL-SHIP-20260821/promotion-finalize-result.json`
- `<runtime-root>/transactions/g8-publisher-canary-final-ship-20260821-a076/promotion-receipt.json`

## 未做

- 未呼叫 `--reset-publisher-activation-only`，因 focused contract 明文拒絕目前 legacy scheduled live Publisher。
- 未安裝 Capacity private-stage plist。
- 未執行七服務連續三次 loaded/no-PID 取樣。
- 未執行 Capacity `--preflight` 或 `--install`。
- 未執行 Rule25 readiness。
- 未執行 `--activate-publisher-only`。
- 未執行 exact-run transaction、release commit、annotated tag 或 canary push。

## 未驗

- 未驗 reset 成功後七服務 coherent activation-only 終態。
- 未驗 Capacity preactivation transition。
- 未驗 current capability `READY` 與 fail-closed fixture `BLOCKED`。
- 未驗 Publisher activation 成功路徑、child 上限、transaction/tag/push 對帳。
- 未驗 post-canary actor/origin clean coherent，因 canary 未開始。

## 殘餘風險

- live Publisher plist 仍有 `StartInterval=60`，雖 service 現為 absent，但若由其他入口載入會恢復週期排程風險。
- G32 private stage 尚缺 Capacity；不得以此 partial stage 執行替代 activation。
- origin/main 與 runtime actor 已正式 promotion 到 `a076...`，但 exact run 尚未發布。
- 本卡已命中 stop-loss；不得在此 thread retry reset、Capacity 或 activation，也不得開 replacement/cycle/Repair/Reviewer。
