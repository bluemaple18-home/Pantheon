---
id: CARD-PANTHEON-GEMINI-RATE-LIMIT-THROUGHPUT-REPAIR-001
status: DELIVERED_CANDIDATE
type: repair
chain_id: PANTHEON-GEMINI-RATE-LIMIT-THROUGHPUT-20260728
repair_cycle: 1
repair_budget: 1
source_candidate: 7e38274efda6b76eb2e5baf27b62d20bb9614292
required_direct_parent: e21d9f7f11ef0fbfd78224afb5027b57c6b07f61
review_evidence_commit: 3adf0746a6810d3a90e26cd3e966300c6d94ec66
---

# Pantheon Gemini rate-limit throughput Repair 001

## 範圍

本 Repair 只處理：

- `PGR-REV-001`：selected credential value 必須在 admission ordinal durable commit
  成功後才可 open/read。
- `PGR-REV-002`：production pool opt-in 時，coordinator 與四條 lane 必須取得
  同一組 pool、state、bounded cooldown contract。

未修改 allocator schema、cooldown schema、seeding、Publisher、multilingual、
SEO lifecycle、V4、文章、queue payload schema 或四條 lane 架構。

## 修復

### PGR-REV-001

`scripts/agy_gemini_runner.py` 現在先執行 `admission.commit()`，成功後才開啟並
讀取 selected credential。Injected commit failure regression 直接觀察：

- credential open/read：0
- ordinal durable：false
- provider construction/call：0
- failed terminal artifact：恰好 1
- production attempt terminal status：`failed`
- raw exception、credential path/value：未持久化

成功路徑另在 provider construction 與 transport call 兩個接縫取得 allocator
lock，證明 provider／HTTP 不在 allocator lock 內。

### PGR-REV-002

coordinator plist example 新增 bounded cooldown 預設。Installer 在 production
pool opt-in 時，把已完成 closed validation 的 pool、shared state、cooldown
同時注入 coordinator 與四條 lane；opt-out 時不注入 pool/state，也不要求
不存在的 pool。

Parity regression 解析五個實際安裝 plist，逐值比較 shared contract，並在
`new_only=0` 的 canary-off 路徑實際觸發 coordinator shared-root runner，確認
它取得同一組環境值。

## Fresh verification

完整結果見：

- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/pantheon_gemini_rate_limit_throughput_repair_001/verification.md`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/pantheon_gemini_rate_limit_throughput_repair_001/results.json`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/pantheon_gemini_rate_limit_throughput_repair_001/findings.json`

Multilingual 在 candidate 與 required parent 都是相同的 `16 passed, 2 failed`，
兩個失敗皆為既有 `missing_policy_contract`，分類為
`PRE_EXISTING_BASELINE`，本 Repair 未新增失敗。

## 交付邊界

狀態：`DELIVERED_CANDIDATE / READY_FOR_TARGETED_REVIEW`

本卡不宣稱 GO、已整合、已部署、已提高 RPD/TPM 硬上限或 production
throughput 已改善。未執行真實 Gemini/HTTP、真 credential、production
queue/state、LaunchAgent、deploy、canary、Publisher 或 publish。
