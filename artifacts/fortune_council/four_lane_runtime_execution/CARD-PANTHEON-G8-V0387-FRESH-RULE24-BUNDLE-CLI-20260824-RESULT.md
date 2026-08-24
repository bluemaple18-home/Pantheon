---
id: PANTHEON-G8-V0387-FRESH-RULE24-BUNDLE-CLI-20260824-RESULT
verdict: DELIVERED_CANDIDATE
---

# V0387 fresh Rule24 bundle CLI result

## 交付內容

已在容量 script 增加正式 `bundle` CLI：讀取 explicit runtime receipt、brief、bounded policy 與 actor identity，要求 existing canonical `/private/tmp` task root，並限制 evidence/sandbox 為 task root 的互不重疊 strict descendants。入口呼叫既有 `run_capacity_proof_evidence_bundle`，輸出 machine-readable unsigned summary 與明確 exit code。未複製容量判斷、未簽 DSSE、未寫 production。

已補 argparse `bundle --help`、happy path delegation、explicit task root、production/outside-root、symlink escape、invalid/unbounded policy 與 missing input fail-closed tests；所有負向測試皆驗證 bundle API 未被呼叫。

## 驗證

證據詳見 `g8_v0387_fresh_rule24_bundle_cli_20260824/verification-receipt.md`。

使用主線 venv 實測：capacity tests `25 passed`，promotion regression `27 passed`。CLI help、py_compile、JSON parse 與 diff check 均通過。

## 邊界

未執行 production runtime、LaunchAgents、remote、promotion、DSSE signing、安裝、push、tag 或下一卡派工。
