from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.gsc_client import GSC_READONLY_SCOPE, GscReadonlyClient, access_token
from scripts.gsc_daily_fetch import build_snapshot, snapshot_path, visible_row_totals, write_snapshot


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_access_token_refreshes_and_preserves_readonly_scope(tmp_path: Path) -> None:
    (tmp_path / "client.json").write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "client",
                    "client_secret": "secret",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "token.json").write_text(
        json.dumps({"refresh_token": "refresh", "scope": GSC_READONLY_SCOPE}),
        encoding="utf-8",
    )

    def fake_urlopen(request: Any, timeout: int) -> FakeResponse:
        assert timeout == 30
        assert request.full_url == "https://oauth2.googleapis.com/token"
        return FakeResponse({"access_token": "new-token", "expires_in": 3600, "scope": GSC_READONLY_SCOPE})

    assert access_token(config_dir=tmp_path, urlopen=fake_urlopen) == "new-token"
    saved = json.loads((tmp_path / "token.json").read_text(encoding="utf-8"))
    assert saved["refresh_token"] == "refresh"
    assert saved["expires_at"] > 0
    assert (tmp_path / "token.json").stat().st_mode & 0o777 == 0o600


def test_access_token_rejects_broader_scope(tmp_path: Path) -> None:
    (tmp_path / "client.json").write_text(json.dumps({"installed": {}}), encoding="utf-8")
    (tmp_path / "token.json").write_text(
        json.dumps({"access_token": "token", "scope": f"{GSC_READONLY_SCOPE} other"}),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="唯讀 scope"):
        access_token(config_dir=tmp_path)


def test_query_all_paginates_with_start_row() -> None:
    starts: list[int] = []

    def fake_urlopen(request: Any, timeout: float) -> FakeResponse:
        assert timeout == 30.0
        payload = json.loads(request.data)
        starts.append(payload["startRow"])
        rows = [{"keys": [f"/articles/{payload['startRow'] + index}", "q"]} for index in range(2)]
        if payload["startRow"] >= 4:
            rows = [{"keys": ["/articles/4", "q"]}]
        return FakeResponse({"rows": rows})

    client = GscReadonlyClient("token", urlopen=fake_urlopen)
    rows, warnings, page_count = client.query_all(
        "sc-domain:mysticpantheon.com",
        "2026-07-21",
        "2026-07-21",
        page_size=2,
        max_rows=10,
    )
    assert starts == [0, 2, 4]
    assert len(rows) == 5
    assert warnings == []
    assert page_count == 3


def test_query_all_warns_when_max_rows_is_reached() -> None:
    def fake_urlopen(_request: Any, timeout: float) -> FakeResponse:
        assert timeout == 30.0
        return FakeResponse({"rows": [{"keys": ["/articles/a", "q"]}, {"keys": ["/articles/b", "q"]}]})

    rows, warnings, page_count = GscReadonlyClient("token", urlopen=fake_urlopen).query_all(
        "sc-domain:mysticpantheon.com",
        "2026-07-21",
        "2026-07-21",
        page_size=2,
        max_rows=4,
    )
    assert len(rows) == 4
    assert page_count == 2
    assert warnings == [
        {
            "reason_code": "MAX_ROWS_REACHED",
            "stage": "gsc_pagination",
            "record": "sc-domain:mysticpantheon.com",
            "impact_count": 4,
        }
    ]


def test_query_all_warns_when_non_multiple_max_rows_is_reached() -> None:
    requested_limits: list[int] = []

    def fake_urlopen(request: Any, timeout: float) -> FakeResponse:
        assert timeout == 30.0
        payload = json.loads(request.data)
        requested_limits.append(payload["rowLimit"])
        return FakeResponse(
            {"rows": [{"keys": [f"/articles/{payload['startRow'] + index}", "q"]} for index in range(payload["rowLimit"])]}
        )

    rows, warnings, page_count = GscReadonlyClient("token", urlopen=fake_urlopen).query_all(
        "sc-domain:mysticpantheon.com",
        "2026-07-21",
        "2026-07-21",
        page_size=2,
        max_rows=5,
    )
    assert requested_limits == [2, 2, 1]
    assert len(rows) == 5
    assert page_count == 3
    assert warnings[0]["reason_code"] == "MAX_ROWS_REACHED"


def test_snapshot_contract_and_atomic_write(tmp_path: Path) -> None:
    rows = [
        {"keys": ["https://mysticpantheon.com/articles/a", "甲"], "clicks": 2, "impressions": 10},
        {"keys": ["https://mysticpantheon.com/articles/a", "乙"], "clicks": 1, "impressions": 20},
    ]
    assert visible_row_totals(rows) == {
        "rows": 2,
        "pages": 1,
        "queries": 2,
        "clicks": 3.0,
        "impressions": 30.0,
    }
    output = snapshot_path(tmp_path, "sc-domain:mysticpantheon.com", "2026-07-21", "2026-07-21")
    snapshot = build_snapshot(
        property_url="sc-domain:mysticpantheon.com",
        start_date="2026-07-21",
        end_date="2026-07-21",
        rows=rows,
        warnings=[],
        page_count=1,
        fetched_at="2026-07-24T00:00:00+00:00",
    )
    write_snapshot(output, snapshot)
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["pagination"] == {"pages": 1, "complete": True}
    assert saved["visible_row_totals"]["impressions"] == 30.0
