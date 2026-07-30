# Independent Review findings

## `LAS-REV-001` — P1 — ASCII tokenizer未驗證完整輸入

- severity：`P1`
- category：correctness／fail-closed validation
- path：`scripts/agy_multilingual_pipeline.py:586`
- trigger：`re.findall(...)` 只抽出符合 token regex 的片段，未確認 token spans 與
  允許的 separator 是否完整覆蓋原始 ASCII-only value。`@@OpenAI@@`、
  `OpenAI???`、`OpenAI/GPT-5/2026`、`OpenAI,GPT-5;2026` 的未消費字元會被
  忽略，剩餘 token 仍符合 name 或 product/model topology。
- reproducible evidence：
  `independent_review_probes.py` 的 full-consumption group 為
  `44 failed`。其中 40 個 failure 覆蓋 ja／ko ×
  `native_search_intent`、每一個 native query、`article_angle`、每一個 H2、
  每一個 coverage note；另四個 direct-helper probes 證明 tokenizer 本身接受
  未消費字元。
- risk：provider 前的 deterministic publication boundary 未對整個 semantic item
  負責。未明列 punctuation、separator 或 leading／trailing junk 可藉由合法 token
  子序列取得 locale authority，直接違反 bounded closed contract 與
  RV-SL-02 的 full-consumption要求。
- minimal repair direction：以 whole-value grammar 驗證（例如 anchored
  `fullmatch`），或明確檢查 token spans 與唯一允許的 separator 完整覆蓋經規範化
  後的輸入；任何未消費字元或未明列 separator 必須 fail closed。補 ja／ko ×
  五類 semantic item 的 punctuation／junk／separator direct tests。
- validation gap：未呼叫 provider、未測 production payload；finding 已在
  deterministic helper 與 hydration boundary 直接重現，不依賴外部 runtime。
- confidence：high

## `LAS-REV-002` — P1 — 單一 Title Case形狀仍可冒充實體authority

- severity：`P1`
- category：correctness／locale authority
- path：`scripts/agy_multilingual_pipeline.py:610`
- trigger：`is_single_name()` 只要求 2–24 個英文字母、首字大寫且含小寫字母。
  因此普通英文 `Strategy` 與未知一般字 `Zorple` 均被視為 name；短全大寫普通字
  `SOURCE` 亦由 acronym branch 接受。這些值作為完整 semantic item 時沒有任何
  目標語言 authority。
- reproducible evidence：
  `independent_review_probes.py` 的 single-word group 為
  `30 failed`，精確覆蓋 ja／ko × 五類 semantic item ×
  `Strategy`／`SOURCE`／`Zorple`。失敗型態皆為預期 locale rejection 未發生。
- risk：任何單一 Title Case普通英文或未知字都能跨過 ja／ko 的 provider 前
  deterministic gate；影響所有 publication semantic fields，而不是單一顯示邊界。
  這仍以 capitalization shape 推斷 entity，未達「可驗證 authority」的 root
  contract。Implementation evidence 將它列為 residual risk 不會縮小觸發範圍。
- minimal repair direction：完整 ASCII-only semantic item 不得只靠單一
  Title Case形狀取得 authority；移除 standalone generic name exception，將
  proper noun保留在含目標語言 authority 的內容中，或使用不會把任意普通字當
  實體的明確封閉契約。保留明確 model code／number 及契約要求的合法 positives。
- validation gap：未使用外部 entity registry，也未評估真實 provider文字分布；
  finding 已在五類 deterministic fields 直接重現。
- confidence：high

## Non-blocking observations

- Bounded multiword/general-English matrix、token count／length bounds 與未明列
  topology 共 70 個 probes 全數通過。
- ja／ko 自然內容、日文純漢字 `実践方法`、局部
  `OpenAI`／`API`／`GPT-5`／`2026`、closed ASCII positives 與 en controls
  共 28 個 probes 全數通過。
- 未另列 P2／P3 finding。
