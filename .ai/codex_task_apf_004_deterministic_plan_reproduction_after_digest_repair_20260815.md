---
id: APF-004-DETERMINISTIC-PLAN-REPRODUCTION-AFTER-DIGEST-REPAIR
title: 重產修復後 deterministic promotion plan
status: ready
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: implementation
cycle: 1
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
model_reason: production promotion 契約已固定；本卡只重產唯讀 plan 與 exact argv 證據，但 identity 漂移或誤寫的回退成本高
parent_candidate: 28b8b84b6dfa319d8151aac3bc1a6a819ae82aa1
traces_to:
  - FR-AGG-PROMOTE-PLAN-DIGEST-REPRO-001
  - SC-AGG-PROMOTE-PLAN-DETERMINISM-001
  - SC-AGG-PROMOTE-EXACT-ARGV-001
---

# APF-004｜重產修復後 deterministic promotion plan

## 任務五行卡

- 目標：在 plan-digest binding 修復已整合後，以 public CLI 重產兩次 deterministic production plan，並鎖定下一張 Gate A 卡所需的 exact apply argv；全程 production mutation=0。
- 可寫：`artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/deterministic_plan_reproduction_after_digest_repair_20260815/**`。
- 禁止：不得執行 `apply/rollback/finalize`；不得建立或修改 transaction root；不得 deploy/install/copy、寫 actor/manifest/plist/private stage、launchctl、create-run、外部模型、select/publish/transaction/tag/push/schedule；不得改 code/config/tests 或其他既有 evidence。
- 驗收：輸出 `PLAN_READY | BLOCKED`；兩次 plan digest 與 ordered transaction contract 完全一致，exact apply argv 只由 plan argv 加入 `--expected-plan-digest` 推導，且 production mutation=0。
- 交付：單一 evidence candidate commit；不 amend、不 push。回 candidate SHA、verdict、plan digest、exact argv digest、mutation summary、下一個所需授權。

## 固定來源與 authority

1. source commit 固定為 `28b8b84b6dfa319d8151aac3bc1a6a819ae82aa1`；工作分支只可比它多本張任務卡，不得有 runtime/code/config/test 差異。
2. public entrypoint 固定為 `python -m scripts.pantheon_content_runtime_promotion plan`；不得呼叫 internal function、手改 JSON、ad-hoc copy 或自造 CLI receipt。
3. 必須從當下實際 production actor、manifest、private stage、queue/state/run/gsc-copy、worker labels、Python executable 與 capacity receipt 重算 current identity；舊 plan 只可作欄位拓撲參考，不得沿用舊 digest 或宣稱 freshness。
4. capacity receipt 必須符合現有 raw receipt contract、實際 artifact SHA-256、`status=PASS` 與 stop-loss closed；若無可驗 freshness 的 receipt，回 `BLOCKED`，不得為了通過而修改 production 或偽造資料。
5. transaction root 只可作為 plan 中尚未建立的目標；前後都必須不存在，或證明既有 bytes 完全未變。既有 root 與預期不符時直接 `BLOCKED`，不得刪除、搬移或覆寫。

## 執行與證據契約

1. 先確認 cwd 為獨立 clean worktree、HEAD 包含本卡且 parent 為固定 source；先以 CodeGraph 找 public CLI seam，若無結果則限域讀取 `scripts/pantheon_content_runtime_promotion.py` 與對應測試確認。
2. 保存 sanitized pre-snapshot：source/actor HEAD-clean-origin、manifest、private stage、queue/state/run/gsc-copy、worker labels、transaction root、capacity receipt與 host capacity；不得落盤秘密或本機使用者路徑。
3. 由實際 artifacts 重建完整 plan argv，執行 public `plan` 兩次；保存每次 sanitized exact argv、stdout、stderr、exit code、payload 與 digest。
4. 兩次的 plan digest、ordered states、write set、backup set、rollback order、postchecks、current/target identity、generation與 correlation 必須 byte-semantically 一致。
5. 從核准的 plan argv 產生 `exact-apply-argv.json`：只可將 subcommand `plan` 改為 `apply`，並加入 `--expected-plan-digest <本次 plan digest>`；不得執行該 argv。另保存 canonical argv digest 與欄位來源映射。
6. 保存 sanitized post-snapshot並逐欄與 pre-snapshot 比對；actor、manifest、private stage、queue/state/run/gsc-copy、worker labels、transaction root與其他 production business state 必須零變化。
7. 驗證所有 JSON 可解析、artifact digest manifest閉合、secret/local-path sanitizer PASS、`git diff --check` PASS；evidence 只能使用 `<repo-root>`／`<repo-parent>`／`<runtime-root>` 等 placeholder。
8. 任一 identity 漂移、capacity receipt失效、輸出不 deterministic、transaction root被建立／修改、exact argv缺欄位或 production mutation非零，立即 `BLOCKED`；不得自行修 production state。

## 最小 evidence 清單

- `pre-snapshot.json`
- `plan-attempt-1.json`
- `plan-attempt-2.json`
- `exact-apply-argv.json`
- `argv-source-map.json`
- `post-snapshot.json`
- `production-mutation-summary.json`
- `verification.json`
- `receipt.json`
- `artifact-digests.json`

## 下一閘門

- 本卡不授權任何 production mutation。
- `PLAN_READY` 候選須交回主線，並由此 chain 既有 Reviewer thread 對固定 candidate SHA 做獨立審查；不得建立第二個 Reviewer identity。
- Reviewer 核准且主線整合後，才可另卡向使用者請求全新 Gate A `apply` 授權；舊授權不得沿用。
- 即使未來 apply 成功，也必須停在 `POSTCHECK_PASSED`；`finalize`、Gate B 與發文均需各自另卡、另授權。
