---
id: REPAIR-PANTHEON-G8-ACTIVATION-ONLY-EXIT-78-PROVENANCE-20260822-RESULT
card_id: REPAIR-PANTHEON-G8-ACTIVATION-ONLY-EXIT-78-PROVENANCE-20260822
chain_id: PANTHEON-G8-ACTIVATION-ONLY-EXIT-78-CONTRACT-CLARIFICATION-20260822
finding_id: G8-EXIT78-P1-001
role: repair
status: repair_ready_for_review
verdict: REPAIR_READY_FOR_REVIEW
production_mutation: false
---

# G8 Exit 78 Provenance Repair RESULT

## 終局判定

`REPAIR_READY_FOR_REVIEW`

已完成離線 RCA、bounded authority seam、production-validator regression與 focused verification；未執行 production reset、Capacity、activation、canary、deploy、merge、tag或 push。

## Root cause

- Capacity production validator原本只驗 live activation-only plist aggregate、launchctl exact path／state／no-PID與 exit集合，對 `[78]`沒有 reset provenance輸入。
- validator未比較 target與old-live generation，same-generation fixture亦可通過並寫入 Capacity private stage。
- 正式 `--reset-publisher-activation-only`成功路徑只輸出文字；既有 `failure-receipt.json`只涵蓋失敗，無 durable success receipt可供 Capacity消費。

## RED → GREEN

```bash
PYTHONDONTWRITEBYTECODE=1 <main-workspace>/.venv/bin/python -m pytest -q -p no:cacheprovider <host-tmp>/test_g8_exit78_provenance_red.py
```

- RED：same live／target generation、缺 current reset receipt、launchctl exit `78`時，production installer仍 exit `0`、validator回 `PASS`並寫入 Capacity stage。
- GREEN：同一 command回 `1 passed`；production installer在任何 staging mutation前以 `publisher reset provenance missing`拒絕。

## Minimal repair

- reset每次開始前先使舊 `publisher-reset-receipt.json`失效；成功後在 rollback trap仍有效時，以 owner-only temporary file＋atomic replace寫入 durable receipt。
- receipt綁定 activation correlation、target manifest/runtime identity/generation、old-live identity/generation relation、Publisher post-reset plist receipt／launchctl identity，以及 other-six pre/post plist digest／launchctl identity。
- success receipt writer只消費 reset既有 backup與新增 read-only post snapshots；沒有第二次 bootstrap、bootout或其他 service mutation。
- Capacity installer傳入固定 receipt path與 caller correlation。validator只有觀察到 `[78]`才驗完整 provenance；`absent`／`0`不新增 receipt前置條件。
- target same-generation、missing／stale receipt、correlation、Publisher identity或 other-six unchanged proof drift均 fail closed；其他 nonzero、PID與path drift沿用既有拒絕。

## Regression matrix

| Case | 結果 |
|---|---|
| target-newer＋current receipt＋matching correlation＋`78` | PASS；只寫 Capacity private stage |
| same-generation＋`78` | PASS；拒絕 |
| missing／stale receipt＋`78` | PASS；拒絕 |
| correlation／Publisher identity／other-six proof drift＋`78` | PASS；拒絕 |
| `absent`／`0`、無 reset receipt | PASS；既有 inert語意不變 |
| 其他 nonzero、PID、path／identity drift | PASS；拒絕 |
| reset promoted-manifest lifecycle child exit `78` | PASS；durable receipt標記 target-newer並保存 old-live generation |
| reset失敗前存在 stale success receipt | PASS；舊 receipt先失效，無法重用 |

## Verification

- Capacity focused suite：`59 passed`。
- coordinator reset focused suite：`20 passed, 244 deselected`。
- G8 production preactivation suite：`41 passed`。
- `bash -n`：兩個受影響 installer皆 PASS。
- `git diff --check`：PASS。
- `[DBG-...]`掃描：無殘留。
- CodeGraph已先查詢；本 worktree未初始化 index，依卡片改採批准檔案的限域 source讀取。

## Scope

Tracked diff只包含卡片原 allowlist、主線追加批准的 reset producer／coordinator tests，以及本唯一 RESULT。未修改 Publisher workload child、selector、ordering、rollback、production state或共享整合檔。
