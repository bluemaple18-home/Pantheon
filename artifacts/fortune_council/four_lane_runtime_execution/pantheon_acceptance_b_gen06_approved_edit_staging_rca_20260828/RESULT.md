# RESULT: Gen06 approved edited candidate production staging RCA

status: `GO_FOR_ONE_BOUNDED_REPAIR`
root_verdict: `FORMAL_STAGING_SEAM_MISSING`
repair_authorized_by_rca: `YES — one bounded Repair only`
production_mutation: `0`
provider/coordinator/publish/tag/push: `0/0/0/0/0`

## Outcome

唯一根因是 translation-run authority 與 publisher handoff 之間從未實作 formal approved-edit bind/seal staging seam。這不是既有 seam 漏找、boundary expectation 錯誤、runtime actor drift或 publisher release failure。

## 四證據閉合

1. `NO_PRECEDENT`：全 history CLI只有 `prepare/run/review/apply/authorize-next-generation-after-reviewer-reject`；沒有 stage/bind/seal。最接近的 `c188582349...` 只支援同 run-dir 原地 edit review後直接 apply。
2. 形成鏈：`c188582349...` 留下 bind omission；`2b5da2f068...` 建 publisher direct apply/release boundary但未補 stage；`f12f24315d...` 只補 terminal reject → next generation。三者都是 HEAD `831c536...` ancestor。
3. durable invariant：publisher只能消費由 translation-run authority以 exact locks + formal approval + rollback receipt封存的 staged payload；Gen06／continuation／queue registry／publisher ledger history不可被隱式覆寫。現況缺 writer與reader contract。
4. RED-capable command已實跑：`red_harness_missing_approved_edit_stage.py` 在16項 identity checks全真後，以 public CLI `invalid choice` 穩定 RED；production root/run/queue/ledger/repo app-web before==after；Gen07 absent；外部與發布 side effects全0。

## 假說裁決

- A existing seam漏找／可組合：`FALSIFIED`。
- B intentional direct apply/publish、staging期待錯誤：`FALSIFIED`。
- C recovery/edit flow缺 formal bind/seal：`SUPPORTED`。

## Repair frontier

只新增 `stage-approved-edited-candidate` 的 plan-only/apply seal、publisher validated reader與對應 negative tests。完整 exact files/functions/SHA locks/rollback/idempotence/why-not-less/more 見 `implementation-frontier.md`。禁止 Gen07、manual overwrite、promotion、campaign、provider、publisher release或泛化新 subsystem。

## Evidence

- `red-reproduction.json`
- `red_harness_missing_approved_edit_stage.py`
- `git-archaeology.md`
- `authority-and-hypotheses.md`
- `implementation-frontier.md`
- `verification-receipt.json`
