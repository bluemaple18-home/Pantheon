#!/usr/bin/env python3
"""驗證 www host 是否以單一步驟永久轉址到 non-www canonical。"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

CANONICAL_HOST = "mysticpantheon.com"
WWW_HOST = f"www.{CANONICAL_HOST}"
PERMANENT_REDIRECTS = {301, 308}


class _NoRedirect(HTTPRedirectHandler):
    """保留第一個回應，避免 client 自動跟隨轉址。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


@dataclass(frozen=True)
class Response:
    status: int
    location: str | None = None


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


def fetch_once(url: str, timeout: float) -> Response:
    """取得單一 HTTP 回應，不自動跟隨 Location。"""

    opener = build_opener(_NoRedirect)
    request = Request(url, headers={"User-Agent": "PantheonCanonicalVerifier/1.0"})
    try:
        response = opener.open(request, timeout=timeout)
    except HTTPError as error:
        return Response(error.code, error.headers.get("Location"))
    return Response(response.status, response.headers.get("Location"))


def build_probe_urls(path: str, query: str) -> tuple[tuple[str, str], ...]:
    """建立 HTTP/HTTPS www 來源與 canonical HTTPS 探針。"""

    suffix = f"{path}?{query}" if query else path
    target = f"https://{CANONICAL_HOST}{suffix}"
    return (
        (f"http://{WWW_HOST}{suffix}", target),
        (f"https://{WWW_HOST}{suffix}", target),
    )


def evaluate_www_redirect(source: str, expected: str, response: Response) -> Check:
    """確認 www 直接永久轉到完整 canonical URL。"""

    if response.status not in PERMANENT_REDIRECTS:
        return Check(source, False, f"預期 301/308，實際 {response.status}")
    if response.location != expected:
        return Check(source, False, f"Location 預期 {expected}，實際 {response.location!r}")
    return Check(source, True, f"{response.status} -> {response.location}")


def evaluate_canonical_response(url: str, response: Response) -> Check:
    """確認 canonical HTTPS 不會再轉走，避免 host loop 或多一步轉址。"""

    if 300 <= response.status < 400:
        return Check(url, False, f"canonical 不應轉址：{response.status} -> {response.location!r}")
    if not 200 <= response.status < 300:
        return Check(url, False, f"canonical 預期 2xx，實際 {response.status}")
    return Check(url, True, f"{response.status}（無轉址）")


def verify(path: str, query: str, timeout: float) -> list[Check]:
    """執行 www 轉址與 canonical 無 loop 驗證。"""

    probes = build_probe_urls(path, query)
    checks = [
        evaluate_www_redirect(source, expected, fetch_once(source, timeout))
        for source, expected in probes
    ]
    canonical_url = probes[0][1]
    checks.append(evaluate_canonical_response(canonical_url, fetch_once(canonical_url, timeout)))
    return checks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        default="/articles/tarot/tarot-0003",
        help="已知存在的公開路徑，必須以 / 開頭",
    )
    parser.add_argument(
        "--query",
        default=urlencode({"canonical_probe": "www redirect", "source": "task-003"}),
        help="不含 ? 的 query string；用於驗證完整保留",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="每次請求 timeout 秒數")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.path.startswith("/") or args.path.startswith("//"):
        raise SystemExit("--path 必須是單一 host 內、以 / 開頭的路徑")
    try:
        checks = verify(args.path, args.query, args.timeout)
    except (URLError, TimeoutError) as error:
        print(f"FAIL network: {error}")
        return 2

    for check in checks:
        print(f"{'PASS' if check.passed else 'FAIL'} {check.name}: {check.detail}")
    return 0 if all(check.passed for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
