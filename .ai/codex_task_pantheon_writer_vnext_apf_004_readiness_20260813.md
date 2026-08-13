---
id: APF-004-READINESS
title: 驗證 Existing Publisher 小批 canary readiness
status: ready
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: implementation
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: production canary 前七段 capability、identity/correlation 與容量 stop-loss 是固定核心契約；本卡只做 synthetic readiness，不建立 canary
parent_candidate: 6b42de1fc3d7e3ac2a990fc53b05145c7a267493
traces_to:
  - US-004
  - FR-012
  - SC-001
  - SC-003
---

# APF-004-READINESS｜Existing Publisher 小批 canary readiness

## 任務五行卡

- 目標：以既有正式入口證明 `create→run→select→publish→transaction→tag→push` 與容量 stop-loss，判定 APF-004 是否可另行請求 production canary 授權。
- 可改：既有 capability receipt／formal preflight adapter、對應測試、專屬 receipt 與 readiness 文件；優先重用現有入口。
- 禁止：不得建立 canary、呼叫外部模型、正式 publish/tag/push/deploy/schedule、修改 LaunchAgent 或 production state。
- 驗收：七段各有正式入口、I/O、同一 correlation、identity、PASS 與 BLOCKED artifact；capacity 兩週期／回收／stop-loss 證據完整。
- 證據：官方 readiness gate 輸出 READY；若任何正式入口或容量證據缺失，輸出 BLOCKED 與唯一 remediation frontier，不得造假補值。

## 邊界

CHECKPOINT-A 已 PASS。APF-004 execution 仍被本卡、production capacity gate 與使用者明確 production 授權阻擋。本卡只做 synthetic／dry-run capability probe，`canary_created=false`。

## 實作契約

1. 先以 CodeGraph 與原始碼確認並重用：
   - `scripts.agy_content_publisher:formal_capability_preflight`
   - `scripts/pantheon_content_capability_receipt.py`
   - 現有 create/run/select/publish/transaction/tag/push synthetic probes 與測試。
2. 不得以 mock、文件文字、裸 shell、HTTP 200、branch/tag 存在或單一成功 log 代替正式入口證據。
3. 七段各保存獨立 positive PASS 與 fail-closed BLOCKED artifact；不可共用同一 artifact冒充正負向。
4. 全鏈使用同一 execution_line_id、correlation_id 與可驗證 actor/runtime identity；任一漂移 gate 必須 BLOCKED。
5. receipt 使用 ai-core `templates/production_canary_capability_receipt.json` 契約，並以 `production_canary_readiness_gate.py` 真實驗證。
6. capacity evidence 必須列所有 write paths、max bytes/file count、增長率、尖峰與保留期限；代表性 synthetic 試跑至少兩週期，含 free space、RSS、swap 前後、回收與 stop-loss。
7. 不得把 readiness READY 當作 canary 或發布授權；receipt 必須明示 `canary_created=false`、external mutations 全 false。
8. 若缺正式 entrypoint 或安全 synthetic seam，只能補最小 adapter；若需 production mutation 才能證明，停止並輸出 BLOCKED/remediation，不得執行。

## Allowlist

- scripts/agy_content_publisher.py
- scripts/pantheon_content_capability_receipt.py
- tests/test_agy_content_publisher_capability_receipt.py
- tests/test_agy_content_publisher.py
- docs/pantheon_writer_vnext_auto_vertical_chain.md
- artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness/**

若需要修改 coordinator、multilingual、scheduler、installer、LaunchAgent、文章／registry 或 allowlist 外 production code，停止並回報 scope change。

## 驗證

1. 七段 positive／negative matrix 全綠，identity/correlation/I/O closure 可重算。
2. official production canary readiness gate 回 `READY`；否則 candidate 必須是 `BLOCKED` evidence，不得宣稱 PASS。
3. storage capacity gate：兩週期、峰值、回收、stop-loss 全 PASS；缺任一即 NO-GO。
4. affected focused tests 與 `tests/test_agy_content_publisher.py` 通過。
5. `git diff --check`；worktree clean；單一 candidate commit。

## 交付

- 回報 READY 或 BLOCKED、candidate SHA、changed paths、七段 evidence、容量 receipt、official gate output。
- 明示未 create canary、publish、tag、push、deploy、schedule、production activation。
- 只交付 readiness candidate；不得開始 APF-004 execution。
