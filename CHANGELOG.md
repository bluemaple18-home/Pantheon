# Pantheon Release Log

每次正式文章發布都必須同步更新 `pyproject.toml`、`package.json` 與本檔，並以同版本 annotated tag 指向 release commit。

## [Unreleased]

- Production-only pool 改用四條 content lane 共用的 owner-only durable strict round-robin state，固定依 account-1→account-2→account-3 循環分配，並以跨程序 lock 內 durable ordinal commit 作為線性化順序。
- Pool transport 在 provider request 前消耗 ordinal，每個 job 僅允許一次 request；crash、429、HTTP/timeout/transport/output failure 不回滾、不換 key、不 retry、不 fallback。
- Corrupt、truncated、symlink、wrong owner/mode、relative path、pool/manifest mismatch 與 TOCTOU state 會在 credential value/provider 前 fail closed。
- Inbox／failed receipt 仍精確只保存匿名 pool／slot／manifest digest；不保存 ordinal、state path 或 credential path/value。Flag-off CLI 與所有 V4 broker／target／shadow 行為維持不變。
- Launchd installer 僅在明確 opt-in 時，把 production pool manifest path 與同一個 absolute allocator state path 加入四條 content lane plist，且所有 preflight 早於 plist/control-plane write。

## [0.3.80] - 2026-07-25

- Release tag：`v0.3.80`
- 公開文章總數：454（新增多語版本，不新增繁中 registry 條目）
- 發布範圍：發布通過母語品質、Reviewer 與 deterministic gate 的多語文章 1 個 run；語系：ja；run_id：auto-i18n-ja-29fb7304e3395b9633b4。
- 驗證：publisher clean-origin gate、來源漂移 gate、多語 deterministic gate、focused multilingual pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/translation-0.3.80`

## [0.3.79] - 2026-07-25

- Release tag：`v0.3.79`
- 公開文章總數：454（新增多語版本，不新增繁中 registry 條目）
- 發布範圍：發布通過母語品質、Reviewer 與 deterministic gate 的多語文章 1 個 run；語系：ko；run_id：auto-i18n-ko-6096aa0317f61d38ae88。
- 驗證：publisher clean-origin gate、來源漂移 gate、多語 deterministic gate、focused multilingual pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/translation-0.3.79`

## [0.3.78] - 2026-07-25

- Release tag：`v0.3.78`
- 公開文章總數：454（新增多語版本，不新增繁中 registry 條目）
- 發布範圍：發布通過母語品質、Reviewer 與 deterministic gate 的多語文章 1 個 run；語系：ja；run_id：auto-i18n-ja-5bc3bbeee039e5859cb1。
- 驗證：publisher clean-origin gate、來源漂移 gate、多語 deterministic gate、focused multilingual pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/translation-0.3.78`

## [0.3.77] - 2026-07-25

- Release tag：`v0.3.77`
- 公開文章總數：454（新增多語版本，不新增繁中 registry 條目）
- 發布範圍：發布通過母語品質、Reviewer 與 deterministic gate 的多語文章 1 個 run；語系：ko；run_id：auto-i18n-ko-c0ae1759d9c4c2fa48d5。
- 驗證：publisher clean-origin gate、來源漂移 gate、多語 deterministic gate、focused multilingual pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/translation-0.3.77`

## [0.3.76] - 2026-07-25

- Release tag：`v0.3.76`
- 公開文章總數：454（新增多語版本，不新增繁中 registry 條目）
- 發布範圍：發布通過母語品質、Reviewer 與 deterministic gate 的多語文章 1 個 run；語系：ja；run_id：auto-i18n-ja-f5b40ddcb4390fd026c6。
- 驗證：publisher clean-origin gate、來源漂移 gate、多語 deterministic gate、focused multilingual pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/translation-0.3.76`

## [0.3.75] - 2026-07-25

- Release tag：`v0.3.75`
- 公開文章總數：454（新增多語版本，不新增繁中 registry 條目）
- 發布範圍：發布通過母語品質、Reviewer 與 deterministic gate 的多語文章 1 個 run；語系：ko；run_id：auto-i18n-ko-6f2eeaf2480ee914828b。
- 驗證：publisher clean-origin gate、來源漂移 gate、多語 deterministic gate、focused multilingual pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/translation-0.3.75`

## [0.3.74] - 2026-07-25

- Release tag：`v0.3.74`
- 公開文章總數：454
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：auto-new-v1-20260725-037-01。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/publish-0.3.74`

## [0.3.73] - 2026-07-25

- Release tag：`v0.3.73`
- 公開文章總數：451（新增多語版本，不新增繁中 registry 條目）
- 發布範圍：發布通過母語品質、Reviewer 與 deterministic gate 的多語文章 1 個 run；語系：en；run_id：auto-i18n-en-7bee7b80f36026debfc6。
- 驗證：publisher clean-origin gate、來源漂移 gate、多語 deterministic gate、focused multilingual pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/translation-0.3.73`

## [0.3.72] - 2026-07-25

- Release tag：`v0.3.72`
- 公開文章總數：451（新增多語版本，不新增繁中 registry 條目）
- 發布範圍：發布通過母語品質、Reviewer 與 deterministic gate 的多語文章 1 個 run；語系：en；run_id：auto-i18n-en-288018d46e93eb3dd6ee。
- 驗證：publisher clean-origin gate、來源漂移 gate、多語 deterministic gate、focused multilingual pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/translation-0.3.72`

## [0.3.71] - 2026-07-25

- Release tag：`v0.3.71`
- 公開文章總數：451（新增多語版本，不新增繁中 registry 條目）
- 發布範圍：發布通過母語品質、Reviewer 與 deterministic gate 的多語文章 1 個 run；語系：en；run_id：auto-i18n-en-e0c230d7788673214969。
- 驗證：publisher clean-origin gate、來源漂移 gate、多語 deterministic gate、focused multilingual pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/translation-0.3.71`

## [0.3.70] - 2026-07-25

- Release tag：`v0.3.70`
- 公開文章總數：451
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：auto-new-v1-20260725-032-02。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/publish-0.3.70`

## [0.3.69] - 2026-07-25

- Release tag：`v0.3.69`
- 公開文章總數：449（新增多語版本，不新增繁中 registry 條目）
- 發布範圍：發布通過母語品質、Reviewer 與 deterministic gate 的多語文章 2 個 run；語系：en, ja；run_id：auto-i18n-en-913c5a8add10757ddf55, auto-i18n-ja-53a44e2be10ed3e62d3a。
- 驗證：publisher clean-origin gate、來源漂移 gate、多語 deterministic gate、focused multilingual pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/translation-0.3.69`

## [0.3.68] - 2026-07-25

- Release tag：`v0.3.68`
- 公開文章總數：449（新增多語版本，不新增繁中 registry 條目）
- 發布範圍：發布通過母語品質、Reviewer 與 deterministic gate 的多語文章 1 個 run；語系：ko；run_id：auto-i18n-ko-07498b76b0e131817586。
- 驗證：publisher clean-origin gate、來源漂移 gate、多語 deterministic gate、focused multilingual pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/translation-0.3.68`

## [0.3.67] - 2026-07-25

- Release tag：`v0.3.67`
- 公開文章總數：449（新增多語版本，不新增繁中 registry 條目）
- 發布範圍：發布通過母語品質、Reviewer 與 deterministic gate 的多語文章 1 個 run；語系：en；run_id：auto-i18n-en-211334d6bc81bb6e2d8c。
- 驗證：publisher clean-origin gate、來源漂移 gate、多語 deterministic gate、focused multilingual pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/translation-0.3.67`

## [0.3.66] - 2026-07-25

- Release tag：`v0.3.66`
- 公開文章總數：449（新增多語版本，不新增繁中 registry 條目）
- 發布範圍：發布通過母語品質、Reviewer 與 deterministic gate 的多語文章 1 個 run；語系：ja；run_id：auto-i18n-ja-ff7ef583f7ec18b4285f。
- 驗證：publisher clean-origin gate、來源漂移 gate、多語 deterministic gate、focused multilingual pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/translation-0.3.66`

## [0.3.65] - 2026-07-25

- Release tag：`v0.3.65`
- 公開文章總數：449
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：auto-new-v1-20260725-019-01。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/publish-0.3.65`

## [0.3.64] - 2026-07-25

- Release tag：`v0.3.64`
- 公開文章總數：446
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：auto-new-v1-20260725-001-02。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/publish-0.3.64`

## [0.3.63] - 2026-07-25

- Release tag：`v0.3.63`
- 公開文章總數：444（新增多語版本，不新增繁中 registry 條目）
- 發布範圍：發布通過母語品質、Reviewer 與 deterministic gate 的多語文章 1 個 run；語系：ko；run_id：auto-i18n-ko-1077656b1308bbc4fd66。
- 驗證：publisher clean-origin gate、來源漂移 gate、多語 deterministic gate、focused multilingual pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/translation-0.3.63`

## [0.3.62] - 2026-07-25

- Release tag：`v0.3.62`
- 公開文章總數：444
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：auto-new-v1-20260724-018-02。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/publish-0.3.62`

## [0.3.61] - 2026-07-25

- Release tag：`v0.3.61`
- 公開文章總數：442（新增多語版本，不新增繁中 registry 條目）
- 發布範圍：發布通過母語品質、Reviewer 與 deterministic gate 的多語文章 1 個 run；語系：ja；run_id：auto-i18n-ja-19ef96cb36d803af4c5c。
- 驗證：publisher clean-origin gate、來源漂移 gate、多語 deterministic gate、focused multilingual pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/translation-0.3.61`

## [0.3.60] - 2026-07-25

- Release tag：`v0.3.60`
- 公開文章總數：442
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：auto-new-v1-20260724-019-02。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Projects/Pantheon-publish-actor/.work/content-publisher/evidence/publish-0.3.60`

## [0.3.59] - 2026-07-25

- Release tag：`v0.3.59`
- 公開文章總數：440（新增多語版本，不新增繁中 registry 條目）
- 發布範圍：發布通過母語品質、Reviewer 與 deterministic gate 的多語文章 1 個 run；語系：ko；run_id：auto-i18n-ko-4c30845dd81a6f69b994。
- 驗證：publisher clean-origin gate、來源漂移 gate、多語 deterministic gate、focused multilingual pipeline tests 與 release record gate。
- 證據：`/Users/mattkuo/Documents/Pantheon-publish-actor/.work/content-publisher/evidence/translation-0.3.59`

## [0.3.58] - 2026-07-24

- Release tag：`v0.3.58`
- 公開文章總數：440
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 2 個 run；run_id：auto-new-v1-20260724-015-02, auto-new-v1-20260724-015-01。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.58`

## [0.3.57] - 2026-07-24

- Release tag：`v0.3.57`
- 公開文章總數：435
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：auto-new-v1-20260724-014-01。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.57`

## [0.3.56] - 2026-07-24

- Release tag：`v0.3.56`
- 公開文章總數：432
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：auto-new-v1-20260724-008-02。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.56`

## [0.3.55] - 2026-07-24

- Release tag：`v0.3.55`
- 公開文章總數：430
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：auto-new-v1-20260724-007-02。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.55`

## [0.3.54] - 2026-07-24

- Release tag：`v0.3.54`
- 公開文章總數：428
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：auto-new-v1-20260724-006-01。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.54`

## [0.3.53] - 2026-07-24

- Release tag：`v0.3.53`
- 公開文章總數：425
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：auto-new-v1-20260724-005-02。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.53`

## [0.3.52] - 2026-07-24

- Release tag：`v0.3.52`
- 公開文章總數：423
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：auto-new-v1-20260724-002-01。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.52`

## [0.3.51] - 2026-07-24

- Release tag：`v0.3.51`
- 公開文章總數：420（舊文重寫，不新增 registry 條目）
- 發布範圍：套用 Gemini Reviewer APPROVE 且 deterministic gate 通過的舊文 body override 2 篇；run_id：legacy-user-fit-repair-20260723-02, legacy-user-fit-repair-20260723-13。
- 驗證：publisher clean-origin gate、Reviewer hash gate、rewrite deterministic gate、source body drift gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/rewrite-0.3.51`

## [0.3.50] - 2026-07-24

- Release tag：`v0.3.50`
- 公開文章總數：420
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-70。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.50`

## [0.3.49] - 2026-07-24

- Release tag：`v0.3.49`
- 公開文章總數：419
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-83。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.49`

## [0.3.48] - 2026-07-24

- Release tag：`v0.3.48`
- 公開文章總數：418
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-42。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.48`

## [0.3.47] - 2026-07-24

- Release tag：`v0.3.47`
- 公開文章總數：417
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-44。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.47`

## [0.3.46] - 2026-07-24

- Release tag：`v0.3.46`
- 公開文章總數：416
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-59。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.46`

## [0.3.45] - 2026-07-24

- Release tag：`v0.3.45`
- 公開文章總數：415
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 2 個 run；run_id：harness-new-20260723-94, harness-new-20260723-64。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.45`

## [0.3.44] - 2026-07-24

- Release tag：`v0.3.44`
- 公開文章總數：413
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 2 個 run；run_id：harness-new-20260723-67, harness-new-20260723-12。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.44`

## [0.3.43] - 2026-07-24

- Release tag：`v0.3.43`
- 公開文章總數：411
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-100。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.43`

## [0.3.42] - 2026-07-24

- Release tag：`v0.3.42`
- 公開文章總數：410
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-49。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.42`

## [0.3.41] - 2026-07-24

- Release tag：`v0.3.41`
- 公開文章總數：409
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-88。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.41`

## [0.3.40] - 2026-07-24

- Release tag：`v0.3.40`
- 公開文章總數：408
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-32。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.40`

## [0.3.39] - 2026-07-24

- Release tag：`v0.3.39`
- 公開文章總數：407
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 2 個 run；run_id：harness-new-20260723-16, harness-new-20260723-60。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.39`

## [0.3.38] - 2026-07-24

- Release tag：`v0.3.38`
- 公開文章總數：405
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-48。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.38`

## [0.3.37] - 2026-07-24

- Release tag：`v0.3.37`
- 公開文章總數：404
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-51。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.37`

## [0.3.36] - 2026-07-24

- Release tag：`v0.3.36`
- 公開文章總數：403
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-57。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.36`

## [0.3.35] - 2026-07-24

- Release tag：`v0.3.35`
- 公開文章總數：402
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-01。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.35`

## [0.3.34] - 2026-07-24

- Release tag：`v0.3.34`
- 公開文章總數：401
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 2 個 run；run_id：harness-new-20260723-52, harness-new-20260723-71。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.34`

## [0.3.33] - 2026-07-24

- Release tag：`v0.3.33`
- 公開文章總數：399
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-19。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.33`

## [0.3.32] - 2026-07-24

- Release tag：`v0.3.32`
- 公開文章總數：398
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-05。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.32`

## [0.3.31] - 2026-07-24

- Release tag：`v0.3.31`
- 公開文章總數：397
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-27。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.31`

## [0.3.30] - 2026-07-24

- Release tag：`v0.3.30`
- 公開文章總數：396
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-58。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.30`

## [0.3.29] - 2026-07-24

- Release tag：`v0.3.29`
- 公開文章總數：395
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-23。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.29`

## [0.3.28] - 2026-07-24

- Release tag：`v0.3.28`
- 公開文章總數：394
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-40。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.28`

## [0.3.27] - 2026-07-24

- Release tag：`v0.3.27`
- 公開文章總數：393（舊文重寫，不新增 registry 條目）
- 發布範圍：套用 Gemini Reviewer APPROVE 且 deterministic gate 通過的舊文 body override 12 篇；run_id：legacy-user-fit-repair-20260723-08, legacy-user-fit-repair-20260723-14, legacy-user-fit-repair-20260723-17, legacy-user-fit-repair-20260723-21, legacy-user-fit-repair-20260723-22, legacy-user-fit-repair-20260723-16, legacy-user-fit-repair-20260723-10, legacy-user-fit-repair-20260723-23, legacy-user-fit-repair-20260723-18, legacy-user-fit-repair-20260723-11, legacy-user-fit-repair-20260723-15, legacy-user-fit-repair-20260723-25。
- 驗證：publisher clean-origin gate、Reviewer hash gate、rewrite deterministic gate、source body drift gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/rewrite-0.3.27`

## [0.3.26] - 2026-07-24

- Release tag：`v0.3.26`
- 公開文章總數：393
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 2 個 run；run_id：harness-new-20260723-25, harness-new-20260723-84。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.26`

## [0.3.25] - 2026-07-24

- Release tag：`v0.3.25`
- 公開文章總數：391
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-18。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.25`

## [0.3.24] - 2026-07-24

- Release tag：`v0.3.24`
- 公開文章總數：390
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-38。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.24`

## [0.3.23] - 2026-07-24

- Release tag：`v0.3.23`
- 公開文章總數：389
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-63。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.23`

## [0.3.22] - 2026-07-24

- Release tag：`v0.3.22`
- 公開文章總數：388
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-86。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.22`

## [0.3.21] - 2026-07-24

- Release tag：`v0.3.21`
- 公開文章總數：387
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-55。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.21`

## [0.3.20] - 2026-07-24

- Release tag：`v0.3.20`
- 公開文章總數：386
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-14。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.20`

## [0.3.19] - 2026-07-23

- Release tag：`v0.3.19`
- 公開文章總數：385
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-41。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.19`

## [0.3.18] - 2026-07-23

- Release tag：`v0.3.18`
- 公開文章總數：384
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-77。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.18`

## [0.3.17] - 2026-07-23

- Release tag：`v0.3.17`
- 公開文章總數：383
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-33。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.17`

## [0.3.16] - 2026-07-23

- Release tag：`v0.3.16`
- 公開文章總數：382
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-61。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.16`

## [0.3.15] - 2026-07-23

- Release tag：`v0.3.15`
- 公開文章總數：381
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-69。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.15`

## [0.3.14] - 2026-07-23

- Release tag：`v0.3.14`
- 公開文章總數：380
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-35。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.14`

## [0.3.13] - 2026-07-23

- Release tag：`v0.3.13`
- 公開文章總數：379
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 6 個 run；run_id：harness-new-20260723-04, harness-new-20260723-81, harness-new-20260723-13, harness-new-20260723-09, harness-new-20260723-54, harness-new-20260723-68。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.13`

## [0.3.12] - 2026-07-23

- Release tag：`v0.3.12`
- 公開文章總數：374
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-04。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.12`

## [0.3.11] - 2026-07-23

- Release tag：`v0.3.11`
- 公開文章總數：373
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-76。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.11`

## [0.3.10] - 2026-07-23

- Release tag：`v0.3.10`
- 公開文章總數：372
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-10。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.10`

## [0.3.9] - 2026-07-23

- Release tag：`v0.3.9`
- 公開文章總數：371
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-39。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.9`

## [0.3.8] - 2026-07-23

- Release tag：`v0.3.8`
- 公開文章總數：370
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-36。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.8`

## [0.3.7] - 2026-07-23

- Release tag：`v0.3.7`
- 公開文章總數：369
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-75。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.7`

## [0.3.6] - 2026-07-23

- Release tag：`v0.3.6`
- 公開文章總數：368
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-82。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.6`

## [0.3.5] - 2026-07-23

- Release tag：`v0.3.5`
- 公開文章總數：367
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-65。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.5`

## [0.3.4] - 2026-07-23

- Release tag：`v0.3.4`
- 公開文章總數：366
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-43。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.4`

## [0.3.3] - 2026-07-23

- Release tag：`v0.3.3`
- 公開文章總數：365
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-95。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.3`

## [0.3.2] - 2026-07-23

- Release tag：`v0.3.2`
- 公開文章總數：364
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 10 個 run；run_id：harness-new-20260723-79, harness-new-20260723-99, harness-new-20260723-73, harness-new-20260723-21, harness-new-20260723-62, harness-new-20260723-97, harness-new-20260723-50, harness-new-20260723-93, harness-new-20260723-56, harness-new-20260723-30。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.2`

## [0.3.1] - 2026-07-23

- Release tag：`v0.3.1`
- 公開文章總數：354
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-24。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.1`

## [0.3.0] - 2026-07-23

- Release tag：`v0.3.0`
- 公開文章總數：353
- 發布範圍：新增 opt-in Gemini V4 broker、durable ledger／replay、agy CLI compatibility 與 canary 基礎設施；受監督產文維持 legacy CLI 並與 V4 解耦。另新增「土星回歸是什麼？30歲前後的工作與關係觀察」，每日產文 CLI 可明確鎖定零次內容修補。
- 相容性：既有 API 與預設產文 transport 不變；V4 必須明確設定 `AGY_GEMINI_V4_BROKER=1` 才啟用。
- 驗證：Gemini Writer 與 fresh Reviewer 通過；255 tests passed；V4 synthetic／canary evidence、prerender、feed、sitemap、本機 desktop／mobile browser acceptance 與 `git diff --check` 通過。
- 證據：`artifacts/fortune_council/content_pipeline_repair_execution/evidence/`、`artifacts/fortune_council/content_seo_execution/evidence/daily_publishing/daily-20260723-repair-01/`

## [0.2.0] - 2026-07-20

- Release tag：`v0.2.0`
- 公開文章總數：352
- 發布範圍：整合 Venus 補充文章與 Article Expansion 50E，新增 52 篇公開文章；保留 Gemini rewrite release cache 契約。
- 發布 commits：`90c5860`、`b6742f9`、`6087cdb`、`f7a5fb2`、`98fd144`
- 驗證：177 tests passed；352 個 article ID、slug 與公開路徑皆唯一；prerender 生成器冪等；`git diff --check` 通過。
- 證據：`artifacts/fortune_council/content_seo_execution/evidence/article_expansion_50e/`
