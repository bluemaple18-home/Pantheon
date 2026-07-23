# Gemini V4 Shadow-002｜Independent Review Decision

## Verdict

`DELIVERED_CANDIDATE / GO / READY_FOR_LIMITED_ROLLOUT`

## Findings

未發現 P0–P3 具體問題。

## Decision basis

- 固定 candidate lineage、獨立clean worktree、Review provisioning與lock gate通過。
- Independent verifier `PASS`；59-byte stdout、request、ledger SHA、event chain、
  final anchor及所有 receipt／command bindings均獨立重算一致。
- Target invocation／process為 `1/1`；retry／fallback／automatic resend／second
  external call為 `0/0/0/0`。
- Real bundle通過privacy與closed-schema檢查。
- 三種 encoding `3/3 accepted`；13 mutations `13/13 rejected`。
- Regression為 `137 unique passed`；`py_compile`、allowlist與
  `git diff --check`通過。
- Review期間外部 Gemini／agy invocation為 `0`。

## Limited rollout boundary

GO只表示主線可另開activation卡，考慮：

- `AGY_GEMINI_V4_BROKER=1`仍是唯一明確opt-in；
- flag off維持legacy；
- flag on失敗不得fallback；
- 預設仍關閉；
- 僅公開sanitized非文章payload或明確授權的極小批次；
- 每次activation另鎖範圍、停止條件、observability與回退契約。

本Verdict不授權activation、預設切換、文章發布、merge、push、deploy或任何新的
external invocation。Provider internal model-call provenance維持 `UNKNOWN`。

## Remaining risk

- 僅有一次real canary，不能外推至長時間或其他payload。
- Privacy-safe bundle未保存當次executable path或binary，只能獨立驗證digest
  cross-binding與production pre-exec hash契約。
- Production process count為1不等於provider internal model call count可知。
