# APF-004-GATE2-ACTIVATION-ONLY-INTEGRATION-001

- 狀態：INTEGRATION / NO LIVE MUTATION
- Base：`de13ef0de5d122cbe66831ede20b4a62cc6e37a1`
- Approved candidate：`ba4afa33577ae8160057a80124dfc7887fe985d2`
- Reviewer：`019ffb96-c9fc-7463-856f-aa37988846df`
- Verdict：`REVIEW_APPROVED`
- 目標：將 activation-only public mode、legacy pre-mutation fail-closed 與 normal authority isolation 完整整合成單一 promotion candidate commit。
- 可改檔案：兩張 repair card、兩份 repair evidence、coordinator installer、runtime manifest helper、兩個直接 test module、本 integration card 與 integration evidence。
- 驗證：P1 zero-mutation edge、activation-only positive、legacy negative、normal success/rollback、expected-mode aggregate/runtime、affected coordinator、runtime suite、三 installer `bash -n`、DBG/secret/path/binary、`git diff/show --check`。
- 禁止：push、merge、deploy、live install/activate/launchctl/runtime write、外部模型、create/run/select/publish/transaction/tag/schedule。
- 驗收：`INTEGRATION_READY | BLOCKED`；附 promotion SHA、exact changed files、test counts；`mutation_executed=false`。
