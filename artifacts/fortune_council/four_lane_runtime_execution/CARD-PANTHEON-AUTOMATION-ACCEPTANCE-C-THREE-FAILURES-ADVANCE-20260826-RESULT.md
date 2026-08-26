# Pantheon 三次失敗後前進自動化驗收 Result

status: `DELIVERED_CANDIDATE`
card_id: `CARD-PANTHEON-AUTOMATION-ACCEPTANCE-C-THREE-FAILURES-ADVANCE-20260826`
dispatch_key: `v1:2a5865ab4eb192d645f4127ef8dbcd4d42ead56923c6677bccc94f48c3a35b85`
activation_token: `act-v1:ce43d63a03a74ad9b06a9c23b1b164fd46123071efc316b6ce17b2d71ad58da0`

## Conclusion

卡 C 的隔離驗收已用 repo 正式 entrypoints 交付 candidate。正式 runtime manifest 對齊 actor `6477ab815e8aecca7d1e8e1588e6e5eba0fab001` 與 generation `g47-6477ab81-activation-only-20260826`，動態 queue/state/log 全在 task-owned `/private/tmp/pantheon-automation-acceptance-c-*`。

失敗 item F 透過正式 coordinator selector、outbox、runner 連續產生三次 closed `GeminiApiFailure / API_TIMEOUT / NETWORK` failure；第三次後正式 coordinator 將 F 轉為 terminal failed/manual-review equivalent state，`transport_attempts=3`，第四次 exact selector probe 不再選取 F。

下一個 item N 使用不同 run identity、不同 article identity 與不同 namespace，被正式 selector 選中並進入 active execution。為避免外部模型與副作用，N 在產生 pending outbox job 後停止，未交給 runner 處理。

## Key Evidence

- F run_id：`acceptance-c-fail-three-20260826`
- F article identity：`ACCEPTANCE-C-F`
- F attempts：
  - attempt 1：job `5056cbf11bffd93b1cf81179bf9c64ecd0c55b4e`, `transport_attempt=0`
  - attempt 2：job `acc29a8cf54c92c80b60eb534ea7de7339a79940`, `transport_attempt=1`
  - attempt 3：job `c688bdb2e515bc97925fc3b7d4a748bc900d9712`, `transport_attempt=2`
- F terminal state：`status=failed`, `error_code=API_TIMEOUT`, `failure_category=NETWORK`, `transport_attempts=3`
- fourth selector probe：`active=0`, `runner.status=idle`
- N run_id：`acceptance-c-next-identity-20260826`
- N article identity：`ACCEPTANCE-C-N`
- N pending execution job：`39f454e962cbfb495de30ca80a90fb6dfb085c7d`
- F/N identity different：true
- task cleanup：`/private/tmp/pantheon-automation-acceptance-c-hvr4fjcj` removed

## Zero Mutation

- production queue digest before/after：`831ee0b7fbbf9c939aad53904150157f060815c07c3482967bd8d5ca43bad4b9`
- production state digest before/after：`bf901c009448d0db4ae58c3030bdb0cff9f2f2542621c3a166689ab5d84a8a0c`
- production queue/state unchanged：true
- Publisher invoked：false
- Writer/Reviewer API invoked：false
- V4 broker invoked：false
- credential pool configured：false
- git push/tag/public URL invoked：false
- seven launchd services before/after：`STOPPED`

## Evidence Files

- `artifacts/fortune_council/four_lane_runtime_execution/automation_acceptance_c_three_failures_advance_20260826/machine-summary.json`
- `artifacts/fortune_council/four_lane_runtime_execution/automation_acceptance_c_three_failures_advance_20260826/run_acceptance.py`
- `artifacts/fortune_council/four_lane_runtime_execution/automation_acceptance_c_three_failures_advance_20260826/tick-error.json`

## Notes

`tick-error.json` records the final safe stop point for N: `ExternalJobPending` after selector execution created the pending outbox job. Earlier harness attempts hit formal fail-closed gates before mutation (`actor_root/head/env route` identity); those gates were corrected inside the allowlist harness without modifying source, production roots, launchd, remotes, or public content.

Final status is candidate delivery only. Mainline owns final GO/NO-GO, integration, and acceptance.
