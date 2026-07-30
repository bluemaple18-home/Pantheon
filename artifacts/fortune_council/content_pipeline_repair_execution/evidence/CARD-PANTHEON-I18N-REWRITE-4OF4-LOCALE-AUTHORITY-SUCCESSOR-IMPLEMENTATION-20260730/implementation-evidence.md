# Implementation evidence

## LA-SL-02

移除 `GENERAL_ENGLISH_WORDS` 與「每個 token 只要大寫／Title Case 即視為
entity」的多詞 authority。新的 ASCII literal contract 只允許：

- 單一 number。
- 2–6 字元的單一 ASCII acronym。
- 最長 24 字元、同時含字母與數字，且具有 uppercase 或 `-`／`+` 結構的
  model／product code。
- 最長 24 字元的單一 name token。
- 最多三個 token，且 topology 僅能是：
  - name／acronym + model code + optional number
  - model code + number(s)

因此一般多詞 ASCII-only item 無論大小寫、Title Case 或是否為未知字詞都會
fail closed；整個 item 只有符合上述 bounded topology 才能走 ASCII-only
exception。沒有新增一般詞表或外部語言套件。

## LA-SL-03

- en 分支未修改。
- ja 純漢字 positive 保持通過。
- per-item validation seam 與錯誤訊息未修改。
- prompt、request identity、continuation、outline rebuild、source coverage、
  hydration、Reviewer、SEO、canonical、安全與 publication code 均未修改。
- final Review probes 與既有 Review evidence 均未修改。

## Changed files and allowlist

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- 本卡實體 `.md`（依 dispatch amendment 精確帶入）
- 本卡專屬 evidence 目錄中的六個 receipt／handoff 檔

全部落在 amendment 後的 allowlist。

## Residual risks

- Deterministic gate 不查外部 entity registry；單一 Title Case name token 仍是
  bounded syntactic exception，而非語意實體認證。
- 不符合 bounded product/model topology 的多詞 ASCII proper noun 可能被拒絕。
  這是本卡要求的 fail-closed 取捨，可避免多詞一般句再次偽裝成 entity。
