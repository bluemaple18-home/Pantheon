# Shadow daemon decision

Date: 2026-07-25

Decision: `KEEP_ACTIVE_SHADOW_OBSERVE`

- LaunchAgent、六小時bucket、每日四筆上限與same-bucket no-resend皆已驗證。
- 第一筆closed diagnostic為`PROVIDER_UNAVAILABLE`，不把它誤報為transport PASS。
- 保持獨立shadow常駐，讓下一個bucket形成新的health observation。
- 不對失敗operation retry、不換credential slot、不fallback。
- 不修改正式產文coordinator、publisher或default transport。
- 未取得多個後續bucket穩定結果前，不做放量或migration決策。
