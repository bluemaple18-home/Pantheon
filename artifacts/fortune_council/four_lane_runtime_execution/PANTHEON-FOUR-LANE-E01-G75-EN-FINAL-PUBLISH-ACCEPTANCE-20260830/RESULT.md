# E01 g75 EN final publish acceptance

## 裁決

`NO_GO_EXISTING_STAGING_SEAM_NOT_APPLICABLE_TO_REPLACEMENT_ATTEMPT_LIFECYCLE`

已核准的 manual repaired candidate 與 formal Reviewer identity 均通過唯讀核對，但現有
正式 `stage-approved-edited-candidate` seam 不能接受本次 exact replacement run 的
`attempts` lifecycle。為避免偽造 continuation／generation authority，staging、publisher、
release、tag、push 均未執行。

## Authority 與 fresh gates

- actor：`e01d56e3847600fa8723a006b3f16e3757af7610`
- generation：`g75-e01d56e3-legacy-replacement-brief-20260830`
- manifest digest：`43e3b4c92318fcea47beb73b34c8635593f3ac5336f33c787095864419e628f1`
- fresh Rule24：`PASS`，2 cycles，stop-loss `STOPPED`
- fresh Rule25：`READY`

## Candidate／Reviewer seal

- run：`auto-i18n-en-aa637e1bf05d3ad21429-replacement-01`
- candidate file SHA-256：`26dd6ccf15a37a165f2ec11f9dd0220db26b9cdbc7fc8b2641b50b551e6731d1`
- approved article SHA-256：`7a63cb36b0dae48df870647653846b9d3e20da97f1725f232d9139c70d378314`
- formal review job：`af0a7de946841d3e899f7b7aeb8c3993762775d3`
- model：`gemini-3.1-flash-lite`
- verdict：`APPROVE`
- findings：`[]`
- approved review SHA-256：`abae910fac8dbffd353d698fff25ae78ef08d2b3eab7f62b5324630dc326b1a5`
- formal review result SHA-256：`1446c10ad80a8e942c553419bf5aa957ded3dbdd2d6bad646fa05047a6d21e2c`
- approved review 等於 `formal-review-result.review`：true

## Exact staging contract blocker

現有正式 seam 的必要輸入／invariant：

1. `<run>/continuation/state.json` 存在，`status=complete`，且
   `next_generation=terminal_generation+1`。
2. `<run>/generations/<terminal>/candidate.json` 與 `review.json` 存在，並與 root audit
   digest 相同。
3. root terminal review 每項必須 `verdict=REJECT`、`hard_failure=true` 且 findings 非空。

本次 replacement 的實際 durable shape：

- `attempts/01..03`：存在。
- `attempts/03/candidate.json` SHA-256：
  `b9799d335a5ec8ec22a32e063174681a9d8e050a65a2a6015b6f39eb54fc1547`。
- `attempts/03/review.json` SHA-256：
  `43ee5f34e50a652fc70da7129cd22ca16a8341adc4b740b1b103d36c0aa47ae3`。
- `continuation/state.json`：不存在。
- `generations/03`：不存在。
- root review：普通 `REJECT`，finding `SOURCE_SYNTAX_TRANSFER`，沒有
  `hard_failure=true`。
- replacement registry digest：
  `25e08420193a9640ad00cbcdf1107590a23d2e22c9d73e9ddcc4235ccf8deeef`。
- publisher ledger digest：
  `4fa27434bfbff2a5344671278697bff6b94521d979083bf1227aff779e453f37`。

因此沒有合法的 `expected-continuation-state-sha256` 或 terminal generation audit locks；
用空值、假 digest、複製 attempts 到 generations 或手建 continuation 都是在偽造 lifecycle
authority。Preflight 在形成正式 plan 前即為 `NO_GO`。

## Mutation seal

- staging plan：未形成
- staging execute：0
- approved revision seal：未建立
- publisher preflight／dry-run／execute：0
- release commit／tag／push：0
- public URL mutation：0
- KO／JA／其他 lane mutation：0
- provider call：0
- production content mutation：0

本卡不開 RCA／Repair，也不創建新的 staging seam。合法 next boundary 必須由主線另行裁決；
在 replacement-attempt lifecycle 有正式、可測、receipt-first 的 staging contract 前，不能
發布這份 candidate。
