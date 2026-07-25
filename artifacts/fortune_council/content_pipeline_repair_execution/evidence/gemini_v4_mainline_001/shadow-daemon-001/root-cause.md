# Root cause

Date: 2026-07-25

一次性shadow只證明當下transport，不能持續發現credential、quota、provider、
schema或本機runtime漂移。既有Gemini coordinator服務正式產文queue，不能混入
health check，否則會讓shadow失敗影響文章狀態。

最小修正是獨立LaunchAgent與state root，以UTC六小時bucket建立固定公開request。
每個bucket有獨立queue、ledger與anchor；同bucket重入只讀durable結果，不重送。
每天最多四個新operation，失敗不換key、不fallback，也不阻擋文章。

第一筆常駐觀察得到closed `PROVIDER_UNAVAILABLE`。這證明fail-closed與no-resend
邊界有效，但不證明provider長期健康；服務保持啟用，等待下一個新bucket觀察。
