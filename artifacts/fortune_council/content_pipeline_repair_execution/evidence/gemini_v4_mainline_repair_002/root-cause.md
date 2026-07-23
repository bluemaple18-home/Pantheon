# Root cause

## Fixed identity

- base：`233ddc25032e0cac4bbc5d3144dbc383f49c0c18`
- base parent：`6c4931c1da63257cd70bd0abe5776dc1758e4557`
- canonical re-review commit：`9279516ed98465fbec535b836e58b078c2157a0d`
- finding：`P1_TRUSTED_RESULT_SCHEMA`
- Repair generation：`2/2`

## Root cause

Repair-1 的 standalone verifier 在驗證 execution 與 inbox result 時，直接使用 bundle
自帶的 `result_schema`。Verifier 雖然檢查 bundle top-level fields closed，卻沒有獨立可信的
fixed canary result contract。因此只要攻擊者同步放寬 schema 並替換 execution／inbox result，
整份 bundle 仍可自洽並被錯誤接受。

既有 `wrong_result_schema` mutation 只改 execution result，並未修改 schema；它只能證明 result
與 recorder 自述 schema 不一致時會被拒絕，不能證明 verifier 會拒絕被一致放寬的 schema。

## Minimal repair

Verifier 內建固定 closed schema，並要求 bundle `result_schema` 與該 contract 完全一致。
execution 與 inbox result 均只依 trusted schema 驗證。另以 canonical result bytes（既有
recorder 的無結尾換行或單一結尾換行）重算並綁定 `byte_count` 與 `stdout_sha256`。

Mutation matrix 保留原 result-only control，新增實際修改 schema 的
`wrong_result_schema` 與同步修改 schema／execution／inbox 的
`coherent_weakened_schema`。未修改 recorder、broker、真實 bundle或 production scope。
