import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.seo_publish_gate import SnapshotContractError, evaluate_snapshot


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "seo_publish_gate.py"


def inspection_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "url": "https://example.com/article",
        "published_date": "2026-07-23",
        "verdict": "NEUTRAL",
        "coverage_state": "Discovered - currently not indexed",
        "indexing_state": "INDEXING_ALLOWED",
        "robots_txt_state": "ALLOWED",
        "page_fetch_state": "SUCCESSFUL",
        "user_canonical": "https://example.com/article",
        "google_canonical": "https://example.com/article",
    }
    row.update(overrides)
    return row


def snapshot(
    *rows: dict[str, object],
    inspection_date: str = "2026-07-24",
) -> dict[str, object]:
    return {"inspection_date": inspection_date, "urls": list(rows)}


def gsc_record(**index_overrides: object) -> dict[str, object]:
    index: dict[str, object] = {
        "verdict": "NEUTRAL",
        "coverageState": "Discovered - currently not indexed",
        "indexingState": "INDEXING_ALLOWED",
        "robotsTxtState": "ALLOWED",
        "pageFetchState": "SUCCESSFUL",
        "userCanonical": "https://example.com/article",
        "googleCanonical": "https://example.com/article",
    }
    index.update(index_overrides)
    return {
        "url": "https://example.com/article",
        "inspection": {"available": True, "index": index},
    }


def gsc_snapshot(*records: dict[str, object]) -> dict[str, object]:
    return {"observation_date": "2026-07-24", "records": list(records)}


@pytest.mark.parametrize(
    ("overrides", "inspection_date", "expected"),
    [
        ({"verdict": "PASS", "coverage_state": "Submitted and indexed"}, "2026-07-24", "indexed"),
        ({}, "2026-07-24", "new_under_observation"),
        ({"published_date": "2026-07-16"}, "2026-07-24", "overdue_discovered"),
        (
            {"published_date": "2026-07-16", "coverage_state": "Unknown"},
            "2026-07-24",
            "overdue_unknown",
        ),
        ({"indexing_state": "BLOCKED_BY_META_TAG"}, "2026-07-24", "blocked_by_noindex"),
        ({"indexing_state": "BLOCKED_BY_HTTP_HEADER"}, "2026-07-24", "blocked_by_noindex"),
        ({"robots_txt_state": "BLOCKED"}, "2026-07-24", "blocked_by_robots"),
        ({"page_fetch_state": "BLOCKED_ROBOTS_TXT"}, "2026-07-24", "blocked_by_robots"),
        ({"page_fetch_state": "SERVER_ERROR"}, "2026-07-24", "fetch_failed"),
        (
            {"google_canonical": "https://example.com/different"},
            "2026-07-24",
            "canonical_split",
        ),
    ],
)
def test_all_classifications(
    overrides: dict[str, object], inspection_date: str, expected: str
) -> None:
    report = evaluate_snapshot(
        snapshot(inspection_row(**overrides), inspection_date=inspection_date),
        7,
    )
    assert report["results"][0]["category"] == expected


def test_next_day_not_indexed_is_warning_not_failure() -> None:
    report = evaluate_snapshot(snapshot(inspection_row()), 7)
    assert report["status"] == "WARNING"
    assert report["results"][0]["severity"] == "warning"


def test_more_than_seven_days_not_indexed_fails() -> None:
    row = inspection_row(published_date="2026-07-16")
    report = evaluate_snapshot(snapshot(row), 7)
    assert report["status"] == "FAIL"
    assert report["results"][0]["severity"] == "fail"


def test_technical_blocker_fails_during_observation() -> None:
    row = inspection_row(indexing_state="BLOCKED_BY_META_TAG")
    report = evaluate_snapshot(snapshot(row), 7)
    assert report["status"] == "FAIL"
    assert report["results"][0]["category"] == "blocked_by_noindex"


def test_exactly_seven_days_remains_under_observation() -> None:
    row = inspection_row(published_date="2026-07-17")
    report = evaluate_snapshot(snapshot(row), 7)
    assert report["status"] == "WARNING"


def test_published_at_is_an_explicit_date_source() -> None:
    row = inspection_row(published_at="2026-07-23T09:00:00+08:00")
    del row["published_date"]
    report = evaluate_snapshot(snapshot(row), 7)
    assert report["results"][0]["published_date"] == "2026-07-23"


def test_missing_fields_are_reported() -> None:
    row = inspection_row()
    del row["coverage_state"]
    with pytest.raises(SnapshotContractError, match=r"urls\[0\] 缺少欄位：coverage_state"):
        evaluate_snapshot(snapshot(row), 7)


def test_invalid_date_is_reported_without_guessing() -> None:
    with pytest.raises(SnapshotContractError, match="不是有效 ISO 日期"):
        evaluate_snapshot(
            snapshot(inspection_row(published_date="2026-07-23T09:00:00")),
            7,
        )


def run_cli(
    tmp_path: Path,
    payload: dict[str, object],
    *args: str,
) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path), "--json", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_cli_exit_codes_and_machine_readable_json(tmp_path: Path) -> None:
    warning = run_cli(tmp_path, snapshot(inspection_row()))
    assert warning.returncode == 0
    assert json.loads(warning.stdout)["status"] == "WARNING"

    overdue = run_cli(
        tmp_path,
        snapshot(inspection_row(published_date="2026-07-16")),
    )
    assert overdue.returncode == 1
    assert json.loads(overdue.stdout)["status"] == "FAIL"

    invalid = run_cli(tmp_path, {"inspection_date": "2026-07-24", "urls": [{}]})
    assert invalid.returncode == 2
    assert json.loads(invalid.stdout)["status"] == "ERROR"


def test_cli_observation_days_override(tmp_path: Path) -> None:
    result = run_cli(tmp_path, snapshot(inspection_row()), "--observation-days", "0")
    report = json.loads(result.stdout)
    assert result.returncode == 1
    assert report["counts"] == {"overdue_discovered": 1}


@pytest.mark.parametrize(
    ("record", "published", "expected_category", "expected_status"),
    [
        (gsc_record(verdict="PASS"), "2026-07-23", "indexed", "PASS"),
        (gsc_record(), "2026-07-23", "new_under_observation", "WARNING"),
        (gsc_record(), "2026-07-16", "overdue_discovered", "FAIL"),
        (
            gsc_record(indexingState="BLOCKED_BY_META_TAG"),
            "2026-07-23",
            "blocked_by_noindex",
            "FAIL",
        ),
        (
            gsc_record(googleCanonical="https://example.com/other"),
            "2026-07-23",
            "canonical_split",
            "FAIL",
        ),
    ],
)
def test_real_gsc_nested_schema(
    record: dict[str, object],
    published: str,
    expected_category: str,
    expected_status: str,
) -> None:
    report = evaluate_snapshot(
        gsc_snapshot(record),
        7,
        {"https://example.com/article": published},
    )
    assert report["results"][0]["category"] == expected_category
    assert report["status"] == expected_status


def test_real_gsc_record_can_carry_published_date() -> None:
    record = gsc_record(verdict="PASS")
    record["published_date"] = "2026-07-23"
    report = evaluate_snapshot(gsc_snapshot(record), 7)
    assert report["status"] == "PASS"


def test_real_gsc_missing_published_mapping_is_error() -> None:
    with pytest.raises(SnapshotContractError, match="--published-dates"):
        evaluate_snapshot(gsc_snapshot(gsc_record()), 7)


def test_real_gsc_cli_published_dates_and_missing_mapping_exit_codes(
    tmp_path: Path,
) -> None:
    payload = gsc_snapshot(gsc_record())
    missing = run_cli(tmp_path, payload)
    assert missing.returncode == 2
    assert json.loads(missing.stdout)["status"] == "ERROR"

    dates_path = tmp_path / "published-dates.json"
    dates_path.write_text(
        json.dumps({"https://example.com/article": "2026-07-23"}),
        encoding="utf-8",
    )
    result = run_cli(tmp_path, payload, "--published-dates", str(dates_path))
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["counts"] == {"new_under_observation": 1}
