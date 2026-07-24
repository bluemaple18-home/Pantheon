# www → non-www canonical runbook

## 判定

正式 canonical 為 `https://mysticpantheon.com`。這項修正必須位於 Cloudflare
zone 的 Redirect Rules，而不是 `app/web/_redirects`：

- 專案部署流程將 `app/web/_redirects` 視為 Cloudflare Pages 路徑規則。
- Cloudflare Pages 官方規格明列 `_redirects` 不支援 domain-level redirects。
- 因此 repository 無法只靠 `_redirects` 判斷 request host；寫入 www 規則會被忽略。

參考：

- [Cloudflare Pages `_redirects` 支援矩陣](https://developers.cloudflare.com/pages/configuration/redirects/#advanced-redirects)
- [Cloudflare Single Redirects：www 轉 root](https://developers.cloudflare.com/rules/url-forwarding/examples/redirect-www-to-root/)
- [Cloudflare Single Redirects 設定](https://developers.cloudflare.com/rules/url-forwarding/single-redirects/settings/)

## 外部設定方案

前置條件：`www.mysticpantheon.com` 必須有 Cloudflare DNS record，且 Proxy status
為 Proxied。若尚未滿足，先補 DNS／Pages custom domain；這是外部控制面變更。

在 Cloudflare Dashboard 的 `Rules > Redirect Rules > Single Redirects` 新增一條規則：

| 欄位 | 值 |
| --- | --- |
| Rule name | `canonical-www-to-apex` |
| If incoming requests match | Wildcard pattern |
| Request URL | `http*://www.mysticpantheon.com/*` |
| Target URL | `https://mysticpantheon.com/${2}` |
| Status code | `301` |
| Preserve query string | Enabled |

`http*` 的第一個 wildcard 會匹配 scheme 中可選的 `s`，第二個 wildcard 是完整
path，因此 target 使用 `${2}`。規則只匹配精確的 www host，non-www 不會命中，
可避免 host redirect loop。HTTP 與 HTTPS www 都會直接指向 HTTPS non-www，
不需要先經過 www 的 HTTP → HTTPS。

部署前先確認沒有更早、同樣匹配 www 的 Single Redirect；Cloudflare 對 redirect
採第一個匹配規則並立即終止。若有既存衝突，調整順序或停用衝突規則後再部署。

## 驗證與回退

部署後從 repository root 執行：

```bash
uv run python scripts/verify_host_canonical.py
```

成功條件：

1. HTTP www 回傳 301 或 308，`Location` 直接是 HTTPS non-www。
2. HTTPS www 回傳 301 或 308，且 path 與 query 完整保留。
3. HTTPS non-www 回傳 2xx，不再轉址，排除 loop。

失敗時先停用 `canonical-www-to-apex` 規則，再重跑 verifier，確認已回到原行為。
不要修改 `_redirects` 作為回退，因為它不控制 host-level redirect。
