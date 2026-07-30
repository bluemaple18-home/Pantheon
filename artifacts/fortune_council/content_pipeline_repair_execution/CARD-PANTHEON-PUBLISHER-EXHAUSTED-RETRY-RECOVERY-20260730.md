---
card_id: CARD-PANTHEON-PUBLISHER-EXHAUSTED-RETRY-RECOVERY-20260730
role: implementation
status: LOCAL_CANDIDATE_READY
thickness: strict
risk: high
required_base_sha: ac042b42b94667603d108f2e33217006111641c8
user_authorization: 搞定他吧
---

# 目標

補上 Publisher 缺少的 exhausted create retry recovery 能力，讓已完整回復、
candidate 仍保留且未發布的 run 可在 operator 明確授權後取得一次新的 retry budget。

# 邊界

- 只改 `scripts/agy_content_publisher.py`、直接測試與本卡 evidence。
- 必須支援 dry-run。
- 必須驗證 retry record、FAILED_RECOVERED evidence、queue candidate/review、
  ledger 與 policy rejection 狀態。
- 每次恢復必須留下 audit receipt；不得直接刪除或手改 production JSON。
- 不降低文章品質、Reviewer、release、push 或 deployment gate。

# 驗收

1. 無效 evidence、錯誤不符、已發布、已 quarantine 或非 exhausted 狀態 fail closed。
2. dry-run 不修改 retry 或 evidence。
3. 正式 recovery 原子寫入新的 retry eligibility，舊紀錄 hash 與原因可追溯。
4. 恢復後只有指定 run 重新可被 collector 選取。
5. Publisher、Web、完整受影響測試與 `git diff --check` 通過。
