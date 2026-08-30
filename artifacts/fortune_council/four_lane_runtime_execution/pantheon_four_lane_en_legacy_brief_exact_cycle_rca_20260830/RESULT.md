# EN legacy brief exact-cycle 停線 RCA

## 結論

唯一主裁決：`LEGACY_BRIEF_CROSS_VERSION_CONTRACT_GAP`。

exact production brief 的頂層多了一個合法 routing metadata `lane=i18n-rewrite`。current coordinator 的 legacy lane authority 與 current promotion preservation boundary 都明確接受這個欄位並要求它與 registry／identity envelope 一致；但 actual live multilingual executor 自 2026-07-24 起仍只接受四個頂層欄位，因而在任何 Writer job 建立前同步拋出：

```text
ValueError: translation brief fields are strict
```

這不是 provider、Writer、Reviewer 或 queue runner 故障。`COORDINATOR_ERROR_OBSERVABILITY_GAP_ONLY` 不是主因：雖然 coordinator 的 generic exception branch 只保存 `ValueError` 類型、吞掉 message，但隔離 A/B 已證明拿掉唯一多出的 `lane` 後，同一 current actor 立即走到 `ExternalJobPending` 並建立一筆 Writer outbox。`INVALID_LEGACY_BRIEF_DATA` 也不夠精確：這組 bytes 對 executor 確實非法，但同一 live actor 的 coordinator／promotion admission contract 把它視為合法 preservation input，因此根因是跨元件、跨 promotion lifecycle 的 contract 不一致。

## Locked incident 與 production mutation

- exact run：`auto-i18n-en-aa637e1bf05d3ad21429`
- accepted source：`73180233275840b0ab0e101f246e495ee6815fc9`
- live actor：`6541693e929a20cbcffe8b070085b5f1caec7a92`
- runtime generation：`g72-6541693e-new-lane-current-acceptance-20260829`
- 第二次 legal exact no-sweep coordinator：return code `1`、`status=failed`，registry `active → failed`，`error_type=ValueError`。
- exact brief raw SHA-256：`bcd31d23f5d8455ea21fea205827afd267a29f4c4533b0064a80154fbd8d12f3`。
- current failed registry raw SHA-256：`9bce7b085e306515e403d511ae7611223c88531b11e1f56f867ffb36ead02d14`。
- production delta：只改一筆 EN registry；run dir、JA／KO、candidate、review、Writer、outbox、provider、publish、push、tag 都是 `0`。
- stop line：禁止第三次 production coordinator／resume／reseed 嘗試。

上列 production facts 來自 activation acceptance 的 `en-exact-coordinator-corrected-cycle.receipt.json`、`en-exact-coordinator-corrected-cycle-comparison.json` 與 before／after snapshots；comparison 的 stop reason 同樣記錄「no writer job/outbox request，only EN registry active→failed」。

## 精確形成鏈

1. `<production-root>/actor/scripts/agy_gemini_outbox.py:1060` 的 `run_pipeline_tick` 讀取 exact `brief.json`；`mode=translate_existing` 路由到 multilingual `run_writer_reviewer`。
2. multilingual pipeline 在執行 planning／Writer 之前呼叫 `validate_translation_brief`。
3. `<production-root>/actor/scripts/agy_multilingual_pipeline.py:249-251` 的 current contract 是：

   ```python
   if set(brief) != {"schema_version", "run_id", "mode", "articles"}:
       raise ValueError("translation brief fields are strict")
   ```

4. exact brief fields 是 `articles, lane, mode, run_id, schema_version`；唯一額外欄位是 `lane=i18n-rewrite`，因此精確 message 為 `translation brief fields are strict`。
5. `<production-root>/actor/scripts/agy_gemini_coordinator.py:2560-2620` 的 `_advance` generic `except Exception` 把 registry 改為 `failed`，只持久化 `type(error).__name__`，沒有持久化 message。這是次要 observability gap，不是功能主因。

## 隔離重現與單變量 control

完整 machine evidence：`isolated-reproduction.json`。

- exact brief／registry 只讀複製到 `TemporaryDirectory`，以 manifest 指定 Python 與 actual live actor modules 執行；direct tick 穩定拋出相同 `ValueError`／message，temp outbox=`0`。
- 再建立一份 exact brief 隔離 copy，只移除頂層 `lane`，其他 payload 不變；current actor 走到 `ExternalJobPending`，temp outbox=`1`、role=`writer`。
- control copy SHA-256：`febaaa04f682a39a96f2ef0fa90b3e11b5e50a8c9fda96a3d9a0deca8d55e190`。
- 所有 temp root 已 cleanup；production write=`0`、provider=`0`、publish=`0`。

因此 RED-capable invariant test 很清楚：同一 translate brief 若被 lifecycle admission 接受，就不得只因一致的 `lane` routing metadata 在 executor preflight 失敗；反例必須在建立 Writer outbox 前穩定 RED。

## 最後相容 contract 與第一個拒絕機制

歷史不能支持「曾有某個 commit 成功執行 exact 五欄 bytes」：

- `c1885823496270cb195308aae2d72c09c5b0712e`（2026-07-24，`fix(content): require native multilingual rewrites`）首次加入 `validate_translation_brief`，從第一天就只允許四個頂層欄位；git blame 顯示 live actor 的 strict check／message 仍源自此 commit。
- `c1885823496` 的 parent `8d35181abd6a2d9e8ea2318f297973acf95e70e4` 尚無 `scripts/agy_multilingual_pipeline.py`，因此也不能算「會成功處理 exact 五欄 translation brief」的 executor version。
- exact run 在 `45942c29710fc58916addb8862f92c90444b29e8`（tag `v0.3.368`，2026-08-18）時註冊。該版本的正式 `prepare_translation_run` 產生四欄 brief，不含 `lane`，且會先通過同一 validator；這是此 run lifecycle 最後可證的相容 producer／consumer contract。
- `204a8bd8b86b37f411048983730ce1efb9fa2734`（2026-08-26，`Require translation seed lane identity`）把 lane 加到 seed API／registry identity envelope，但正式 `prepare_translation_run` 到 current actor 仍然不把 lane 寫入 brief。
- current brief 的 inode birth／mtime 同為 `2026-08-26T10:14:16+08:00`，晚於原註冊時間 `2026-08-18T11:04:26+08:00`；現有 filesystem／artifact evidence 只能證明它被 post-seed recreate／rewrite 成五欄 bytes，不能鎖定是哪個正式 writer。不得猜測 writer。

所以不存在可誠實命名的「最後成功處理 exact 五欄 bytes 的 commit」；第一個拒絕機制也不是 seed 後的新 validator commit，而是 post-seed brief 加入 `lane` 後首次撞上自 `c1885823496` 未變的 strict executor schema。current coordinator `<production-root>/actor/scripts/agy_gemini_coordinator.py:2652-2685` 與 promotion `<production-root>/actor/scripts/pantheon_content_runtime_promotion.py:363-397` 又都接受 explicit translation lane，讓不相容 brief 穿過 preservation／activation boundary。

## Durable invariant、owner、promotion boundary

Durable invariant：任何被 coordinator integrity 與 promotion preservation 接受的 `translate_existing` brief，必須可被同一 actor 的 `validate_translation_brief` 執行。schema v1 可接受 legacy 無 `lane`（routing authority 來自 registry envelope）；若 brief 明列 `lane`，只能是合法 i18n lane 且須與 registry／identity envelope 相同，不能在 executor 另以 unknown-field 拒絕。

Authoritative owner：

- brief schema／execution owner：`scripts/agy_multilingual_pipeline.py::validate_translation_brief`。
- lane routing identity owner：registry `lane` + `identity_envelope`，由 coordinator integrity 驗證。
- promotion boundary：`scripts/pantheon_content_runtime_promotion.py::_validate_run_identity_matches_brief`；它不得 preserve／activate 一份 current executor 不能解析的 brief。

這不是新增 authority；是讓既有三個 contract 使用同一可執行集合。

## 現有正式 operational seams 適用性

| seam | exact precondition 對帳 | 裁決 |
|---|---|---|
| `resume` | 只把 failed 改回 active 並移除 error；brief bytes 不變 | 不適用；必然重演 |
| `terminalize-pending` | 需要 exact `job_id/request_sha/model/role/attempt` 與未 claim outbox；本案 `last_job=null`、outbox=`0` | 不適用 |
| `terminalize-dangling-active` | 需要 registry active 且 run dir 實體遺失；本案 failed 且 run dir/brief 存在 | 不適用 |
| `retry-same-generation-locale-plan` | 只接受 `LocalePlanValidationError`、generation cache 與 job receipts；本案在 generation/Writer 前同步 `ValueError` | 不適用 |
| authorized next-generation reactivation | 需要 reviewer terminal reject 與 authority transition；本案 candidate/review=`0` | 不適用 |
| `replace-failed-external-job` | 需要 failed external `source_job_id`、request/correlation/failure category；本案沒有 external job | 不適用 |
| translation replacement/reseed | replacement 會先用同一 strict validator 驗 base brief；普通 enqueue 看見既有 registry 時只對 source/envelope，不重建 brief | 不適用；不能修正 bytes |

沒有既有正式 terminalize／retry／reseed seam 能安全消除這個 functional contract gap；資料也不是一筆已有 job 可正式 terminalize 的 pending。禁止用 generic 手改／刪檔繞過。

## 唯一 bounded next step

開一張 bounded Repair，frontier 嚴格鎖定最多 `1 source + 1 test`，本 RCA 不實作：

- source：`scripts/agy_multilingual_pipeline.py`，讓 `validate_translation_brief` 對 schema v1 接受 optional `lane`，並只接受 `i18n-new`／`i18n-rewrite`；既有無 lane brief繼續相容。
- test：`tests/test_agy_multilingual_pipeline.py`，以 exact legacy flat explicit-lane fixture 證明 validator 接受、第一 tick 走到一筆 Writer `ExternalJobPending`／outbox，另用 invalid lane 保留 fail-closed。

Why not less：純 `resume`／reseed 不改 deterministic invalid input；只補 coordinator error message 仍會功能失敗。Why not more：不需要 migration、registry、FSM、新 authority，也不需要改 coordinator 或 promotion；它們已具 lane/envelope consistency gate。

Repair 完成前 stop conditions：production coordinator／resume／reseed/provider/publish 全停；不得第三次嘗試。Repair 後仍須先過 exact isolated fixture RED→GREEN、受影響 test 與獨立 review；未閉合前不得 promotion 或 production retry。

## Acceptance status

- precise formation/message：PASS
- exact immutable isolated reproduction：PASS
- single-variable causal control：PASS
- historical contract boundary：PASS（並明列 exact 五欄 bytes 無成功 commit evidence）
- existing seam applicability：PASS／全部不適用
- single root verdict：`LEGACY_BRIEF_CROSS_VERSION_CONTRACT_GAP`
- production/provider/publish mutation：`0`
- next production attempt：`STOPPED`
- machine evidence JSON parse：PASS
- `git diff --check`：PASS
- final status：`RCA_COMPLETE_REPAIR_REQUIRED`
