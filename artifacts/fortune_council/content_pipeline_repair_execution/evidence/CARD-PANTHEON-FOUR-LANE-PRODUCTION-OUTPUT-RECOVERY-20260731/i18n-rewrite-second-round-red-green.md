# EV-I18N-REWRITE-SECOND-ROUND-RED-GREEN-001

## Scope

```text
lane: i18n-rewrite
run_id: auto-i18n-en-daf6984c146f81cb5738
source_article_id: ASTRO-LOVE-01
locale: en
provider_payload_disclosed: false
```

## RED

真實 production writer 與 semantic repair 都反覆輸出以中文為主、逐段翻譯或
模板式英文。deterministic 與 Reviewer gate 正確拒絕，沒有 candidate 被
Publisher 接受，也沒有用 reviewer bypass。

主要 findings：

```text
SOURCE_SYNTAX_TRANSFER
AI_TEMPLATE_STYLE
target-language mismatch
```

## Repair

模型 repair 額度用完後採人工英文編輯，但沒有變更事實或驗收契約：

- 保留 `ASTRO-LOVE-01` source SHA 與所有 facts／safety boundaries；
- 保留 locale plan 的 4 個精確 H2；
- 把來源 5×3 段落重組為自然英文 4×2 段落；
- candidate validator、plan alignment 與 deterministic gate 全部 PASS。

此處的人工編輯只取代不合格的 prose generation；最後核准仍由不同的 Gemini
Reviewer 與既有 deterministic gates 決定。

## GREEN

最終獨立 Reviewer：

```text
job_id: 5e9c56ac42e0e3290cdd45df2e242486eed0dce8
verdict: APPROVE
findings: []
approved_by_reviewer: 1
canonical_status: complete
```

Publisher dry-run 唯一命中本 run；create／rewrite 均 idle，未被拿來當完成。
正式 release：

```text
version: 0.3.189
commit: d9d1be2353bce1bc251e00f55d17523dcfeb18f9
tag: v0.3.189
status: PUBLISHED_TRANSLATION
pushed: true
public_article_count: 504
```

驗證：

- 3 個 web tests：PASS；
- 366 個 release tests：PASS；
- canonical probes、release-record gate：PASS；
- production asset 經 cache-busting/no-cache probe 為
  `200 application/javascript`，包含 run ID、`ASTRO-LOVE-01` 與標題
  `How to Read Relationship Horoscopes Without Letting Them Run Your Love Life`。

最後一個獨立 Reviewer 是第 40/40 次授權 Gemini 外呼；額度已封閉，不再呼叫。
