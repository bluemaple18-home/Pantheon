# APF-004-CREATE-RUN-ADAPTER-INTEGRATION

- 類型：主線整合與驗收
- Main baseline：`75dd38bd07f6d0bce4cc6657a52f1ede1eb0a4f9`
- Approved candidate：`d8f062bb1550cc7770d5783f1fd5b31fecaac54a`
- Reviewer：`019ffb27-b3ff-7dd3-94b1-c108c2736ab8`，verdict `APPROVED`
- 目標：以 fast-forward only 將 approved lineage 整合到 local `main`，並驗證主線。
- 禁止：production runtime、external model、publish、transaction、tag、push、deploy、schedule、canary。

## Gate

1. `main` 必須仍為 baseline，且為 candidate ancestor。
2. candidate worktree clean；approved commits 與 review evidence 可查。
3. 先在 candidate 跑 APF targeted、multilingual、`git diff --check main...HEAD`。
4. 只允許 fast-forward local `main`；不允許 merge commit、rebase、force、push。
5. 整合後在 main tree 重跑同組測試並確認 exact HEAD、clean。

## 回報

- `INTEGRATED_AND_ACCEPTED` 或 `BLOCKED`
- main before/after、測試、diff check、未執行事項。
