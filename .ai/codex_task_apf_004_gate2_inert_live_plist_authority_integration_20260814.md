# APF-004-GATE2-INERT-LIVE-PLIST-AUTHORITY-INTEGRATION-001

- base：`d3f621d9849cfef1857b9765914243210ed12e79`
- candidate：`91c2c4c74a5827e6a06ef3f8994f1208c385ddc1`
- review：`REVIEW_GO`；無 P0/P1
- 目標：在 clean promotion worktree 整合 exact candidate
- allowlist：candidate四檔、本卡、integration evidence
- 驗收：blob equality、34 targeted、59 affected、42 runtime、三 bash-n、drift scans、`diff/show --check`
- 禁止：production mutation、push前未驗證、發文、修改 root dirty checkout
- evidence：`.ai/evidence/apf_004_gate2_inert_live_plist_authority_integration_001.md`
