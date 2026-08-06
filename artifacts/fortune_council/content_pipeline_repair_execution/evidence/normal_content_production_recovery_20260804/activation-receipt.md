# Activation receipt

- deployment candidate：`efe69373e6326e7da07be85d1ca1ca5ceb5cbd20`
- initial Publisher runtime digest：`d073d48d1f0f11c17c4bb5589b671c9b13f72ec071ca985b69c79e0572eb2021`
- loaded：`com.pantheon.agy-content-publisher`、`com.pantheon.agy-gemini-coordinator`、`com.pantheon.agy-gemini-new`、`com.pantheon.agy-gemini-rewrite`
- unloaded：`com.pantheon.agy-gemini-i18n-new`、`com.pantheon.agy-gemini-i18n-rewrite`
- watchdog：`com.pantheon.content-capacity-guard` loaded；所有觀察樣本 PASS。
- autonomous continuation：Publisher 在 `v0.3.290` 後未經人工重載，即由下一個 StartInterval 自行啟動並發布 `v0.3.291`；lagging actor deployment preflight 仍為 `ready`，runtime paths 無 drift。

判定：`PASS`。
