# RESULT：Pantheon Service Activation Manifest Identity Topology RCA

- card：`CARD-PANTHEON-SERVICE-ACTIVATION-MANIFEST-IDENTITY-RCA-20260829`
- status：`RCA_RE_REVIEW_REQUESTED`
- verdict：`CROSS_VERSION_ACTIVATION_SCHEMA_GAP`
- accepted source：`779fb96434c15013d82833788a6795119730daad`
- production mutation：`0`

## 唯一主裁決

主因是 `CROSS_VERSION_ACTIVATION_SCHEMA_GAP`。

promotion／runtime manifest 自 `11e6c4c10566af1db0e182af49cf339d8019f7f6` 起，把 `target_identity` 當 caller-supplied、non-empty opaque string 寫入正式 manifest；capacity transition 在 `35cfdd52739f3e2896bf151ed6434a5e6d6ab95e` 引入較窄的 `gate2-actor:<sha>:activation-only` consumer check，`29f758f6ad74afa412dd8ff3878efdd79074b36f` 保留該 check並擴大stage validation。兩邊沒有共用 schema 或 lineage contract。`779fb` manifest 在 promotion／manifest schema、七 plist exact tuple、barrier digest contract都合法，卻在 capacity 的私有舊格式 validator fail closed。

secondary：

1. `INSTALLER_VALIDATOR_OVERREACH`：capacity 把 activation mode 編碼假設加到 opaque shared identity；其他六個 service／aggregate validator 都只要求同一 manifest tuple。
2. `ORCHESTRATION_ORDERING_GAP`：正式 transition order 是 coordinator＋四 lane → publisher exact-run → capacity → aggregate activation；原 acceptance 實際走 publisher → capacity，且對既有 stopped normal cohort 應使用 recovery-stage seam。這會造成下一個 stage/topology blocker，但不是目前 exact RED 的唯一主因；依正式順序重播仍在 identity check 先 RED。
3. `PROMOTION_MANIFEST_CONTRACT_GAP` 是 contributing producer-side gap：promotion 未限制或分類 identity；但 publisher producer bug仍為偽，且 promotion 本身依現行 manifest schema正確保存 caller input。

## 七服務 DAG 與 authority

1. promotion 讀 authorization 的 `target_identity`、source SHA、現有 actor／manifest／stage、Rule24 receipt；寫 actor、`runtime-manifest.json`、readiness acknowledgements、activation barrier、transaction receipt。
2. coordinator installer `--install` 讀 manifest、model route、coordinator/lane templates；一次寫 coordinator、new、rewrite、i18n-new、i18n-rewrite 五個 staged plist，以及 manifest/generation/model-route stage authority。
3. publisher installer `--install` 讀 manifest、publisher template、queue/runs；寫 publisher staged plist、manifest/generation、`publisher-max-runs`、`publisher-exact-run-id`。
4. capacity installer `--install|--install-recovery-stage` 讀 manifest、Rule24 stdout、top-level stage authority、barrier、舊 live 七 plist/services；只有 transition PASS 才寫第七個 staged plist。若 top-level authority尚不存在，它會跳過 transition validator，因此順序敏感。
5. coordinator `--activate|--activate-only` 是唯一七服務 aggregate activator：先驗七 staged plist，再 snapshot 舊 live tuple／barrier，replace 七 plist、bootout/bootstrap 七 labels、aggregate validate、activate barrier；任何失敗走七服務共同 rollback。

逐服務 mapping、read/write authority 與 line receipt 在 `control-plane-topology.json`。四條 lane 沒有各自 installer，均由 coordinator 同一 loop產生，所以不是四個獨立順序邊界。

## Identity owner 與形成

- committed manifest bytes 的 writer：promotion `_target_manifest()` → `runtime_manifest.build_manifest()`／transaction apply。
- identity 值的 semantic owner：promotion caller／authorization `--target-identity`；source只驗 non-empty、無空白，未生成 operation suffix。
- `...:new-lane-current-acceptance-20260829` 由 acceptance promotion input明示傳入，不是 publisher或 manifest builder生成。
- `...:activation-only` 的格式 owner：capacity guard 的 `ACTIVATION_ONLY_IDENTITY_PATTERN`；pattern於 `5b0c662f466a6bf32c39fccb9c4d66e88f355377` 引入，transition identity check由 `35cfdd52739f3e2896bf151ed6434a5e6d6ab95e` 引入。`29f758f6` 的 exact parent diff證明它沒有新增該限制：parent已存在；它移除額外 config-version conjunct、保留 suffix check並加入完整 target-stage validation。
- 實際七 plist writer並不生成 identity；三個 installer都從同一 manifest複製同一值。activation mode另由 plist `--activation-only` argument表示。

## Last-good／first-bad

last-good（production evidence closed）：

- actor `6477ab815e8aecca7d1e8e1588e6e5eba0fab001`
- generation `g47-6477ab81-activation-only-20260826`
- identity `gate2-actor:6477ab815e8aecca7d1e8e1588e6e5eba0fab001:activation-only`
- manifest digest `c2cd3cc7b63d7685f355a4426854b7f3d2c88b4e26b8e51468afdc7c49eadc53`
- promotion receipt `COMMITTED`；目前保留的七個 live plist全為同一 tuple，mtime集中於 `2026-08-26T10:45:12+08:00`；`10:45:19` 即有 new run註冊，閉合 install/aggregate activation後 runtime執行證據。

first-bad 分兩層：

- source incompatible mechanism：`11e6c4c` 已允許 opaque target identity；`35cfdd52` 後來在 capacity transition要求 activation-only suffix，`29f758f6` 繼承並保留。`11e6c4c` parent→commit證明 promotion module／CLI由不存在變成 caller identity直接寫入manifest；`29f758f6` parent→commit則推翻「29f首次引入identity限制」，並證明該窄consumer在stage hardening後仍位於所有barrier/stage/live checks之前。
- first located bad COMMITTED production manifest：actor `8a50395f67d22343fec4b0a8a5f41c8f40ac360e`、transaction `pantheon-gen05-release-8a-20260828`、identity `gate2-actor:8a50395f67d22343fec4b0a8a5f41c8f40ac360e:gen05-dangling-registry-guard-release-20260828`。其格式已不可能通過 capacity regex；`779fb` 延續同一 operation-specific identity機制並首次在本 acceptance正式重現 installer failure。

精確 commit metadata、receipt/hash與七 plist census見 `history-and-live-census.json`。

## Durable invariant

### Post-review design correction

detached parent同選集 baseline發現 shared actor-prefix parser新增36個真回歸後，durable invariant修正如下；RCA主因 `CROSS_VERSION_ACTIVATION_SCHEMA_GAP` 不變：

- 每個 activation cohort仍只有 committed manifest的一個 identity；七 staged/live plist、barrier、readiness ack必須 exact match同一 manifest identity/digest/generation tuple。
- identity本身只需符合既有 `build_manifest` contract：nonempty、trimmed opaque correlation；不要求內嵌 actor SHA。
- actor authority由 separate `actor_head`擁有；`manifest_digest`綁完整payload，`runtime_identity_digest`分別綁identity與存在時的actor_head，`load_manifest`另驗actor root/head。
- `normal`／`activation-only` mode由既有 explicit argument與plist/stage topology擁有，不得從 opaque identity suffix推導。
- accepted parent有6個正式producer、14個load consumers；5份committed manifests共7,556 bytes含兩種identity shapes。除capacity外，從identity推導actor或mode的consumer皆為0。

## Exact RED

`production-shaped-red-harness.py` 使用 `779fb` exact identity/generation與正式三支 installer，所有寫入限定 task-owned temporary HOME/root。Rule24輸入是既有 authoritative PASS receipt 的 byte-exact stdout replay，SHA-256 `ec6faea1d8d1d334b9d0eb092eecf6c509d108d78b4339e388d75309c57465cb`；無欄位投影、手填或猜值。Reviewer repair後capacity exact action為 stopped cohort正式 seam `--install-recovery-stage`。

- 正式順序 coordinator `--install` → publisher `--install` → capacity `--install-recovery-stage`：前六個 staged plist完成；capacity在 `validate_preactivation_transition:ACTIVATION_ONLY_IDENTITY_PATTERN` 回 `preactivation manifest mismatch`。
- 原 acceptance順序 publisher `--install` → capacity `--install-recovery-stage`：一個 staged plist後，同一 exact edge RED。
- diagnostic capacity-first recovery-stage：因stage authority尚不存在而跳過transition，最後可形成七 staged plist；這證明只有capacity installer順序敏感，也證明不能以錯序繞 validator作修復。
- double run：兩份 output byte-identical，SHA-256皆為 `f80fa92d0d22aa0445174153192cd161af7d5e294bfecc35927ee72249c13dcc`。
- production control-plane before/after：manifest、promotion receipt、136 registry files、publisher ledger、private stage與七 live plist bytes/hashes完全相同。
- calls：activation `0`、provider `0`、reviewer `0`、publisher execute `0`。

## Bounded Repair frontier

### Post-review corrected frontier

原「shared parser至少鎖actor prefix與actor_head」frontier判定為 `OVERREACH`，應撤回。最小Repair一次只改既有capacity seam：

1. runtime manifest保留既有 nonempty/trimmed opaque identity、digest與separate actor_head/root驗證，不新增identity parser或schema。
2. capacity停止以 `ACTIVATION_ONLY_IDENTITY_PATTERN`拒絕transition，也停止在live plist不可讀時以identity suffix猜mode。
3. 保留capacity既有manifest digest、barrier、stage/live exact tuple、Rule24、recovery mode與fail-closed checks。
4. production-shaped regression證明正式 coordinator→publisher→capacity recovery順序轉GREEN，actor_head/digest、stage、barrier、live tuple與mode drift仍RED。

`why_not_less`：只把 `g8-live` 加白名單仍保留capacity對shared identity的錯誤語義所有權，且無法涵蓋 `g8-staged`、`parent/tree`與後續合法opaque correlations。

`why_not_more`：actor_head、兩層digest、barrier、stage/live tuple與explicit mode topology已有正式owner；不需改runtime manifest producer、publisher/coordinator、queue、registry、ledger或promotion FSM。

`do_not_absorb`：逐installer if/else、generic identity field union、per-service identity、new registry/FSM/DB/authority ledger、manifest/stage migration、live rewrite、validator bypass、automatic activation、provider/reviewer/publisher retry。

## Verification 與 anti-expansion

- existing targeted tests：`3 passed`
- harness／collector `py_compile`：PASS
- harness double-run：byte-identical
- JSON parse：PASS
- `git diff --check`：PASS
- source/test changes：`0`
- production/live/service/git mutations：`0`
- install/activate/scheduler/provider/reviewer/publisher/commit/push/tag/deploy：`0`

本卡沒有實作 Repair；下一步只能另開 bounded Repair並回同一 RED驗證。

## Reviewer P1 closure

1. `P1-recovery-stage-replay`：`CLOSED`。harness已改走 exact coordinator `--install` → publisher `--install` → capacity `--install-recovery-stage`；雙跑仍為相同 identity edge RED、byte-identical、production bytes unchanged。主裁決與ordering說明不需翻轉。
2. `P1-parent-commit-causality`：`CLOSED_WITH_TIMELINE_CORRECTION`。已保存 `11e6c4c`、`29f758f6` 各自 exact parent→commit scoped diff、before/after snippets與blame。證據保留 cross-version主裁決，但更正 hard check introduction為 `35cfdd52`；`29f758f6` 是保留該check並hardening stage contract，不是首次引入者。

狀態：`RCA_RE_REVIEW_REQUESTED`。
