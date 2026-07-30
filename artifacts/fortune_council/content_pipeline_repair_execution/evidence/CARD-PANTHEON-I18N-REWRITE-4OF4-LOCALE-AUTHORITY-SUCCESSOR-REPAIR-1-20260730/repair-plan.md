---
id: CARD-PANTHEON-I18N-REWRITE-4OF4-LOCALE-AUTHORITY-SUCCESSOR-REPAIR-1-20260730-plan
status: complete
type: repair-plan
---

# Repair plan

Root question：以封閉、whole-value ASCII literal grammar 修復兩個 P1，同時維持日韓自然語言、明列 literal 與 en 行為。

1. `LAS-REV-001`
   - 先 fresh 跑 full-consumption Review group，確認 RED。
   - 在 direct test 補 whole-value regression。
   - 將抽取式 tokenization 改為 anchored fullmatch 與明確單一空白 separator。
   - 重跑 Review group與 direct regression 至 GREEN。
2. `LAS-REV-002`
   - 先 fresh 跑 standalone-word Review group，確認 RED。
   - 在 direct test 補未列名 standalone word regression。
   - 以最小封閉 literal authority set 取代 capitalization shape。
   - 重跑 Review group、direct regression 與 positive controls 至 GREEN。
3. Fresh 跑完整 independent probes、direct suite、既有 re-review probes與七檔 regression suite。
4. 執行 compile、debug scan、diff check、changed-files allowlist 與 evidence safety scan。

禁止範圍維持派工卡契約；不修改任何 Review probe。
