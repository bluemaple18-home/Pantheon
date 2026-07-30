# LA-SL-01 RED → GREEN

## RED

Production code 變更前：

1. Fresh final Review probe：
   - 結果：`10 failed, 3 passed`
   - 十個 failure 精確涵蓋 ja／ko × 五類 semantic item。
   - 共同失敗：`READERS EVALUATE SOURCES CAREFULLY` 未觸發
     `native locale language` rejection。
2. 新 direct adversarial matrix：
   - 結果：`40 failed, 29 passed`
   - RED failures 涵蓋 ja／ko × 五類 semantic item，以及 Title Case、全大寫、
     未知 Title Case 與多個大寫 token。
   - 小寫 ASCII-only 句與既有 positives 已在 RED 階段正確通過。

## GREEN

最小 production seam 修改後：

1. Direct matrix 與 positives：`69 passed, 64 deselected`
2. Fresh final Review probe：`13 passed`
3. 完整 direct multilingual suite：`141 passed`

GREEN 保留：

- 自然日文與自然韓文。
- 日文純漢字 H2 `実践方法`。
- 目標語言文字內的 `OpenAI`、`API`、`GPT-5`、`2026`。
- 封閉 ASCII-only literal：單一 name、短 acronym、model code、number，以及
  `OpenAI GPT-5 2026` 的 bounded product/model topology。
