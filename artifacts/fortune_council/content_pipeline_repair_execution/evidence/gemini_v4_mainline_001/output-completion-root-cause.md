# Output completion root cause

Date: 2026-07-24

Status: BLOCKED

## Localized layer

Canary-005 已把失敗定位在 target stdout 與 caller JSON contract 之間：

- durable replay：`COMPLETE`
- process count：`1`
- target outcome：`SUCCESS`
- caller validation：`JSON_INVALID`
- closed diagnostic：`PARSE_ERROR_AT_END`

因此 exactly-once ledger、anchor、replay、fork/exec、外層 timeout 與 legacy
fallback 都不是這次失敗層。broker 的 `MAX_RESULT_BYTES` 也不是相容解釋：超過
上限會讓 control frame 的 byte count／digest 與 parent 收到的 bytes 不一致並
fail closed，不會得到目前的 `SUCCESS + JSON_INVALID`。

## Production capability boundary

本機已驗證的 `agy 1.1.6` headless contract 是文字型
`--print <prompt>` 與 bounded `--print-timeout`。官方 1.1.6 help／文件未提供
JSON Schema、structured output、response MIME type或 output-token ceiling參數。
所以 runner 放進 prompt 的 canonical schema 只是模型指令，不是 transport
enforcement。

Primary references（read-only，2026-07-24）：

- `https://antigravity.google/docs/cli/using?app=antigravity`
- `https://github.com/google-antigravity/antigravity-cli/blob/main/CHANGELOG.md`
- `https://codelabs.developers.google.com/sdd-agy-cli`

repo 內 legacy writer 對格式錯誤的既有收斂方式是 bounded schema retry；V4 的
同一 operation exactly-once／no-fallback contract 明確禁止沿用該行為。

## Falsified or rejected repairs

- 增大 broker result ceiling：觀察結果不符合本機 2 MiB ceiling failure。
- 增加外層 timeout：target 約 14 秒 exit 0，沒有 timeout observable。
- 剝除 fence／wrapper：closed diagnostic 已排除這兩類。
- 自動補 `}`、`]`、引號或其他 token：必須猜測缺失內容，會改寫 model stdout，
  也會破壞 receipt／result digest 與 strict caller contract。
- retry 同一 job：違反 exactly-once，且 canary-005 已 terminal。
- 第四次真實 canary：同一長文章 `JSON_INVALID` blocker 已累計第三次，受 stop
  rule 禁止。

## Root cause and decision

可證明的架構根因是：目前 `agy 1.1.6 --print` transport 對長文章 JSON 只有
prompt-level convention，沒有 machine-enforced structured-output completion。
`PARSE_ERROR_AT_END` 的內部直接成因仍可能是 provider output limit、CLI
completion behavior 或模型提早結束；在不保存 raw output 的 privacy contract
下無法再細分，也不影響 transport 不具格式保證的結論。

在本卡 allowlist 與不可變契約內沒有可驗證的 production code repair。可行的新
主線必須二選一，且都超出本卡：

1. 改用供應商原生、可指定 JSON Schema／structured output與 output-token
   ceiling 的 transport，保留一次外部 generation。
2. 重新設計成多個較小的 generation/chunk operation，為每個 chunk 建獨立
   operation identity、ledger與上層組裝契約。

在任一替代 transport 通過新的 synthetic／real acceptance 前，legacy 維持唯一
預設產文 transport，V4 flag-on 繼續 fail closed。
