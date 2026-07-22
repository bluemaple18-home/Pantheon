# Root cause

- 已存在且曾成功使用的本機 transport 是 Antigravity `agy` CLI；問題不是「Gemini CLI 未安裝」。
- V4 broker 原先固定執行 `Popen([executable], stdin=raw_request, env={})`。
- `agy 1.1.5` 的非互動 parser 要求 `--print <prompt>`，且既有成功 transport 同時提供 model label、plan、sandbox、log file 與 print timeout。
- 因此 V4 broker 與實際 CLI 介面不相容；在已知錯誤介面上跑真模型 canary 只會浪費一次外部呼叫，不能驗證 transport。

修復採 closed `antigravity_cli_v1` profile，不變更 runner、outbox、文章或發布流程。
