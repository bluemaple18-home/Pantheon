---
id: CARD-PANTHEON-I18N-REWRITE-4OF4-LOCALE-AUTHORITY-SUCCESSOR-REPAIR-1-20260730-red-green
status: complete
type: repair-evidence
---

# Red → green

## LAS-REV-001

- Review group RED：`44 failed, 128 deselected`。
- Direct regression RED：`4 failed, 141 deselected`。
- Root cause：`re.findall()` 只抽出形狀可接受的 token，未證明原值全部被 grammar 消費。
- Minimal fix：以 anchored `re.fullmatch()` 驗證完整 token sequence，只允許明確 token grammar與單一 ASCII space separator。
- Review group GREEN：`44 passed, 128 deselected`。
- Direct regression GREEN：`4 passed, 141 deselected`。

## LAS-REV-002

- Review group RED：`30 failed, 142 deselected`。
- Direct regression RED：`3 failed, 145 deselected`。
- Root cause：Title Case name與 2–6 字元 UPPERCASE acronym 只靠 capitalization shape 取得 authority。
- Minimal fix：刪除 shape authority，standalone alphabetic token 只接受明列 `OpenAI`、`API`；model code與 number 繼續使用封閉 grammar。
- Review group GREEN：`30 passed, 142 deselected`。
- Direct regression GREEN：`3 passed, 145 deselected`。

## Closed-invariant follow-up

R1 的 whole-value grammar 讓混合日文 `OpenAIを使う` 不再由整段 helper 抵銷 Latin 字母。依既有 positive control，改為只在 mixed-language authority 計算中扣除逐 token 驗證通過的封閉 literal；純 ASCII semantic item 最終仍必須通過 whole-value helper。

- Targeted findings與 positive controls：`95 passed, 77 deselected`。
- Direct literal／native controls：`25 passed, 123 deselected`。
