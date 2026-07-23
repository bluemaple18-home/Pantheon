# Gemini V4 Output Binding Repair｜Review Decision

## Delivery

`DELIVERED_CANDIDATE / GO`

## Findings

未發現 P0–P3 具體問題。

## Decision basis

- Candidate lineage精確：candidate的唯一parent為指定base，Review卡提交緊接
  candidate。
- 原始stdout bytes先通過control byte count／SHA-256、replay、process count與
  final anchor核對，才可能進入`BrokerResult.result_json`。
- 只有schema-valid JSON object保留已驗證raw bytes；malformed與schema-invalid
  output仍fail closed。
- `.result`、normalized trace與runner inbox只暴露parsed object。
- ledger／anchor exactly-once、replay／concurrent duplicate、flag-on no-fallback、
  flag-off legacy與privacy契約未弱化。
- Base到candidate changed files精確符合Repair allowlist。
- 獨立驗證共`137 passed`，另有synthetic trust-boundary harness通過；
  `py_compile`與`git diff --check`通過。
- 外部Gemini／agy invocation為`0`。

## Boundary

GO只表示Repair candidate可交回主線考慮整合，不表示rollout ready、已放量或已
上線。Blocked rollout evidence仍維持唯讀與blocked；整合後不得省略新的明確外部
canary授權、執行與獨立驗證。Provider internal model-call provenance仍為
`UNKNOWN`。
