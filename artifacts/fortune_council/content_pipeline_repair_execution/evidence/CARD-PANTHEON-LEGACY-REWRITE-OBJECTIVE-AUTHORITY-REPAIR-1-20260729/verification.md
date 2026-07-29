# Legacy rewrite objective authority Repair-1 驗證紀錄

> 本檔保留初版交付紀錄；`a243edacd981b8f28c257b040a41a121efc34b64`
> 的 `REVIEW_NO_GO` 證明初版 code-only reconciliation 可造成 semantic false approve。
> 文末「Reviewer NO_GO follow-up」為目前有效的 authority 設計與驗證結果。

## 任務契約

- card：`CARD-PANTHEON-LEGACY-REWRITE-OBJECTIVE-AUTHORITY-REPAIR-1-20260729`
- finding：`LEGACY-REWRITE-OBJ-AUTH-001`
- base：`ca1e7bf89cb32e8d50aa933dfa125ed2280e51a2`
- worktree：`<repo-root>`
- 修改範圍：pipeline、對應測試與本卡 evidence
- 禁止動作：provider、push、deploy、publish、replacement、sub-agent

實體 card 未存在本 worktree 的 base tree；activation prompt 已內嵌完整卡片契約，因此未越界建立或修改 card。

## Capability 與 source context

- `worktree_capability_preflight.sh --prepare --with-codegraph` 的首次 bounded prepare 因 sandboxed `uv` cache 與 Node registry 無網路而中止。
- 改以已釘選的本機 runtime、禁止 dependency installer 後完成 prepare。
- CodeGraph：278 files、3,640 nodes、native backend，indexed HEAD 與 base SHA 相同。
- 已執行 task-specific `codegraph_context`，再以 graph search/explore 定位：
  - `run_writer_reviewer`
  - `rewrite_quality_findings`
  - `hydrate_review`
  - `reconcile_external_review_with_machine_gate`
  - `_reviewer_prompt`

## RED

指令：

```bash
.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py::test_rewrite_ignores_false_body_shape_review_without_spending_writer_repair -q
```

production-shaped fixture：

- run：`legacy-auto-sweep-v1-fortune-0013-chart-ziwei-11`
- article：`CHART-ZIWEI-11`
- 5 節 × 3 段
- 正文精確總長：1762 字
- 段落長度：`127,125,125,118,120,116,119,117,112,122,115,111,116,110,109`
- `rewrite_quality_findings == []`
- Reviewer：兩筆 `BODY_SHAPE_VIOLATION`

結果：`exit 1`；Writer 實際呼叫 2 次，測試要求 1 次。這證明錯誤客觀 finding 會消耗 Writer repair。

## 根因與修復

1. `run_writer_reviewer` 只對 `create` 套用 machine-owned reconciliation，`rewrite_existing_body` 未套用。
2. machine-owned code 比對為大小寫敏感，production 的大寫 `BODY_SHAPE_VIOLATION` 無法辨識。
3. `validate_review` 未嚴格驗證每筆 finding 的 `code/message`，malformed machine-owned finding 可能被誤忽略。

修復：

- 為 rewrite 建立封閉的 objective-only code allowlist，不包含搜尋意圖、語意、場景、動詞、限制、安全、錯別字或模板感。
- code 僅做 `strip + casefold` 後對封閉 allowlist 比對；未知 code 保留並 REJECT。
- `hydrate_review` 路徑透過嚴格 finding schema，將 malformed payload 轉成既有 hard-failure review。
- deterministic 非空時維持原有 short-circuit，Reviewer 無法覆寫。
- Reviewer prompt 明示 objective authority 邊界，同時保留語意與安全審查責任；這只是輔助，實際防線仍在 deterministic reconciliation。

## GREEN 與 acceptance

同一 production-shaped 指令修復後：

```text
1 passed in 0.04s
```

新增 acceptance 組：

```bash
.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py -q -k 'rewrite_ignores_false_body_shape or rewrite_malformed_machine_owned or rewrite_semantic_rejection_keeps or rewrite_deterministic_reject_never or rewrite_unknown_reviewer'
```

結果：

```text
7 passed, 104 deselected in 0.14s
```

涵蓋：

- deterministic clean + false body-shape finding：Writer/Reviewer 各 1 次，最終 APPROVE。
- 真正語意 finding：持續 REJECT。
- deterministic 非空：Reviewer 0 次，維持 REJECT。
- unknown finding：fail closed。
- malformed finding：hard-failure fail closed。
- `max_repairs=0/1/2`：Writer 與 Reviewer 都精確為 `max_repairs + 1` 次。

## Fresh regression

```text
.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py -q
111 passed in 55.78s

.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py tests/test_agy_content_publisher.py -q
99 passed, 1 warning in 16.14s

.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py -q
19 passed in 0.04s

git diff --check
PASS
```

唯一 warning 為既有 `DeprecationWarning: invalid escape sequence '\/'`，不在本卡修改範圍。

## 初版 Residual risk（已被 re-review 推翻）

- 初版曾判定封閉 allowlist 不會 false approve；`a243edac…` hostile seam 證明 semantic finding 錯標 machine-owned code 時仍會被刪除並提升為 APPROVE。
- 本卡使用 deterministic fixture 與 test doubles，未接觸真實 provider，符合禁止範圍。

## Reviewer NO_GO follow-up

### Provenance

- follow-up base：`a243edacd981b8f28c257b040a41a121efc34b64`
- base parent：`7cf63b5e40a1f5fd0c8ce3c05fe1f17e11274c47`
- Reviewer evidence：`repair-1-re-review.md`
- fast-forward 前後均確認本 detached worktree clean；未讀寫主工作區 dirty changes。
- CodeGraph 重新 index 至 follow-up base，共定位 6 個 `hydrate_review` rewrite callers：
  - `run_writer_reviewer`
  - `run_rewrite_repair`
  - `run_rewrite_release_generation`
  - `review_rewrite_release_final`
  - `run_rewrite_repair_closure`
  - `review_existing_candidate`

### Follow-up RED

1. production-shaped 1762 字 fixture 改用明確 semantic/objective schema 後，舊實作將 payload 視為 invalid review，final `REJECT`；預期 `APPROVE`。
2. isolated aggregate runner 收到 machine-green + 單篇 false objective observation 後，舊實作進入第 2 輪 Writer，超過預期 Writer=5。
3. `review_existing_candidate()` 對相同 false objective observation 產生 `REJECT`；預期 `APPROVE`。
4. `review_existing_candidate()` deterministic 非空時仍呼叫 Reviewer，觸發 `deterministic rejection must skip Reviewer`。

### Authority repair

- rewrite Reviewer schema 改為四個 exact fields：
  - `slot`
  - `semantic_verdict`
  - `semantic_findings`
  - `objective_observations`
- `semantic_verdict` 必須明確為 `APPROVE` 或 `REJECT`。
- semantic `APPROVE` 必須沒有 semantic findings；semantic `REJECT` 必須至少有一筆 semantic finding。
- objective observations 只接受封閉的本機可計算 code；unknown 或 malformed observation 轉為 hard-failure review。
- `hydrate_rewrite_review()` 只把 semantic verdict/findings 映射到 final review；objective observations 保留在 `external-review*.json` 作為模型原始證據，但不得推導或改寫 semantic verdict。
- hostile semantic finding 即使 code=`BODY_SHAPE_VIOLATION`，仍完整保留並 final `REJECT`。
- 6 個 rewrite review callers 全部改用同一 strict schema 與 hydration seam。
- deterministic 非空路徑在 main runner、isolated runner、release generation 與 existing-candidate 均 short-circuit Reviewer；review-only/closure entrypoints原有前置 deterministic clean 條件維持。
- create、optimize 與 translation 保留原 schema，未擴張本次 rewrite authority 變更。

### Follow-up acceptance

```text
.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py -q -k 'rewrite_ignores_false_body_shape or rewrite_semantic_reject_survives or rewrite_malformed_machine_owned or rewrite_semantic_rejection_keeps or rewrite_deterministic_reject_never or rewrite_unknown_reviewer or batch_002_isolated_runner or review_existing_rewrite or create_machine_length_repair_is_field_bounded'
12 passed, 102 deselected in 0.09s

.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py -q
114 passed in 55.92s

.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py tests/test_agy_content_publisher.py -q
99 passed, 1 warning in 16.36s

.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py -q
19 passed in 0.04s

git diff --check
PASS
```

Acceptance mapping：

- production 1762 字 false objective：Writer=1、Reviewer=1、semantic APPROVE、final APPROVE。
- hostile semantic mislabel：final REJECT，semantic message 未被刪除。
- aggregate isolated runner：Writer=5、Reviewer=1、internal repair=0、五篇 final APPROVE。
- existing candidate：同一 invariant，false objective final APPROVE；deterministic finding Reviewer=0。
- unknown semantic finding：REJECT；malformed payload：hard-failure REJECT。
- `max_repairs=0/1/2`：Writer/Reviewer 均精確 `max_repairs + 1`。

### Follow-up residual risk

- 新的 objective observation 同義 code 若未列入封閉集合，會 fail closed 成 invalid review，不會 false approve。
- 真實 provider 尚未在本卡執行；schema 與 prompt 均已更新，但本次證據限於 deterministic fixtures/test doubles。
- 唯一 warning 仍為既有 `DeprecationWarning: invalid escape sequence '\/'`，不在本卡範圍。
