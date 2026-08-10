---
card_id: CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-001
status: CARD_DRAFTED
execution_authorized: true
production_authorized: false
chain_id: PANTHEON-RUNTIME-AUTHORITY-ACTIVATION
role: implementation
cycle: 1
required_base_ref: codex/four-lane-formal-runtime-repair-2-candidate-20260810
required_base_sha: 80fa0641102fa08d03acb1ee2b91559e0700763a
source_kind: commit
source_sha: 80fa0641102fa08d03acb1ee2b91559e0700763a
supersedes_chain: PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN
supersession_reason: 舊鏈已達 Repair 2/2 且最終 REVIEW_NO_GO；本卡是新的 architecture root，不是 Repair-3。
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 四項架構契約已由最終 P1 證據與 handoff 固定，屬高影響但 bounded 的 filesystem authority、operation trace 與 activation barrier 實作；不再重開 authority fork，也不含 production mutation。
ownership: 可信 filesystem authority、實際 mutation trace、七服務 runtime identity 與 7/7 atomic activation barrier
traces_to:
  - FRA-001
  - FRA-002
  - FRA-003
  - FRA-004
  - SCA-001
  - SCA-002
  - SCA-003
  - SCA-004
allowlist:
  - artifacts/fortune_council/runtime_authority_activation_execution/CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-001.md
  - scripts/agy_content_publisher.py
  - scripts/agy_gemini_coordinator.py
  - scripts/agy_gemini_runner.py
  - scripts/pantheon_content_capability_adapter.py
  - scripts/pantheon_content_capacity_guard.py
  - scripts/pantheon_content_runtime_manifest.py
  - scripts/pantheon_runtime_fs_authority.py
  - scripts/pantheon_runtime_activation.py
  - tests/test_agy_content_publisher.py
  - tests/test_agy_gemini_coordinator.py
  - tests/test_agy_gemini_runner.py
  - tests/test_pantheon_content_capability_probe.py
  - tests/test_pantheon_content_capacity_guard.py
  - tests/test_pantheon_content_runtime_manifest.py
  - tests/test_pantheon_runtime_fs_authority.py
  - tests/test_pantheon_runtime_activation.py
  - artifacts/fortune_council/runtime_authority_activation_execution/evidence/runtime_authority_activation_001/**
forbidden_scope:
  - 舊 PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN 的 Repair-3、改名重置或 Reviewer 替換
  - Writer vNext 契約、prompt、內容政策、SEO metadata、Schema、FAQ、文章正文或前端
  - production queue/state、正式文章、publication、tag、push、deploy、launchctl 安裝／載入／重啟
  - queue、approval、publication、lock、retry 或 deployment 的第二套 control plane
  - 現有主工作區 dirty files、舊 review/evidence、共用 registry、sitemap、feed、redirects
  - 以 path resolve、前後 snapshot、mock PASS 或測試專用平行實作冒充 filesystem／mutation authority
evidence_path: artifacts/fortune_council/runtime_authority_activation_execution/evidence/runtime_authority_activation_001/
---

# 可信 Runtime Authority 與七服務原子啟動

## 五行派工卡

任務 ID｜`CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-001`；建立可信 directory-handle filesystem authority、實際 operation trace 與 7/7 atomic activation barrier。

派工對象｜單一嚴格實作 task；從固定候選 SHA 建立獨立 clean worktree，只交付 candidate commit，不負責 Review、merge、push、deploy 或 production。

任務目的｜關閉可重現的 parent-swap TOCTOU P1，並讓 coordinator、四 lane、Publisher、capacity guard 在第一次 queue/state I/O 前由同一 generation 與 runtime identity 原子放行。

可改範圍｜只限 frontmatter allowlist 的 runtime authority／activation source、public-behavior tests 與本卡唯一 evidence 目錄；必要的新 helper 必須保持單一用途。

驗收證據｜先跑 parent-swap RED，再以 dir-fd/no-follow/device+inode 契約轉 GREEN；operation trace 能記錄 transient create+remove；6/7、identity mismatch、stale generation 全部零 queue/state I/O，7/7 才放行；targeted tests、受影響 suite、`git diff --check` 與 allowlist inventory 通過。

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：可信 Runtime Authority 與七服務原子啟動
- 正在做什麼：以新的 architecture root 取代已耗盡 Repair 額度的舊鏈，封住 filesystem authority 並收斂七服務啟動契約。
- 現在狀態：`CARD_DRAFTED`；production 維持 `NO-GO`。

## Root Question

在不建立第二套 control plane、且不碰 production 的前提下，能否由可信 sandbox directory descriptor 執行相對 I/O，以實際 operation trace 證明所有 mutation，並讓七個正式服務只有在相同 runtime identity 的 7/7 readiness 完整成立時才開始 queue/state I/O？

## 固定事實與根因

1. 舊 chain 的最終權威結論是 `REVIEW_NO_GO / BLOCKED`，Repair generation 已達 `2/2`；禁止 Repair-3。
2. 固定來源 SHA `80fa0641102fa08d03acb1ee2b91559e0700763a` 可重現：containment validation 後、第一次 queue `mkdir/open` 前交換父目錄為外部 symlink，public result 仍回 `PASS`，外部 queue 已被建立。
3. 根因是 `_require_sandbox_descendant()` 只保存一般 resolved path；後續 I/O 沒有綁定可信 directory descriptor、`O_NOFOLLOW` 或 device/inode identity。
4. 現有 mutation receipt 以 before/after snapshot 推論，會漏掉 transaction worktree 的 create+remove transient mutation。
5. 舊候選與測試可作來源素材，但不得因既有 `137 passed`、`258 passed` 或單篇手動產文就宣稱 runtime、capacity 或 production ready。

## 可證偽假說與唯一 RED 迴圈

- H1：若根因是 lexical/resolved path 沒有持有 parent authority，則在 containment 返回後交換 parent symlink，現有 public preflight 會在 sandbox 外建立 queue；改為可信 dir-fd 相對 I/O 並核對 inode 後，同一測試應在任何外部 I/O 前 `BLOCKED`。
- H2：若 mutation 漏報源自終態 snapshot，則 create+remove 後 snapshot 相同仍會回 `sandbox_mutation=false`；改由實際 operation trace 推導後應回 `sandbox_mutation=true` 並保留 create/remove 事件。
- H3：若 barrier 只是配置狀態而非 I/O authority，則 6/7 或 stale generation 仍可能到達 queue/state boundary；把 generation token 綁到每次 I/O 前重驗後，call recorder 應保持零 I/O。

先新增並實際執行一個 public-behavior parent-swap test，使它只因上述外部 mutation 症狀失敗。import error、fixture error、private helper assertion 或只證明沒有 crash 不算 RED。GREEN 前不得另開第二個 RED。

## 需求

### FRA-001｜可信 sandbox directory authority

- 從已驗證的 sandbox root 開啟可信 directory descriptor；後續 queue、state、lock、transaction materialization 與 evidence I/O 只接受相對 component。
- 每段 traversal 使用平台可用的 directory/no-follow 語意；拒絕空 segment、`.`、`..`、absolute path、symlink component、非 directory parent 與跨 device/inode identity drift。
- 在實際 I/O 前後核對 anchor 與必要 parent 的 device/inode；失配即 fail loud，且外部 tree before/after identical。
- 不得只用 `Path.resolve()`、`is_relative_to()`、lexical prefix 或 preflight snapshot 作 authority。

### FRA-002｜實際 operation trace

- filesystem 與 Git mutation receipt 必須由實際被允許的 operation 事件產生，至少包含 operation、relative target、anchor identity、pre/post identity、result、correlation ID 與 runtime identity digest。
- transaction worktree create+remove 即使終態相同仍須被記為 sandbox mutation；production mutation 只可由可信 authority 與 operation target 推導。
- trace 必須 deterministic、可重算、fail-closed；不得以 caller 布林或手寫 PASS artifact 自證。

### FRA-003｜七服務 runtime identity

- coordinator、`new`、`rewrite`、`i18n-new`、`i18n-rewrite`、Publisher、capacity guard 共七個服務使用同一 versioned identity contract。
- identity 至少包含 manifest digest、queue root identity、state root identity、service/actor identity、code/runtime digest、config version 與 generation。
- 每個服務在第一次 queue/state read/write 前驗證；Publisher 在 publication/transaction boundary 前再驗證；缺欄或 mismatch 均零 I/O fail-closed。

### FRA-004｜7/7 atomic activation barrier

- readiness acknowledgement 綁 service identity、generation、runtime digest 與 correlation ID。
- 少於 7/7、重複 service、identity mismatch、manifest unreadable 或 stale generation 時 barrier 不得開啟。
- activation owner 只能原子發布單一 generation token；每個服務在 I/O 前重驗 token 與 identity。
- rollback 必須比對七服務實際載入的 previous identity；不一致回 `ROLLBACK_FAILED`，不得用設定檔或狀態文案冒充恢復。

## 成功準則

- SCA-001：deterministic parent-swap harness 在任何外部 `mkdir/open/tempfile/Git` 前 `BLOCKED`；外部 tree before/after identical。
- SCA-002：sandbox 內正式 Publisher/capability path 仍命中 publish、transaction、tag、push 的既有 production boundary，但全部保持 dry-run/fail-closed，無 network、tag、push 或 production mutation。
- SCA-003：operation trace 正確記錄 transaction create+remove，且可由 trace 重算 sandbox/production mutation 結論。
- SCA-004：七服務 7/7 同 identity 才能取得 generation token；6/7、任一 mismatch、stale token 與 rollback identity drift 均在 queue/state I/O 前拒絕。

## 垂直切片與 blocking edges

### Slice A｜Authority seam：RED → GREEN

建立唯一 parent-swap RED，將可信 dir-fd authority 接到現有 public preflight 的第一次 filesystem boundary，轉綠後重跑既有靜態 path-negative cases。Slice B/C 被 A 阻擋。

### Slice B｜Operation trace checkpoint

把 sandbox filesystem/Git receipt 改由實際 operation trace 推導，證明 create+remove transient mutation。只在 Slice A GREEN 後開始。完成後跑 Publisher/capability targeted suite。

### Slice C｜七服務 identity＋barrier

將既有 runtime identity/readiness 收斂到 7/7 atomic token，並在七服務 I/O seam 前重驗。只在 Slice B checkpoint 通過後開始；不得新增 daemon、queue 或 publication owner。

### Final checkpoint｜整批驗證

重跑所有受影響 suite、shell/plist 靜態驗證（若本卡實際變更 shell/plist；否則標記 not-applicable）、allowlist、debug-marker 與 `git diff --check`。不得執行 repository full suite 以外的 production/launchd/network 動作。

## 必跑驗證

至少執行：

```bash
<repo-root>/.venv/bin/python -m pytest \
  tests/test_agy_content_publisher.py \
  tests/test_pantheon_content_capability_probe.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_gemini_runner.py \
  tests/test_pantheon_content_capacity_guard.py \
  tests/test_pantheon_content_runtime_manifest.py \
  tests/test_pantheon_runtime_fs_authority.py \
  tests/test_pantheon_runtime_activation.py
git diff --check
```

另外保存：

- RED 與 GREEN 指令、exit code、症狀斷言。
- parent-swap、static path、transient mutation、6/7、7/7、identity mismatch、stale generation、rollback drift matrix。
- 實際 changed-files allowlist 比對與 `[DBG-` 清理結果。
- source SHA、candidate parent、candidate SHA、test receipt、`git status --short`。

## 停損與交付

- 同一 blocker 第三次失敗立即停止，不做第四次。
- 若需要 allowlist 外 source/test、外部 dependency、platform-specific unsafe fallback、production I/O 或重新定義 Writer／Publisher ownership，回 `BLOCKED / CONTRACT_EXPANSION_REQUIRED`。
- 交付只能是 clean candidate commit，狀態只能 `CANDIDATE_READY_FOR_REVIEW` 或 `BLOCKED`。
- 不得自行 Review、Repair、merge、push、deploy、建立 canary、啟動服務或宣稱 production ready。
- strict chain 後續最多 Repair-1、Repair-2；只有 P0/P1 finding 可 `REVIEW_NO_GO`，re-review 只驗原 finding 與 Repair regression。

## Frontier

本卡是目前唯一可執行 frontier。Writer vNext contract review、orchestration、production behavior、Publisher compatibility、capacity trial 與 capability/canary 全部 parked，直到本卡取得獨立 `REVIEW_GO`。
