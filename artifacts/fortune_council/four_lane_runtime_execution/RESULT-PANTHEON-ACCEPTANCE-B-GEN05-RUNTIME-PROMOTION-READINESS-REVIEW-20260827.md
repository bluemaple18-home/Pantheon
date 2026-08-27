---
id: RESULT-PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION-READINESS-REVIEW-20260827
title: 審查｜第五代執行環境升版就緒度
reviewed_candidate: 2b9343bc5011f82e5a9d2a81cf1d03a61d80c97d
reviewed_parent: 28f36604fdfe399e06b559f37873ec06aec28d10
source_head: d0b2bbe05950291e04490b915bc35e1557ac3196
verdict: REVIEW_NO_GO
production_mutation: false
---

# Pantheon Acceptance B：gen05 runtime promotion readiness Review

## 裁決

`REVIEW_NO_GO`

候選 `2b9343bc5011f82e5a9d2a81cf1d03a61d80c97d` 不能升為 promotion apply 授權決策。主要阻塞是正式 promotion plan 不能從 committed artifact 與現 reviewer worktree 重現：候選 argv 與 plan artifact 綁定不存在的 source worktree 與不存在的 raw capacity receipt path，且 `readiness-decision.json` 把 raw capacity digest 當 promotion authority，但 repo 內實際保存的是 portable-redacted bytes。

## P1 Findings

### P1-001：正式 promotion plan 無法以候選 exact argv 重現

- Evidence：
  - `exact-plan-argv-798.json` 指向 `/Users/mattkuo/.codex/worktrees/1480/Pantheon` 作為 `--source-repo`，並指向 `/Users/mattkuo/.codex/worktrees/dfd6/.../planner-capacity-receipt-28f366-host.json` 作為 `--capacity-receipt`。
  - reviewer 環境中兩個路徑皆不存在。
  - 實際重跑候選 exact argv，正式入口回：`{"error": "source_repo is missing", "status": "NO-GO"}`，returncode `1`。
- Impact：
  - 任務卡要求 deterministic promotion plan validator 必須重跑並確認 target、actor/manifest/stage、plan digest、target manifest/generation 可重算。
  - 候選 GO 依賴的 `READY_TO_APPLY` 無法由正式入口在 reviewer worktree 重新產生，因此不能授權 promotion apply。
- Minimal repair frontier：
  - 重新產生可提交、可重算的 exact plan input，source repo 不得綁定消失的產生者 worktree。
  - committed capacity receipt path 與 digest 必須能直接通過 promotion planner 的 `_validate_capacity_receipt`。

### P1-002：Rule24 capacity authority 的 digest/bytes 契約不一致

- Evidence：
  - `readiness-decision.json` 宣告 `capacity_receipt_digest=6def7497...`，同時宣告 committed portable receipt SHA256 是 `28ffddce...`。
  - `planner-capacity-rule24-summary.json` 也明確區分 raw digest `6def7497...` 與 portable SHA `28ffddce...`。
  - 實際 `shasum -a 256 planner-capacity-receipt-28f366-host.json` 為 `28ffddce4c33bf0e38e34a53b7fb978d6123a08e5efc20c45ad3e0fa28d273b3`，不是 promotion plan 要求的 `6def7497...`。
  - `planner-capacity-receipt-28f366-host.json` 本體含 two cycles、RSS/swap、reclamation、stop-loss，但沒有可供 promotion planner 直接驗證的 raw bytes authority，也沒有 target `79884d8b...` binding。
- Impact：
  - Rule24 PASS 不能同時作為 repo-portable evidence 與 promotion planner capacity receipt authority。
  - 若以 committed bytes 重跑 planner 會 digest mismatch；若以 raw digest 重跑則依賴未提交、現已不存在的外部 worktree path。
- Minimal repair frontier：
  - 產生 fresh Rule24 host receipt，將正式 planner 要驗證的 exact bytes 提交進候選 evidence，並讓 readiness decision、plan argv、plan artifact 使用同一份 digest。
  - capacity receipt 需明確綁定 `79884d8bff7256aa9d1adcb7133162d7ac30b86d`、execution identity/correlation 與 authority boundary。

### P1-003：evidence-index 無法完整驗證 committed evidence set

- Evidence：
  - `evidence-index.json` 列出 125 個 evidence files。
  - reviewer 重算：JSON files `106` 全部可讀，但 evidence-index 有 2 個 missing paths：
    - `rule25-readiness/capability/sandbox/.git/agy-content-publisher.lifecycle.lock`
    - `rule25-readiness/capability/sandbox/.git/agy-content-publisher.transaction.lock`
  - `git ls-tree` 與工作樹實際檔案數都只有 124 個 evidence files；`.git/...` lock files 未被提交。
- Impact：
  - 候選的 evidence index 不能完整證明自身 artifact bytes。
  - 這會削弱 Rule25 package/official receipt 的 byte-level reproducibility；在高風險 promotion readiness gate 中屬阻塞。
- Minimal repair frontier：
  - 移除不可提交 `.git` lock path from evidence-index，或改以可提交 sandbox path 表示 lock evidence。
  - 重算 evidence-index，要求 all indexed files exist、byte length 與 SHA256 全部一致。

## 通過核對

- cwd：`/Users/mattkuo/.codex/worktrees/2eee/Pantheon`
- worktree：獨立 detached worktree；HEAD `d0b2bbe05950291e04490b915bc35e1557ac3196`；起始工作區 clean。
- candidate parent：`2b9343bc5011f82e5a9d2a81cf1d03a61d80c97d` parent 為 `28f36604fdfe399e06b559f37873ec06aec28d10`。
- candidate diff allowlist：`28f36604... → 2b9343bc...` 為 125 個新增檔；範圍是一個 RESULT 與專屬 evidence directory。
- target：candidate decision 指向 `79884d8bff7256aa9d1adcb7133162d7ac30b86d`。
- protected tripwire：`protected_changed_keys=[]`、`production_mutation_count=0`、`transaction_root_created=false`。
- continuation：`next_generation=5`、gen04 abandoned/non-resumable、gen05 `source-ref-map` exists、gen06 does not exist。
- Rule25 summary：`status=READY`、七段 create/run/select/publish/transaction/tag/push present、official ready `READY`、missing-push fixture `BLOCKED`、`canary_created=false`、`production_mutation=false`。

## 驗證

- CodeGraph：`codegraph_context` attempted；此 worktree 未初始化 CodeGraph，依卡片降級為限域檔案查核。
- `git status --porcelain=v1`：clean before review output。
- `git show --format='%H%n%P' --no-patch 2b9343bc5011f82e5a9d2a81cf1d03a61d80c97d`：parent confirmed `28f36604fdfe399e06b559f37873ec06aec28d10`。
- `git diff --name-status --no-renames 28f36604fdfe399e06b559f37873ec06aec28d10 2b9343bc5011f82e5a9d2a81cf1d03a61d80c97d`：125 added files, no modified/deleted files.
- Exact plan argv replay：returncode `1`, stdout `{"error": "source_repo is missing", "status": "NO-GO"}`。
- SHA256 checks：committed `planner-capacity-receipt-28f366-host.json` = `28ffddce4c33bf0e38e34a53b7fb978d6123a08e5efc20c45ad3e0fa28d273b3`; plan requires `6def7497a06f4d453934ea5cb6f8fffb518e21cc654b0bbf878212796a3913b5`。
- JSON parse check：106 candidate JSON files parsed successfully。
- Evidence index check：125 indexed files, 2 missing, 0 digest mismatches among existing files。
- `uv run pytest tests/test_pantheon_content_runtime_promotion.py tests/test_pantheon_rule24_signed_capacity_evidence.py tests/test_prepare_pantheon_canary_actor.py tests/test_pantheon_writer_vnext_runtime_activation_capacity.py`：102 passed。
- `git diff --check`：passed。

## Residual Risk

未重裁 gen04/gen05 RCA、topology Repair 或 Acceptance B 內容品質，符合任務卡禁止擴大範圍。Reviewer 沒有執行 promotion apply/finalize、provider、production gen05、publish、transaction、tag、push、deploy、launchctl 或 service mutation。
