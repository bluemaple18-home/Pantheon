# V4 Architecture Review｜NO_GO

## Verdict

- Spec axis：`NO_GO`
- Standards axis：`NO_GO`
- Architecture verdict：`NO_GO`
- Reviewed candidate：`735d2850bd89bf3e4b29748f310981ba4d855709`
- Reviewed range：`8a4ade5bcadd16fa8e5a7bc0d14e730041b43088..735d2850bd89bf3e4b29748f310981ba4d855709`
- Decision：方案 B 不可進入 production implementation。存在 process accounting、FD isolation、crash replay、threat boundary 與證據誠實性的 P1 finding。

## Findings

### [P1] broker crash 的未記錄 spawn 被錯報為 0 process

- severity：`P1`
- category：`correctness / process_accounting / crash_replay`
- path:line：`scripts/agy_gemini_v4_architecture_probe.py:80`
- evidence：reviewer-owned probe 建立兩個相同 binding 的真實 crash case。其一在 `BROKER_ATTEMPTED` 後、spawn 前退出；另一個已實際啟動 child 並留下 marker，但在寫入 `PROCESS_STARTED` 前退出。兩份 ledger byte-identical；後者 replay 仍回 `gemini_process_starts=0`。`results.json` 的 `crash_and_exec_boundaries.before_and_after_spawn_ledgers_byte_identical=true`、`actual_child_marker=true` 與 replay 0 count 可重現。
- risk：crash window 內已發生的 Gemini CLI process 會被當成 0，而不是 `ambiguous/unknown`；這直接違反不得猜 process count 的核心契約，後續 recovery 可能誤判可安全重送。
- suggested_fix：定義 durable fork/exec handshake 與 typed replay status；只有 durable start evidence 才可回 1，只有確定未跨 spawn 邊界才可回 0，其餘必須回 `ambiguous`。不得從 broker attempt 推算 process count。
- validation_gap：candidate 只有同一 process 依序寫入事件的模擬，沒有真實 broker crash-before-spawn、crash-after-spawn-before-event 與 orphan child probe。
- confidence：`high`

### [P1] replay 不是所宣稱的 typed state machine

- severity：`P1`
- category：`correctness / replay_schema`
- path:line：`scripts/agy_gemini_v4_architecture_probe.py:109`
- evidence：fresh probe 以合法 hash chain 寫入三種非法序列，candidate 全部回 `complete=true`：`PROCESS_TERMINAL` 先於 `PROCESS_STARTED`、第二個重新串鏈的 `OPERATION_CREATED`、`process_ordinal=99` 加非法 terminal outcome。結果位於 `replay_adversarial.out_of_order`、`rechained_duplicate_operation_created` 與 `invalid_terminal_and_ordinal`。
- risk：malformed、duplicate 或錯序 ledger 可被認證為 complete；因此 replay completeness、0/1 process accounting 與 terminal outcome 都不可信。
- suggested_fix：以事件專屬 schema 加嚴格 FSM 驗證完整序列：恰一個 operation、恰一個 broker attempt、合法 fork/exec/start/terminal 次序、固定 ordinal、outcome allowlist、禁止未知欄位或明確版本化。
- validation_gap：現有測試只注入 exact duplicate 與 truncated tail；未測合法重串鏈的 duplicate、out-of-order、非法欄位與非法 outcome。
- confidence：`high`

### [P1] Option B 的 FD isolation 與 broker accounting 沒有被 POC 實測

- severity：`P1`
- category：`security / fd_isolation / evidence_honesty`
- path:line：`scripts/agy_gemini_v4_architecture_probe.py:208`
- evidence：`_fd_probe` 由 parent 先執行一個只寫 FD 的 subprocess，再由 parent 另起 `gemini_child`；Gemini 並非由 broker exec。broker 收到的 FD 實測仍為 inheritable。另 `_operation_probe(..., broker=True)` 只多 append `BROKER_ATTEMPTED`，實際 `Popen` 仍在同一 reviewer process。fresh probes 證明正確 `close_fds=True` 可阻擋 FD，但 wrong `close_fds=False`、wrong `pass_fds` 與 foreign inherited FD 均能讓 child 寫入。`candidate_evidence_structure` 四項皆為 false。
- risk：matrix 將未實作、未走過的 broker→Gemini 邊界標成 `PREVENTED/DETECTED`，可能使下一張 implementation 卡沿用錯誤 FD policy，讓 Gemini child 或 foreign FD 取得 writer authority。
- suggested_fix：POC 必須由真實 broker 收到唯一 allowlisted ledger FD，再由該 broker exec fake Gemini；在 broker 內明確設 CLOEXEC／`close_fds=True` 且不傳 ledger FD，並驗證 wrong `close_fds/pass_fds`、foreign inherited FD 都 fail closed。Option B process matrix必須由此真實 broker path 產生。
- validation_gap：現有 focused test 只重述 `_fd_probe` 的三個布林值，沒有觀察 broker 啟動 target 的 FD table。
- confidence：`high`

### [P1] same-UID full replacement 在缺少外部 anchor 時仍被接受

- severity：`P1`
- category：`security / threat_boundary / tamper_evidence`
- path:line：`docs/pantheon_gemini_reviewer_v4_architecture.md:49`
- evidence：same-UID subprocess 可直接覆寫 ledger。raw garbage 相對舊 anchor 會被偵測；但 attacker 改寫成另一份自洽 hash chain 後，`replay(..., external_anchor=None)` 回 `complete=true`，只有提供舊 external anchor 才回 `EXTERNAL_ANCHOR_MISMATCH`。文件與 proposed caller API 未鎖定 anchor 的獨立 owner、持久位置、crash lifecycle 或 recovery 取得方式。
- risk：parent/broker crash 正是方案 B 要處理的情境；若 external anchor 只在已退出 process 記憶中，recovery 會讓 ledger 自證，same-UID attacker 可替換完整 history 而不被偵測。append-only 與 hash chain只能提供相對可信 anchor 的 tamper evidence，不能提供 immutability。
- suggested_fix：implementation contract 必須指定 ledger 之外的可信 anchor owner、原子更新順序、crash recovery 與讀取授權；若做不到，same-UID full replacement 必須標為 `OUT_OF_SCOPE`，不可標 `DETECTED`。
- validation_gap：candidate 只測單一 bytes replacement 且永遠傳入舊 in-memory anchor，未測 crash 後 anchor 缺失或整鏈重寫。
- confidence：`high`

### [P1] preflight missing 與 post-fork exec failure 未分帳

- severity：`P1`
- category：`correctness / event_schema / process_accounting`
- path:line：`scripts/agy_gemini_v4_architecture_probe.py:19`
- evidence：`EVENT_TYPES` 沒有 exec-failure event；`preflight_missing` 是直接回傳的 hard-coded branch，未觸發 OS exec。fresh probe 對「preflight 判定 missing」與「實際 `Popen` 遭 `FileNotFoundError`」建立的 ledger byte-identical，兩者都 replay 為 complete、0 process。`exec_failure_event_supported=false`。
- risk：executable 在 preflight 與 exec 間消失、權限改變或 loader 失敗時，ledger 無法區分根本沒 fork/exec attempt 與 exec boundary failure；migration/recovery 無法誠實解釋 0 count 與 failure phase。
- suggested_fix：schema 明確分離 preflight rejection、broker/fork attempt、exec failure、successful Gemini process start 與 terminal；加入 executable-race probe並鎖定各分支的 0/1/unknown 語意。
- validation_gap：現有 tests 只呼叫 `_run_fake("preflight_missing")`，沒有真實 missing executable 或 executable replacement race。
- confidence：`high`

### [P2] matrix 結論由 literals 產生，沒有由 observables 導出

- severity：`P2`
- category：`testing / evidence_honesty`
- path:line：`scripts/agy_gemini_v4_architecture_probe.py:313`
- evidence：12 列 A/B/C status 與 evidence 都是固定 tuple；runtime evidence 與 matrix cells 沒有 reference、predicate 或 derivation。tests 只斷言 literal status 存在且屬於 allowlist，兩次 byte-identical只能證明固定輸出穩定。
- risk：probe 行為即使退化，matrix 仍可保持相同 verdict；stored matrix 不能作為 architecture acceptance evidence。
- suggested_fix：每個 supported cell 應引用一個具體 observable 與判定 predicate，由 fresh run 導出 status；沒有 executable observable 的 cell 必須 `UNSUPPORTED`。
- validation_gap：沒有 mutation/negative control 證明 observable 改變會讓 matrix cell fail 或降級。
- confidence：`high`

### [P2] caller API 與 implementation allowlist 尚不足以直接開 bounded implementation

- severity：`P2`
- category：`maintainability / migration / api_contract`
- path:line：`docs/pantheon_gemini_reviewer_v4_architecture.md:73`
- evidence：API 只有 `ledger_sink=caller_opened_sink`，未定義 broker command framing、FD allowlist、external-anchor ownership、exec handshake、replay status enum、PID 僅作觀察值而非 identity 的規則，亦未鎖定現有 `_generate_with_receipt`、outbox transport與多個 caller 中哪一條由 feature flag 接入。現行 caller仍含 runtime retry receipt 與多層 generation loop。
- risk：下一張 implementation 卡仍需自行決定安全關鍵接口與 caller cutover，超出「bounded implementation」而容易重建 V3 類信任邊界。
- suggested_fix：先修訂 architecture contract，鎖定單一 broker entrypoint、wire schema、FD close policy、anchor owner、exact caller/callsite、feature flag、舊 retry 行為處置與 focused test 檔名，再派 implementation。
- validation_gap：沒有 caller-level fake executable trace證明 proposed API 可無歧義接入指定 production path，且每 operation 維持 0/1 process。
- confidence：`high`

## Spec axis assessment

- 三方案可讀且 C 所有 matrix cells 均為 `UNSUPPORTED`：`PASS`。
- 不建立 filesystem token；provider internal calls 保持 `UNKNOWN`：`PASS`。
- Gemini child不繼承ledger FD/capability/records path/writer authority：`UNPROVEN`；現有 POC 沒走 broker→Gemini exec。
- logical operation、broker/fork attempt、Gemini process start、exec failure、terminal分帳：`FAIL`；缺 exec failure，crash window回錯 count。
- crash/partial replay只能 complete/blocked/ambiguous：`FAIL`；只有 boolean complete，且非法順序可 complete。

## Standards assessment

- same-UID raw mutation：實際可寫；只有可信 external anchor存在時可 `DETECTED`，否則 full replacement不會被偵測。
- append-only/hash chain：僅視為 tamper evidence，未認定 kernel immutability。
- POC production import：未發現 production import；只有 focused test import。
- dependency/retry：candidate未新增 framework dependency或 automatic retry。
- migration/rollback：方向存在，但安全接口與 caller cutover 尚未收斂到可直接實作。
- PID reuse：fresh probe以相同 fixture PID、不同 operation binding均可獨立 replay；目前 replay不以 PID 作 identity。這點沒有形成 blocking finding，但 production schema仍應明文鎖定。

## Final decision

`NO_GO`。不得開始 production implementation、merge、push、deploy、publish或 content recovery。本 review 只新增 reviewer evidence，未修改 candidate、POC、tests、docs、spike evidence或任何 V1–V3 檔案。
