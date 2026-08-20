# Cycle 17 formal preflight contract correction

## 結論

`PATCHED / NO RUNTIME EXECUTION`

既有 source seam 足以表達安全順序，無 `CONTRACT-SEAM CONFLICT`：promotion 先 materialize target actor／manifest／barrier；coordinator 與 Publisher installer 先形成六服務 stage；capacity installer 的 `--preflight` 在 capacity plist install 前退出；PASS 後原七服務 restaging authority 才允許 capacity `--install` 寫入第七份 plist。

## 契約修正摘要

- 明確拆開 Cycle 16 bounded synthetic capacity receipt 與 target formal runtime identity/capacity public preflight。
- tooling venv 僅屬 Gate A／promotion tooling authority；formal preflight 必須綁 target manifest materialize 後的 manifest-bound Python。
- formal seam 鎖為 authoritative target actor 內的 capacity installer `--preflight`，並要求 plan、postcheck、authorization 與 argv 使用同一 target manifest digest。
- exact argv 必含 canonical `TMPDIR=/private/tmp`；禁止 `/tmp` fallback、direct module、system Python 或 current manifest 代驗。
- 新 formal preflight authorization 必須與 Gate A authorization 分離，且綁 exact argv digest、target actor、manifest path/digest 與 Python。
- gate order 鎖為：Cycle 16 receipt → zero-write plan → Gate A/push/promotion → 六服務 stage → 單次 formal preflight → capacity install → 七服務 staged postcheck。
- Publisher no-PID 被標記為 transition 預期輸入，禁止先 activation/reload。
- 第一次 formal preflight 非 PASS 即停止；不得用 `--install`、換入口或第二次 preflight 重試。
- capacity `--install` 的內建安全重驗被界定為 PASS 後、mutation 前的 fail-closed revalidation，不得掩蓋 formal preflight 失敗。
- 原 Gate A、push、promotion、no-canary、queue preservation 與 production stop conditions 全部保留，沒有新增 production authority。

## 本次執行 counts

- public preflight：`0`
- Gate A：`0`
- push：`0`
- promotion：`0`
- restaging/install：`0`
- activation/canary/lane/Publisher/tag/publish：`0`
- runtime invocation：`0`
- production mutation：`0`

修正後 Cycle 17 card SHA256：`82513dce1f0d307c0538440b16d3cfa2a1b75ce1a16101508405c96e1e986e3e`。
