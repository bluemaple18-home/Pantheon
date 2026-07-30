# Independent review plan

## Root question

判定 ja／ko 每個 semantic item 的 bounded ASCII-only literal exception 是否確實
fail closed：一般英文、未知字、未明列 topology 與未消費字元不得取得 locale
authority；同時保留自然 ja／ko、日文純漢字、局部 proper noun／acronym／model
code／number、en 行為與既有 continuation invariants。

## Review sequence

1. 固定 candidate lineage、changed-file allowlist、Implementation card/evidence
   integrity 與既有 Review probes immutability。
2. 限域審查 `_ascii_is_name_acronym_or_number()`、
   `_plan_matches_target_language()`、每欄 semantic validation 與 direct tests。
3. 以 Review 專屬 probes 覆蓋 ja／ko × 五類 semantic item、大小寫、未知字、
   punctuation／separator／junk、長度／token bounds、未明列 topology、single
   Title Case／uppercase ordinary word、positive controls 與 en controls。
4. Fresh 執行 final targeted probe、direct suite、三組既有 Review probes、
   七檔 affected suite、production compile、debug scan 與 whitespace checks。
5. 將 Spec axis 與 Standards axis 分開判定；只有可重現 P0／P1 阻擋。

## Evidence boundary

只新增本 Review 卡、本目錄中的 probes 與 receipts。不得修改 candidate
production code、direct tests、Implementation artifacts 或既有 Review probes。
