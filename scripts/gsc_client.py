#!/usr/bin/env python3
"""Google Search Console 唯讀 OAuth 與分頁 client。"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable


GSC_API = "https://www.googleapis.com/webmasters/v3"
URL_INSPECTION_API = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
GSC_READONLY_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
DEFAULT_PAGE_SIZE = 25_000
DEFAULT_MAX_ROWS = 250_000


def compact_json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def default_config_dir() -> Path:
    configured = os.environ.get("GSC_CONFIG_DIR", "").strip()
    return Path(configured).expanduser() if configured else Path.home() / ".config" / "pantheon-gsc"


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RuntimeError(f"找不到 GSC credential：{path}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"GSC credential 不是有效 JSON：{path}") from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"GSC credential root 必須是 object：{path}")
    return payload


def _write_private_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_bytes(compact_json_bytes(payload) + b"\n")
    temporary.chmod(0o600)
    temporary.replace(path)
    path.chmod(0o600)


def _scope_set(value: object) -> set[str]:
    if isinstance(value, str):
        return set(value.split())
    if isinstance(value, list):
        return {str(item) for item in value}
    return set()


def _validate_readonly_scope(token: dict[str, Any]) -> None:
    scopes = _scope_set(token.get("scope"))
    if scopes != {GSC_READONLY_SCOPE}:
        raise RuntimeError(f"GSC token scope 必須恰為唯讀 scope，目前為：{sorted(scopes)}")


def _refresh_access_token(
    client_path: Path,
    token_path: Path,
    *,
    urlopen: Callable[..., Any] = urllib.request.urlopen,
) -> str:
    client_payload = _read_json_object(client_path)
    installed = client_payload.get("installed")
    if not isinstance(installed, dict):
        raise RuntimeError(f"OAuth client 缺少 installed 設定：{client_path}")
    token = _read_json_object(token_path)
    _validate_readonly_scope(token)
    refresh_token = str(token.get("refresh_token") or "")
    if not refresh_token:
        raise RuntimeError("GSC token 缺少 refresh_token，必須重新授權")

    form = urllib.parse.urlencode(
        {
            "client_id": str(installed.get("client_id") or ""),
            "client_secret": str(installed.get("client_secret") or ""),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    ).encode("ascii")
    request = urllib.request.Request(
        str(installed.get("token_uri") or "https://oauth2.googleapis.com/token"),
        data=form,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            refreshed = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Google OAuth refresh HTTP {error.code}: {detail}") from error
    if not isinstance(refreshed, dict) or not refreshed.get("access_token"):
        raise RuntimeError("Google OAuth refresh 未回傳 access_token")

    merged = {**token, **refreshed, "refresh_token": refresh_token}
    merged["scope"] = refreshed.get("scope") or token.get("scope")
    merged["expires_at"] = int(time.time()) + int(refreshed.get("expires_in") or 3600)
    _validate_readonly_scope(merged)
    _write_private_json(token_path, merged)
    return str(merged["access_token"])


def access_token(
    *,
    config_dir: Path | None = None,
    urlopen: Callable[..., Any] = urllib.request.urlopen,
) -> str:
    """依序使用環境 token、持久 OAuth token，最後才嘗試 gcloud ADC。"""
    environment_token = os.environ.get("GSC_ACCESS_TOKEN", "").strip()
    if environment_token:
        return environment_token

    credentials_dir = config_dir or default_config_dir()
    token_path = credentials_dir / "token.json"
    client_path = credentials_dir / "client.json"
    if token_path.exists() or client_path.exists():
        token = _read_json_object(token_path)
        _validate_readonly_scope(token)
        expires_at = int(token.get("expires_at") or 0)
        current = str(token.get("access_token") or "")
        if current and expires_at > int(time.time()) + 60:
            return current
        return _refresh_access_token(client_path, token_path, urlopen=urlopen)

    try:
        result = subprocess.run(
            [
                "gcloud",
                "auth",
                "application-default",
                "print-access-token",
                f"--scopes={GSC_READONLY_SCOPE}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise RuntimeError(
            f"找不到 GSC credential；請設定 GSC_ACCESS_TOKEN 或放置 {client_path} 與 {token_path}"
        ) from error
    current = result.stdout.strip()
    if not current:
        raise RuntimeError("gcloud 回傳空的 access token")
    return current


class GscReadonlyClient:
    def __init__(
        self,
        access_token: str,
        timeout: float = 30.0,
        *,
        urlopen: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self.access_token = access_token
        self.timeout = timeout
        self.urlopen = urlopen

    def _request(self, method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = compact_json_bytes(payload) if payload is not None else None
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with self.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"GSC HTTP {error.code}: {detail}") from error
        if not isinstance(result, dict):
            raise RuntimeError("GSC API response root 必須是 object")
        return result

    def list_properties(self) -> list[dict[str, Any]]:
        return list(self._request("GET", f"{GSC_API}/sites").get("siteEntry") or [])

    def inspect_url(
        self,
        property_url: str,
        inspection_url: str,
        *,
        language_code: str = "en-US",
    ) -> dict[str, Any]:
        response = self._request(
            "POST",
            URL_INSPECTION_API,
            {
                "siteUrl": property_url,
                "inspectionUrl": inspection_url,
                "languageCode": language_code,
            },
        )
        result = response.get("inspectionResult")
        if not isinstance(result, dict):
            raise RuntimeError(f"URL Inspection 缺少 inspectionResult：{inspection_url}")
        return result

    def query_page(
        self,
        property_url: str,
        start_date: str,
        end_date: str,
        *,
        start_row: int = 0,
        row_limit: int = DEFAULT_PAGE_SIZE,
    ) -> list[dict[str, Any]]:
        encoded = urllib.parse.quote(property_url, safe="")
        payload = {
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": ["page", "query"],
            "dimensionFilterGroups": [
                {"filters": [{"dimension": "page", "operator": "contains", "expression": "/articles/"}]}
            ],
            "rowLimit": min(row_limit, DEFAULT_PAGE_SIZE),
            "startRow": start_row,
            "dataState": "final",
        }
        response = self._request("POST", f"{GSC_API}/sites/{encoded}/searchAnalytics/query", payload)
        return list(response.get("rows") or [])

    def query_all(
        self,
        property_url: str,
        start_date: str,
        end_date: str,
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_rows: int = DEFAULT_MAX_ROWS,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
        if not 1 <= page_size <= DEFAULT_PAGE_SIZE:
            raise ValueError(f"page_size 必須介於 1 與 {DEFAULT_PAGE_SIZE}")
        if max_rows < page_size:
            raise ValueError("max_rows 不得小於 page_size")

        rows: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        page_count = 0
        while len(rows) < max_rows:
            requested_size = min(page_size, max_rows - len(rows))
            batch = self.query_page(
                property_url,
                start_date,
                end_date,
                start_row=len(rows),
                row_limit=requested_size,
            )
            page_count += 1
            rows.extend(batch)
            if len(batch) < requested_size:
                break
        if len(rows) >= max_rows:
            warnings.append(
                {
                    "reason_code": "MAX_ROWS_REACHED",
                    "stage": "gsc_pagination",
                    "record": property_url,
                    "impact_count": len(rows),
                }
            )
        return rows, warnings, page_count

    def query(
        self,
        property_url: str,
        start_date: str,
        end_date: str,
        row_limit: int = DEFAULT_PAGE_SIZE,
    ) -> list[dict[str, Any]]:
        """保留既有單頁介面；新資料管線應使用 query_all。"""
        return self.query_page(property_url, start_date, end_date, row_limit=row_limit)
