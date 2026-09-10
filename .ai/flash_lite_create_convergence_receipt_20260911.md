# Flash Lite create convergence receipt（2026-09-11）

## 目的

在不更換 `gemini-3.5-flash-lite`、不放寬 canonical quality gate、也不放寬 provider structural validation 的前提下，讓 create Writer 的機械長度問題能穩定進入 deterministic local repair，並確認 Reviewer 不會以錯誤字數估算覆蓋本機 authoritative measurement。

## 修復邊界

- Branch：`codex/web-schema-boundary-repair-20260911`
- 前置 architecture repair：`919dcd2f6808`
- 前置 runtime smoke receipt：`dfd3d54184`
- Writer：`gemini-3.5-flash-lite`
- Reviewer：`gemini-3.1-flash-lite`
- 僅修改：`scripts/agy_seo_copy_pipeline.py`、`tests/test_agy_seo_copy_pipeline.py`
- 未執行：publish、apply、approval、production mutation、queue mutation、服務啟停、route/config 變更

## 實作結果

1. description bounded repair 改用四個 provider semantic parts：`readerProblem`、`concreteSituation`、`observableAction`、`nextStep`；本機依固定順序 hydration 成 canonical string，並附上 canonical-safe boundary sentence。
2. provider 回傳過長時，本機只裁切 provider parts，保留四個 semantic part 與固定 boundary；過短時不補造內容，仍交 canonical `quality_findings()` fail-closed。
3. body repair 重用原有 paragraph reflow 演算法；只有 `bodySections` 已被 repair contract 授權時才執行，且每節 concatenated text 必須 byte-for-byte 保留。文字不足時不補造內容，canonical gate 仍拒絕。
4. create repair prompt 加入 trusted local measurements 與 bounded target，避免要求 Flash Lite 自行精準計數。
5. Reviewer reconciliation 僅加入已實際觀察到的 machine-owned aliases：`description_length_violation`、`paragraph_length_insufficient`。未採 prefix/family 泛化；semantic finding 仍保留並可阻塞核准。

## 自動化驗證

- 核心受影響 regression：`20 passed`。
- multilingual fixed-coverage：`25 passed, 405 deselected`。
- SEO pipeline 全檔：`222 passed / 24 failed`。24 個 failure 數量與本輪修改前既有 baseline 相同；分類為：
  - 舊 route expectation 仍期待 `gemini-3.5-flash`，目前正式 route 已是 `gemini-3.5-flash-lite`。
  - sparse worktree 未帶入既有大型 content matrix / rewrite evidence artifacts，相關 fixture 讀檔失敗。
- `git diff --check`：PASS。
- `py_compile`：PASS。
- 測試環境註記：此 sandbox 的 `uv` 先因共用 cache 權限失敗，改用可寫 cache 後又觸發 macOS SystemConfiguration panic；因此 pytest 使用同一套既有 Pantheon `.venv` Python 直接執行。

## 真實 Flash Lite final-code smoke

共同條件：同一合成 create brief `SMOKE-SCHEMA-BOUNDARY-20260911`、`max_repairs=2`、輸出只在 `/private/tmp`。

### Final smoke 1

Run dir：`/private/tmp/pantheon-flash-lite-final-1-20260911.nnAdIP`

- attempts：3
- content repairs：2
- schema repairs：0
- validator：PASS
- failure codes：`[]`
- description：90 字
- answer：43 字
- paragraph range：80–148 字
- Reviewer：APPROVE，findings `[]`
- `approval_created=false`
- `apply_executed=false`

### Final smoke 2

Run dir：`/private/tmp/pantheon-flash-lite-final-2-20260911.FyPWDj`

- attempts：3
- content repairs：2
- schema repairs：0
- validator：PASS
- failure codes：`[]`
- description：83 字
- answer：24 字
- paragraph range：109–124 字
- Reviewer：APPROVE，findings `[]`
- 未建立 approval，未執行 apply / publish / production mutation。

## 第三個真實 payload reconciliation replay

來源：`/private/tmp/pantheon-flash-lite-ready-3-20260911.Tln4iN/attempts/03/external-review.json`

- 真實 candidate deterministic findings：`[]`
- description 本機實測：90 字
- paragraph range：131–145 字
- 原 Reviewer：REJECT，錯誤回報 `paragraph_length_violation` 與 `description_length_violation`
- 目前 reconciliation：APPROVE，findings `[]`

這個 replay 證明新增 alias 只處理本機已 authoritative 驗證的 machine-owned measurement；semantic finding preservation regression 另有測試保護。

## 未重跑項目

原計畫第三次 final-code live smoke 的額外外網呼叫被自動 approval review 擋下，因此沒有重送 provider。這不改變前兩次 final-code live smoke 與第三個既有真實 payload replay 的結果，也沒有造成 provider quota 消耗。

## 判定

本輪 create convergence repair 可進下一階段 release / production readiness review：provider schema boundary、deterministic quality gate、bounded repair、Reviewer authority 已形成可重現閉環。

此 receipt 不宣稱已部署。正式 production canary / deploy 仍需依 repository 的 storage-capacity 與 production-canary readiness gate 執行。
