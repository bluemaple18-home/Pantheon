---
id: CARD-PANTHEON-G8-PUBLISHER-RESET-STAGE-VALIDATION-REPAIR-20260821-RESULT
card_id: CARD-PANTHEON-G8-PUBLISHER-RESET-STAGE-VALIDATION-REPAIR-20260821
status: candidate
terminal_state: CANDIDATE READY
---

# G8 Publisher reset stage-validation 修復 RESULT

## 結果

`CANDIDATE READY`

`--reset-publisher-activation-only` 現在會先 canonicalize ambient temp directory，再於 canonical path 建立 reset plist。`publisher-plist-receipt` 的 canonical realpath／owner／mode gate 完全保留；若 activation-only temp receipt 為 `NO-GO`，installer 會把完整結果寫到 stderr 並在 mutation 前 fail closed。

candidate full SHA 由包含本 RESULT 的單一 commit object 決定，列於正式 thread terminal handoff；commit 無法在自身內容中可靠自我引用其 SHA。

## Root Cause

正式環境的 `TMPDIR` 使用 `/var/folders/...` spelling，但 `Path.resolve(strict=True)` 得到 `/private/var/folders/...`。Installer 原先直接以 `${TMPDIR}` 建立 `PUBLISHER_RESET_TEMP`，因此 temp plist 的輸入 path 不是 canonical spelling；正式 `publisher-plist-receipt --activation-mode activation-only` 正確回傳：

```json
{"status":"NO-GO","error":"plist canonical realpath or owner mismatch"}
```

該 receipt stdout 原本被 `>/dev/null` 丟棄，外層只留下 `publisher_reset_stage_validation`、exit `1` 與空 stdout/stderr。先前 `/private/tmp` 診斷會 PASS，正是因為該 path 已 canonical。

## Primitive Failure Matrix

| Primitive | Production-shaped evidence | 修復契約 |
| --- | --- | --- |
| stage directory／manifest／generation／max-runs receipt | PASS | 不變 |
| staged Publisher formal preflight | PASS | 不變 |
| ambient temp directory realpath | alias spelling | canonicalize 後使用 |
| mktemp | PASS | 改在 canonical directory 建檔 |
| copy／chmod 600 | PASS | 不變 |
| live argv 無 activation-only | PASS | 不變 |
| RunAtLoad／StartInterval／KeepAlive | PASS | 不變 |
| live normal receipt | PASS | 不變 |
| live identity fields／service label | PASS | 不變 |
| one-shot transform／plutil | PASS | 不變 |
| activation-only argv transform／plutil | PASS | 不變 |
| temp activation-only receipt | RED：canonical realpath mismatch | canonical path 後 PASS |
| receipt failure observability | RED：stdout 被吞 | 完整 NO-GO 轉寫 stderr |
| pre-mutation live plist／launchctl／其他六服務 | 零變更 | 零變更 |
| Publisher／其他六服務 child I/O | `0` | `0` |

## Changed Files

- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `tests/test_agy_gemini_coordinator.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-PUBLISHER-RESET-STAGE-VALIDATION-REPAIR-20260821-RESULT.md`

## 驗證

精確 RED：

```text
<main-workspace>/.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -k canonicalizes_ambient_tmpdir_alias -q
1 failed, 254 deselected
returncode=1, stdout='', stderr=''
```

修復後 regression：

```text
<main-workspace>/.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -k 'canonicalizes_ambient_tmpdir_alias or reports_temp_receipt_failure_before_mutation' -q
2 passed, 254 deselected
```

Focused reset suite：

```text
<main-workspace>/.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -k publisher_terminal_reset -q
16 passed, 240 deselected
```

- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`：PASS
- `git diff --check`：PASS
- `[DBG-...]` marker 清查：PASS，無殘留

## 未做

- 未碰 production runtime、queue、actor、LaunchAgents 或 launchctl。
- 未重跑正式 reset、Capacity、Rule25 或 Publisher activation。
- 未修改 `scripts/pantheon_content_runtime_manifest.py` 或放寬 canonical／owner／mode gate。
- 未執行 release 全套。
- 未 push、tag 或 deploy。

## 未驗

- 未在 production `/var/folders` 實體 TMPDIR 執行 reset；僅以 real directory 加 symlink alias 的 focused fixture 重現相同語義。
- 未驗正式 reset 後的七服務終態、Capacity、Rule25 與 exact-run transaction。

## 殘餘風險

- Candidate 尚未經獨立 review 或 production continuation 驗證。
- 若 ambient TMPDIR 不存在或無法 canonicalize，reset 會在 mutation 前以穩定 stderr fail closed；本修復不嘗試 fallback 到其他 temp root。
- 正式 chain 先前已命中 NO RETRY；本 candidate 不構成再次執行 production reset 的授權。
