# Pantheon Publisher Resident Continuation Repair

## 目的

讓常駐 publisher 在自己成功推送 content-only release 後，下一個 60 秒週期仍可從最新 `origin/main` 繼續發布。

## 根因

- LaunchAgent 將 actor 固定在已驗證的 runtime SHA，這是正確的程式碼部署邊界。
- 每輪隔離 transaction 從最新 `origin/main` 發布，成功後 remote main 會前進，但 actor HEAD 保持固定。
- `deployment_preflight` 目前要求 actor HEAD 必須等於 `origin/main`，所以第一輪成功後第二輪必然被擋。
- 實際證據：第一輪自動發布 `v0.3.82` 成功後，唯讀 preflight 回報 `32411edd4267 != 172de9eede1a`。

## 安全契約

- actor HEAD 仍必須等於安裝時核准的 runtime SHA。
- `origin/main` 必須是 actor runtime SHA 的後代，禁止分歧或 force-push 歷史。
- actor 與最新 `origin/main` 之間不得變更 publisher runtime 路徑。
- 只有 content-only commit 前進時，resident preflight 才可繼續。

## 可修改範圍

- `scripts/agy_content_publisher.py`
- `tests/test_agy_content_publisher.py`
- 本卡與同任務驗證證據

## 禁止範圍

- 不讓 actor 自動執行未部署的新 publisher runtime。
- 不繞過完整 release gate、pre-push hook 或 atomic push。
- 不修改文章候選、review、queue、ledger、retry 與品質政策。

## 驗收

1. content-only descendant origin advance 可通過 deployment preflight。
2. 分歧歷史或 runtime path drift 仍 fail-closed。
3. publisher 完整單元測試與受影響 release suite 通過。
4. `git diff --check` 通過。
5. 部署後至少觀察兩個相鄰 LaunchAgent 週期；第二輪不得因 actor/main SHA 差異失敗。

## 回退

- 修復分支：`codex/publisher-resident-continuation-repair-20260729`
- 若驗收失敗，不合併；若上線後異常，以修復 commit 的 revert 回退並停用 LaunchAgent。
