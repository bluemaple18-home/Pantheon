# V3 Repair 2 Recovery Review｜NO_GO

## Verdict

- Spec axis：`NO_GO`
- Standards axis：`NO_GO`
- Chain status：`BLOCKED`
- Reviewed candidate：`f6a86a5884a55514133c9ce2ea9553c32444bca2`
- Repair generation：`2/2`；禁止 Repair 3。

## Finding

### [P1] 同 OS user 可自行讀取 owner token並在真實 spawn期間寫入 foreign terminal

- category：correctness / security / concurrency
- path：`scripts/agy_gemini_operations.py`（owner token落盤與record completion邊界）
- evidence：reviewer-owned probe以未接收token參數的同UID子程序掃描records tree，成功讀取token並經production writer寫入foreign terminal；`token_read=true`、`record_written=true`、`foreign_record_persisted=true`，同時target `Popen`仍啟動一次，最後才以`FileExistsError`發現競態。
- risk：production契約宣稱launcher期間由owner capability排除正常跨process writer，但同UID子程序能取得capability並在external process已啟動後破壞唯一terminal/gate契約。
- suggested_fix：不得把可由同UID讀取的token檔當作信任邊界；需使用不暴露給被啟動子程序的broker/parent-held capability或把records completion集中在單一可信writer，並在spawn前完成不可繞過的ownership判定。
- validation_gap：目前沒有證據能證明同UID writer不能取得token；現有application-level non-owner測試只覆蓋「刻意不讀token」情境。
- confidence：high。

## 已確認關閉

- 未持token且不自行探索token的application-level writer：在target spawn前遭拒，`target_popen_spawns=0`。
- raw callback entry與真實Popen spawn已分帳；callback進入一次不等於external process啟動。
- CLI missing 0-process方向未被本finding推翻。

## 執行與停損

Recovery Reviewer thread `019f87ac-e309-7f80-b5c0-3709ae27d008` 連續三次平台`systemError`，未形成commit；依契約沒有第四次。主線只執行該獨立Reviewer已建立的probe並固化原始輸出，未修改candidate。

重跑命令：

從 candidate `f6a86a5884a55514133c9ce2ea9553c32444bca2` 的 checkout／worktree 執行；clean main 尚未含candidate新增的`agy_gemini_operations.py`，不可在main直接執行並誤讀ImportError：

```bash
PYTHONPATH=. <repo-root>/.venv/bin/python <recovery-review-worktree>/artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_single_shot_v3_repair_002_recovery_review_001/reviewer_probes.py
```

## Mainline decision

Candidate不得整合。V3 chain已達Repair 2/2，依硬上限正式`BLOCKED`；不得以新finding、改卡名或新Reviewer重置Repair額度。未恢復內容線，未push、deploy或publish。
