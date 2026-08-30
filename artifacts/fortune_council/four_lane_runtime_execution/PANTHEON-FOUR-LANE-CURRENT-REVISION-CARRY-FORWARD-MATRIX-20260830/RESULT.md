# RESULT：四線 current-revision change-impact carry-forward matrix

status: `COMPLETE_READ_ONLY`
overall_verdict: `CARRY_FORWARD_THREE_LANES_FULL_E2E_I18N_REWRITE_ONLY`
production_actor_observed: `d7b09a99bd006544dd703a49f4ce774d32554c66 / g74-d7b09a99-exact-replacement-repair-20260830`
remote_main_observed: `e01d56e3847600fa8723a006b3f16e3757af7610`
operation: `READ_ONLY`

## 單一裁決

`new`、`rewrite`、`i18n-new` 的既有 production publication acceptance 可以正式 carry forward；三線都不需要重做 semantic/provider/Reviewer/Publisher/full E2E。三線在 E01 成為 live actor 後，只剩一組共用 control-plane gate，以及 current-actor 的 bounded `route → lane queue → exact selector/claim` smoke 與既有 public URL/canonical/body recheck。

只有 `i18n-rewrite` 仍是 `MISSING_PRODUCTION_E2E`，且必須沿 E01 的 failed-run exact replacement seam 建立 replacement 後完成一條 fresh `Writer → Reviewer → Publisher → release/tag/push → public URL HTTP 200/body`。不得用其他三線文章存在、Rule25 `READY`、replacement plan-only 或 route smoke補成此 lane 的 E2E。

目前 live production 尚是 D7/g74；E01 promotion plan 雖為 `READY_TO_APPLY`，但 apply 因缺明確 production promotion 授權而未執行。remote `origin/main` 已是 E01，因此**不用先 push**；下一個 shared frontier 是取得既有正式 E01 promotion/activation boundary 的授權與完成 identity gates，不是建立新架構，也不是先重跑四線。

## Change-impact closure

CodeGraph 先查結果：`replace_failed_translation_run_exact` 的影響只回到 coordinator exact replacement 與既有 `enqueue_translation_replacement`；沒有形成 `new`、`rewrite`、Publisher 或 public asset call edge。CodeGraph 對整段 commit 的 context 回傳雜訊後，才以限域 `git diff`／`rg` 閉合。

Commit chain：

- `f456a4d8c21ce0a237254d31e6662339a1d522fb`：只在 `scripts/agy_multilingual_pipeline.py` 增加 registered legacy translation brief normalizer。標準 strict brief 仍走原 `validate_translation_brief`；只有多出且可信 registry/state 明載 `lane=i18n-rewrite` 的舊 flat brief會被去除 legacy `lane` 後繼續。
- `d7b09a99bd006544dd703a49f4ce774d32554c66`：只在 `scripts/agy_gemini_coordinator.py` 增加 terminal failed translation run 的 exact `plan-only/execute` replacement seam；execute 最多呼叫既有 `enqueue_translation_replacement`，不執行 runner/provider/Publisher。
- `e01d56e3847600fa8723a006b3f16e3757af7610`：只把上述 exact seam 的 brief load 改成同一個可信 legacy normalizer，使 D7 plan-only 對 exact EN legacy brief的 strict-field拒絕收斂。

整段 `f456^..e01` 唯一 source files 是：

- `scripts/agy_multilingual_pipeline.py`
- `scripts/agy_gemini_coordinator.py`

對應 tests 只有 `tests/test_agy_multilingual_pipeline.py`、`tests/test_agy_gemini_coordinator.py`。D7→E01 本身更窄：source 只改 coordinator。沒有改 Writer/Reviewer schema、new/rewrite candidate formation、Publisher、ledger、release/tag/push、public assets、article/locale registry資料或路由程式。

結構上 F456 將 `_load_registered_translation_brief` 接到 translation 的 planning/reviewer-repair/staging/apply functions；但標準 `i18n-new` brief keys 精確等於 strict schema時，normalizer只 validate 並原樣回傳。真正新增的 runtime branch只接受可信 legacy `i18n-rewrite`，因此本次 semantic impact 是 failed `i18n-rewrite` replacement/lifecycle，不是四線共同語意變更。

## 四線 carry-forward matrix

| lane | last accepted actor / release | exact run / job | Reviewer | publish / release / remote | public evidence | 本 diff impact | current-revision requirement |
|---|---|---|---|---|---|---|---|
| `new` | actor `6477ab815e8aecca7d1e8e1588e6e5eba0fab001`; commit `0257bd5213eed0d0df10661a54f6215901a54997`; `v0.3.371` | run `v0391-publish-canary-20260826-02`; article `V2-TAROT-DEATH-MONEY`; separate Writer/Reviewer job IDs were not preserved in the located synchronous run receipt | `APPROVE`, findings `0`; candidate SHA `f39815d56b2c43b440f62663d5e1f7804bde17a4987d8da88e05af354dcb0cfd` | `published_runs` exactly one; remote annotated tag `v0.3.371^{}` → `0257bd...`; commit is contained by current remote main | `https://www.mysticpantheon.com/articles/tarot/tarot-1884`; recorded HTTP `200`, exact canonical/body visible; body SHA `ef616d26...` | no changed function/file on new candidate/review/publish path | `CARRY_FORWARD_AFTER_CURRENT_ACTOR_SMOKE_AND_PUBLIC_RECHECK`; no fresh full E2E |
| `rewrite` | actor `e5c0743fe1e0c99a66f2c0e3355591f2a353a322`; commit `47d7b804f4dbda6491f48141535fc869000421aa`; `v0.3.372` | run `legacy-auto-sweep-v1-astrology-0002-astro-base-02`; article `ASTRO-BASE-02`; separate job IDs not preserved in located synchronous run receipt | clean `APPROVE`, findings `0`; candidate body SHA `8f242bfd...` | exact Publisher once: `PUBLISHED_REWRITE`; `rewrite_released_runs` exactly one; pushed=`true`; remote `v0.3.372^{}` → `47d7...` | `https://www.mysticpantheon.com/articles/astrology/astrology-0002`; HTTP/2 `200`; browser exact canonical; new body visible, 2342 chars | no changed function/file on monolingual rewrite candidate/review/publish path | `CARRY_FORWARD_AFTER_CURRENT_ACTOR_SMOKE_AND_PUBLIC_RECHECK`; no fresh full E2E |
| `i18n-new` | accepted actor `dfcb3c77f9404fc9ff0707cb944ad08f50a4abef`; release `22d7e21b7a3da4e8afffd58a76b2746bebad8b41`; `v0.3.374` | run `auto-i18n-ja-1414b75a404721e95e74`; article `V2-TAROT-DEATH-MONEY:ja`; formal Reviewer job `e6c4542483f0b1100a19a5fb7af8c0597600462f` | actual release gate是 approved-edit formal rereview：`APPROVE_READY_FOR_STAGING`, findings `0`; formal result SHA `8394f603...`; stage SHA `9544705d...`。Gen06 root review本身是 `REJECT`，不得冒充 approve | `PUBLISHED_TRANSLATION`; `translation_published_runs` exactly one; remote `v0.3.374^{}` → `22d7...`; release commit/tag/push closed | `https://www.mysticpantheon.com/ja/articles/tarot/tarot-1884`; HTTP `200`; rendered canonical/title/H1/body sentinel PASS; console warning/error `0` | F456 common loader is structurally touched, but strict current brief takes validate-and-return identity path; D7/E01 exact replacement branch is unreachable | publication evidence `DIRECT_CARRY_FORWARD`; after E01 activation only shared current-actor smoke/public recheck, no fresh full E2E |
| `i18n-rewrite` | no accepted production E2E on any current revision | source run `auto-i18n-en-aa637e1bf05d3ad21429`; original run terminal failed after Gen03 plan validation; E01 replacement does not yet exist because E01 is not promoted | prior Gen01/Gen02 reviews were `REJECT`; no approved terminal candidate/review | `translation_published_runs` match for this run/replacement=`0`; no release/tag/push | shared locale route control曾 PASS，但不是此 lane publication evidence | exact legacy normalizer + exact failed replacement seam are precisely the changed branch | `FRESH_FULL_E2E_REQUIRED`; cannot carry forward |

### 不把文章存在當 receipt

`new` 與 `rewrite` 的 carry-forward 不是由 public article existence 推導：兩者都有 immutable run candidate/review、唯一 ledger record、正式 Publisher transaction、release commit/tag/push與 HTTP/browser evidence。若只剩文章而缺其中任一鏈，本矩陣會標 `MISSING`。舊 receipt 未保存獨立 async job ID 的欄位則明確標為 `NOT_PRESERVED`，不虛構 job identity。

`i18n-new` 特別以 v0.3.374 的 formal rereview/stage/ledger/remote tag/browser rendered DOM閉合；root Gen06 `REJECT` 不是放行 verdict。

## Shared control-plane gates（只列一次）

以下是 E01 current actor的共用前置，不是每 lane 各重跑一次：

1. 取得明確 production promotion授權，沿既有 E01 plan/apply/finalize/status seam完成 actor/manifest/private-stage/barrier identity；不得先用別的入口改 production。
2. 在同一 actor/manifest/generation tuple完成既有七服務 preflight/install/aggregate activation與 rollback postcheck；Rule24/Rule25、queue preservation、service selector/model route必須全部 fail-closed通過。
3. provider=`0` 的 bounded current-actor smoke：驗證 `new`、`rewrite`、`i18n-new` 的 route→正確 lane namespace→exact selector/claim；只驗控制面與既有 strict translation brief branch，不產生 semantic candidate、不發 Reviewer/Publisher。若正式 smoke會寫 production queue，先在隔離 fixture重現；本卡不授權該 mutation。
4. 唯讀 recheck三個 carry-forward URL的 HTTP `200`、exact canonical與既有 body sentinel/identity。任一 content identity漂移才把該 lane降級成 fresh E2E；不是預設全部重跑。
5. 前四項通過後，才進唯一 production mutation frontier：E01 exact EN replacement，再逐步完成 `i18n-rewrite` fresh full E2E。

## 修正版最小 remaining gates

唯一 frontier：`PROMOTE_AND_ACTIVATE_E01_THEN_RUN_ONE_SHARED_CARRY_FORWARD_SMOKE`。

若 shared gate PASS：三條已接受 lane維持 carry-forward，production semantic/provider/Reviewer/Publisher mutation budget皆為 `0`；只把 `i18n-rewrite` 排入 fresh full E2E，並沿 exactly-one replacement/run/selector、bounded Writer/Reviewer repair budget、exactly-one Publisher transaction與 public rendered acceptance執行。

Stop conditions：

- E01 promotion未獲授權、actor/manifest/generation或 installed plist identity不一致即停。
- queue snapshot、route/lane/model selector、exact claim不是唯一或需要手改 registry/state即停。
- 任何 carry-forward URL的 canonical/body identity與其 ledger release不一致，只降級該一 lane，不擴成四線全重跑。
- EN replacement不是 pristine、lineage/digest/source/semantic budget不一致、需要第二個 replacement或 provider重送超出既有 budget即停。
- Reviewer未正式 approve、Publisher selector非 exactly one、release/tag/push或 rendered public正文任一缺失，即 `i18n-rewrite` 仍為 `MISSING_PRODUCTION_E2E`。

## Push decision

`NO_PUSH_REQUIRED_BEFORE_FRONTIER`。本次唯讀 remote refs確認：

- `origin/main` → `e01d56e3847600fa8723a006b3f16e3757af7610`
- `v0.3.371^{}` → `0257bd5213eed0d0df10661a54f6215901a54997`
- `v0.3.372^{}` → `47d7b804f4dbda6491f48141535fc869000421aa`
- `v0.3.374^{}` → `22d7e21b7a3da4e8afffd58a76b2746bebad8b41`

push identity已存在不等於 E01 production actor已切換；目前 live manifest仍是 D7/g74。Promotion、activation、production/provider/Publisher仍需各自既有 authority boundary。

## Evidence index

- previous four-lane matrix：`../pantheon_four_lane_current_acceptance_matrix_20260829/RESULT.md`
- independent modality review：`../pantheon_four_lane_current_acceptance_matrix_modality_review_20260829/RESULT.md`
- `new` last-success/current readiness RCA：`../pantheon_new_lane_current_readiness_rca_20260829/RESULT.md`
- `rewrite` Acceptance A：`../CARD-PANTHEON-AUTOMATION-ACCEPTANCE-A-LEGACY-REWRITE-20260826-RESULT.md`
- `i18n-new` Gen06 final：`../pantheon_acceptance_b_gen06_final_publish_acceptance_20260829/RESULT.md`
- D7 exact replacement acceptance：`../PANTHEON-FOUR-LANE-D7B-EN-REPLACEMENT-ACCEPTANCE-20260830/RESULT.md`
- E01 promotion acceptance：`../PANTHEON-FOUR-LANE-E01-G75-EN-REPLACEMENT-ACCEPTANCE-20260830/RESULT.md`
- production ledger：`<production-root>/state/ledger.json`（本次唯讀確認 EN source/replacement published match=`0`）
- production manifest：`<production-root>/runtime-manifest.json`（本次唯讀確認 actor D7/g74）

## Not claimed

- 未宣稱四線全通；`i18n-rewrite` 仍缺完整 E2E。
- 未執行 provider、Reviewer、coordinator、Publisher、promotion、activation、commit、push、tag或 deploy。
- 未修改 production queue/state/runtime、source、tests或舊 acceptance artifact。
- 未把 Rule25 capability或 public article存在當作 lane E2E。
