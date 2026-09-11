# Pantheon 四線恢復：Web 初修派工卡

## Root question

如何一次修正 provider schema 與本地品質 gate 的責任邊界，使中文新文、中文重寫、多語新文、多語重寫都能進入本地 repair／Reviewer，而不再逐一追著 `minLength`／`maxLength` 錯誤修補？

## Current state

- 候選 HEAD：`9730db3130d910af72f536266f552d61b8122c2d`；parent：`ebfa35a351efef503afed41f01d561011757c188`。
- `ebfa35a` 已將多語 41 個 opaque fact ID coverage 改為程式 deterministic 建立；模型只做語意規劃。EN／JA／KO provider 測試各一次通過 41 facts。
- `9730db3` 已讓 create 初始回應的 description 長度限制延後至本地 gate，並修正 Gemini request 仍從 canonical schema 讀取 70–95 提示。
- 正式 runtime actor 目前也是 `9730db3`，但六個內容服務已主動停止；capacity guard 保持載入。不得宣稱四線正在產文或已驗收。
- 新 run `auto-new-v1-20260910-092-01` 證明 create 初始 provider schema 可通過；後續 repair 仍因 body paragraph `maxLength` 在 provider transport 被擋。
- 根因已定位為 schema 規則在多個入口重複：`external_create_repair_schema()` 直接複製 `_article_json_schema()` 的字串長度限制；initial／repair／create／rewrite／i18n 各有不同 provider schema 路徑。
- `tests/test_agy_seo_copy_pipeline.py` 目前 targeted 4 tests PASS；全檔 211 PASS／26 FAIL，失敗主要是既有 sparse fixtures／config route mismatch，不能宣稱全綠。

## Durable invariant

Provider-bound schema 只負責 JSON 結構、欄位、型別與必要陣列結構。內容長度、語言、fact identity、coverage、SEO 品質由 deterministic hydration 與本地 validator／repair／Reviewer 負責。Opaque canonical IDs 由程式建立或還原，不要求小模型精準抄寫。

## Scope

先唯讀盤點所有 provider-bound schema producer／consumer，再做一個 bounded repair：

1. `scripts/agy_seo_copy_pipeline.py`：create／rewrite 的 initial 與 repair schema、`GeminiClient.generate_json`、本地 hydration／quality gate。
2. `scripts/agy_multilingual_pipeline.py`：planning、candidate、continuation／repair、Reviewer schema 與 hydration。
3. `scripts/agy_gemini_runner.py`：`_response_schema_for_model`、結果 normalization 與 broker validation。
4. 新增離線 fake-transport regression：遍歷所有 provider-bound initial／repair 路徑，讓 structurally valid 但長度不足／超長的 payload 通過 transport，並證明本地 gate 能抓到且進入 repair／Reviewer；另驗證 canonical IDs deterministic 還原。

## Constraints

- 不呼叫任何 provider，不啟動排程，不修改 production/runtime，不發布文章，不放寬本地品質 gate。
- 不新增第二套 workflow、ledger、registry、FSM 或 runner。
- 不逐一 patch 下一個錯誤訊息；先完成 schema matrix、失敗機制與 RED-capable test，再做一次 bounded repair。
- 保留現有兩個 commits；不要 reset、squash 或重寫歷史。
- 文件與註解使用繁中；Python 使用既有 `.venv`／uv。

## Deliverables and acceptance

- 一份精簡 schema matrix，列出每個 provider-bound schema 的 producer、consumer、目前承載的品質規則及修正方式。
- 一個可 review 的 commit，修改範圍限於必要 pipeline 與 regression tests。
- targeted tests、受影響測試與 `git diff --check` 結果；明確列出仍存在的既有失敗。
- 不做 deploy／push；交回主線 review。最終四線完成仍須 Writer → Reviewer → publish → 公開網址 HTTP 200 且正文可見。

## Evidence references

- `.ai/locale_planner_contract_receipt_20260910.md`
- `.ai/locale_planner_activation_receipt_20260910.md`
- `.ai/create_description_repair_activation_scope_20260910.md`
- `.ai/create_description_repair_activation_receipt_20260910.md`
- `handoff_20260910_g105_quota_constrained_next.md`
