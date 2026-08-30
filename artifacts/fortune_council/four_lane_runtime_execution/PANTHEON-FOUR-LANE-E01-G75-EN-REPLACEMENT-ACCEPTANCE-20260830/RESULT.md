# E01 g75 EN replacement production acceptance

## 終局裁決

`TERMINAL_REVIEWER_REJECT_STOPPED_NO_PUBLISH`

E01 promotion 與 exact replacement lifecycle 均依正式 g75 authority 執行；最後
Generation 03 Reviewer 判定 `REJECT`，finding 為 `SOURCE_SYNTAX_TRANSFER`。依 Owner
明示 stop condition，未執行 publisher、release commit、tag、push 或公開網址驗收。

## Promotion authority

- actor：`e01d56e3847600fa8723a006b3f16e3757af7610`
- generation：`g75-e01d56e3-legacy-replacement-brief-20260830`
- manifest digest：`43e3b4c92318fcea47beb73b34c8635593f3ac5336f33c787095864419e628f1`
- promotion plan digest：`1ef6927c6be09b1db42a65ec5038c14dff6657357c4ce0965d00b9b395653a2b`
- queue snapshot digest：`ab13fb3c0483b05d08a7af7b2f9ae7ad92c76582c137698223207bf85e9d87fa`
- transaction：`COMMITTED`
- status：`PASS`
- fresh Rule24：`PASS`，2 cycles，stop-loss `STOPPED`
- fresh Rule25：`READY`
- preserved registry count：136

## Exact replacement

- source run：`auto-i18n-en-aa637e1bf05d3ad21429`
- source registry digest：`7b98f9c9eb11f32bce7768046dcd48a51c4ca4c4edd9f28dfae8b8bbf736cff8`
- replacement run：`auto-i18n-en-aa637e1bf05d3ad21429-replacement-01`
- replacement reason：`LOCALE_PLAN_VALIDATION`
- replacement registry digest：`25e08420193a9640ad00cbcdf1107590a23d2e22c9d73e9ddcc4235ccf8deeef`
- replacement brief SHA-256：`a8410b89d96d7a86af9ccea22d1cb2d817619707d10436461c9b80229f0b191f`
- replacement brief fields：`articles, mode, run_id, schema_version`
- second plan-only：`expected_write_set=[]`
- source terminal preserved：true
- attempts：`01, 02, 03`
- Generation 04：不存在

Registry 最終顯示 `status=complete` 只代表 lifecycle 結束；其
`result.approved_by_reviewer=0`，因此不可發布。

## Gemini call ledger

| # | Generation | Role | Job ID | Model | Result |
|---:|---:|---|---|---|---|
| 1 | 01 | Plan Writer | `84b3b03b12507d6e07e72894687353a6693aa47a` | `gemini-3.5-flash-lite` | processed |
| 2 | 01 | Article Writer | `65cfa63131a6f1cb97b76d54a43916e303727de6` | `gemini-3.5-flash-lite` | processed |
| 3 | 01 | Reviewer | `e052a7367850199639866d611835c5c544b53262` | `gemini-3.1-flash-lite` | REJECT |
| 4 | 02 | Repair Plan Writer | `e9d45e48c5bd3a47e07b33ccbd2809c15a207bb3` | `gemini-3.5-flash-lite` | processed |
| 5 | 02 | Article Writer | `26efd6d4f0616465a7cb8926442695458a657974` | `gemini-3.5-flash-lite` | processed |
| 6 | 02 | Reviewer | `a71ae0761dc37d91910af2e08c6c5ac5f06ba318` | `gemini-3.1-flash-lite` | REJECT |
| 7 | 03 | Repair Plan Writer | `4f38ad7a58465f1192f9533d55f75d09a69d6b1e` | `gemini-3.5-flash-lite` | processed |
| 8 | 03 | Article Writer | `45a4addcbf84177fdf33f70b8eb0e84e228ad7f0` | `gemini-3.5-flash-lite` | processed |
| 9 | 03 | Reviewer | `97678eafb23595f3f8dcff696b3d2e254e0cd2e0` | `gemini-3.1-flash-lite` | REJECT |

Reviewer findings：

- Gen01：`MIRRORED_STRUCTURE`, `AI_TEMPLATE_STYLE`
- Gen02：`MIRRORED_STRUCTURE`, `NON_NATIVE_SEARCH_INTENT`
- Gen03：`SOURCE_SYNTAX_TRANSFER`

## 唯讀 failure classification

唯一裁決：

`SINGLE_ARTICLE_PERSISTENT_LOCALIZATION_QUALITY_FAILURE / AUTOMATION_ACCEPTANCE_NO_GO`

三代 candidate 並非相同 bytes，也不是固定沿用同一份 H2 topology：

- source 有 5 個 H2；三代 candidate 各有 4 個 H2。
- Gen01 順序為定義 → 安全感 → 邊界 → 實作策略。
- Gen02 改為邊界 → 日常觀察 → 實作策略 → 定義。
- Gen03 再改為日常觸發 → 核心概念 → 邊界 → 實作策略。
- title、description、answer 與各代正文 digest 均不同。

因此不能把這次證據定性成 deterministic topology replay，也不能僅憑一篇文章外推成
automation-wide code defect。不過三代 Reviewer finding 持續落在同一品質族群：英文仍受
中文 source 的組織與句法牽引；最後一代即使換序，仍以 `SOURCE_SYNTAX_TRANSFER`
終局拒絕。這是單篇內容的 persistent localization failure，足以令本次 automation
production acceptance `NO_GO`，但不足以授權新的 pipeline RCA／Repair。

合法 next boundary 是一張 bounded manual content repair：只修改本篇 Gen03 EN
candidate 的英語組織與句法，保留 source facts、claim boundaries、article identity 與 locale；
回原 Reviewer 做獨立審查。不得建立 Gen04、不得再呼叫 automated Writer、不得放寬
Reviewer，也不得在 Reviewer APPROVE 前進 publisher。

## Terminal seal

- 四 lane outbox／processing：全部 0
- KO registry：`active`，digest `c535a650bfbafd2a2302ae78c04a3132ce50cb1bd7c41475f975917e0b16df32`
- JA registry：`active`，digest `43d2f9dc474adb7060c91fe85f076b935de872db65e5d39a91f1b14577f4f4c1`
- ledger digest：`4fa27434bfbff2a5344671278697bff6b94521d979083bf1227aff779e453f37`
- services loaded：0
- publisher calls：0
- release commit／tag／push：0
- public URL mutation：0
- actor worktree：clean

這次 acceptance 完成的是 promotion 與 bounded replacement lifecycle；內容未取得 Reviewer
APPROVE，因此正式發文未完成。
