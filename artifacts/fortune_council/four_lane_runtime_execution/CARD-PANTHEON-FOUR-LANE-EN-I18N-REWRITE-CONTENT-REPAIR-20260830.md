# Pantheon 四線 EN i18n-rewrite Gen03 bounded content repair

## 任務目的

只針對 replacement run `auto-i18n-en-aa637e1bf05d3ad21429-replacement-01` 的 final Generation 03 candidate 做一次隔離、人工、內容層修訂，排除終局 Reviewer finding `SOURCE_SYNTAX_TRANSFER`，並保留前代 findings `MIRRORED_STRUCTURE`、`AI_TEMPLATE_STYLE`、`NON_NATIVE_SEARCH_INTENT` 的閉合。

## 權威輸入

- production `brief.json`：來源身分、fact package、claims、constraints、locale 與 metadata authority。
- production `attempts/03/candidate.json`：本次唯一可修候選。
- production `attempts/01..03/{locale-plan,review}.json`：outline 與 Reviewer history。
- production source bytes：唯讀，用於來源／事實／claim 比對。

## 唯一可寫範圍

- 本卡。
- `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-EN-I18N-REWRITE-CONTENT-REPAIR-20260830/`
  - 權威輸入的隔離副本與 checksum／inventory。
  - `candidate-repaired.json`。
  - deterministic validation receipts。
  - `RESULT.md`。

## 內容修訂契約

- 使用 native English information architecture；不得鏡射來源語言的句法、段落推進或逐項模板。
- 不得只改標題或同義替換；正文的資訊排序與段落功能必須形成自然英文讀者路徑。
- 不使用 AI template 套路、機械轉場、重複開場或無資訊結語。
- 保留全部 authoritative fact IDs、source refs、claims、constraints、metadata identity 與 English locale。
- 不新增、刪除或改寫風險／限制聲明的實質範圍。
- 不新增來源未支持的資訊、推論、承諾、數字或專有名詞。

## 禁止範圍

- 不修改 source code、tests、production run、registry、queue、manifest 或 runtime。
- 不呼叫 provider、外部 Reviewer 或 publisher。
- 不建立 Generation 04。
- 不 tag、不 push、不發布。
- 不把隔離候選直接寫回 production。

## 驗收

- identity、fact、claim、constraint、locale、metadata 均與權威輸入一致。
- topology／paragraph flow 不再鏡射來源句法，且不是標題換皮。
- duplicate、residue、SEO 與既有受影響 validators 通過。
- production protected bytes `before == after`。
- `git diff --check` 通過。
- `RESULT.md` 唯一狀態為 `READY_FOR_FORMAL_REVIEW` 或 `BLOCKED`。

