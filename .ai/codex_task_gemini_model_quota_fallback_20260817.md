# Gemini Writer／Reviewer 配額感知降級

## 目標

讓正式內容流程先輪換可用 project；只有確認某模型的所有 project 都是每日配額耗盡或零配額時，才切換模型。RPM 暫時限流與 503 不得觸發模型降級。

## 固定路由

- 正常：Writer `gemini-3.5-flash`；Reviewer `gemini-3.1-flash-lite`。
- Writer 降級：Writer `gemini-3.5-flash-lite`；Reviewer維持 `gemini-3.1-flash-lite`。
- Reviewer 降級：Writer維持 `gemini-3.5-flash`；Reviewer `gemini-3.5-flash-lite`。
- Writer 與 Reviewer 不得使用同一模型。
- 找不到有效的不同模型配對時，停止領取新工作並保留 queue，不得假裝成功。

## 需求與驗收

- `FR-GMF-001`：把暫時限流／服務不可用與每日配額耗盡／零配額分類成封閉錯誤碼；不得保存原始 provider body、API key 或敏感 project 資訊。
- `FR-GMF-002`：同一模型必須先輪完所有可用 project，只有全數被配額阻擋才可降級。
- `FR-GMF-003`：Writer／Reviewer 路由始終維持不同模型。
- `FR-GMF-004`：使用上列固定路由；無合法配對時 fail closed 並保留 queue。
- `FR-GMF-005`：receipt 只保存角色、舊／新模型、封閉原因碼與安全 slot identity。
- `SC-GMF-001`：測試證明 RPM 429 與 503 不降模型；quota-exhausted／0-quota 在所有 project 不可用後才降級。
- `SC-GMF-002`：測試證明 Writer／Reviewer 不同模型，且無合法配對時不做工作 mutation。
- `SC-GMF-003`：installer／plist 精確寫入正常路由與降級路由契約。
- `SC-GMF-004`：受影響測試、shell syntax 與 `git diff --check` 全通過。

## 工作切片

1. `SL-GMF-CLASSIFY`：新增封閉 provider 錯誤分類與單元測試。
2. `SL-GMF-ROUTE`：新增 per-model／per-slot 配額阻擋與角色配對路由；依賴 1。
3. `SL-GMF-INSTALL`：把路由契約納入正式 installer／plist；依賴 2。
4. `SL-GMF-VERIFY`：跑受影響測試、review、diff check；依賴 1～3。

## 邊界

- 本卡允許修改內容 pipeline、Gemini runner／allocator、installer 與對應測試。
- 不改文章內容、SEO schema、發布 transaction 或既有文章。
- 本卡不單獨授權 production launchd 重裝、canary、發文或任何 production mutation；完成程式與驗證後另走正式啟用閘門。
