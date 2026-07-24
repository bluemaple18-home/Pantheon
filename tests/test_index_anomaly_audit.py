import json

from scripts.index_anomaly_audit import (
    CLASS_CURRENT_BUG,
    CLASS_MORE_EVIDENCE,
    CLASS_WAITING,
    ResponseSnapshot,
    TARGET_HISTORY,
    audit_snapshots,
    main,
)


def page(path: str, *, robots: str = "index,follow", canonical: str | None = None) -> str:
    canonical = canonical or f"https://mysticpantheon.com{path}"
    return f"""<!doctype html>
<html><head>
<meta charset="utf-8">
<title>可索引頁面</title>
<meta name="description" content="足以供測試使用的 rendered description">
<meta name="robots" content="{robots}">
<meta property="og:url" content="https://mysticpantheon.com{path}">
<link rel="canonical" href="{canonical}">
<script type="application/ld+json">{{"@type":"WebPage","url":"https://mysticpantheon.com{path}"}}</script>
</head><body><h1>可索引頁面</h1></body></html>"""


def healthy_responses() -> dict[str, ResponseSnapshot]:
    responses = {
        path: ResponseSnapshot(status=200, headers={}, body=page(path))
        for path in TARGET_HISTORY
    }
    responses["/discovery"] = ResponseSnapshot(
        status=200,
        headers={},
        body="".join(f'<a href="{path}">target</a>' for path in TARGET_HISTORY),
    )
    return responses


def test_historical_signals_are_separated_from_current_output() -> None:
    report = audit_snapshots(healthy_responses(), discovery_complete=True)

    assert report["findings"]["/articles/career/career-0001"]["classification"] == CLASS_MORE_EVIDENCE
    for path in (
        "/articles/personality/personality-0017",
        "/articles/tarot/tarot-0048",
        "/articles/tarot/tarot-0009",
        "/articles",
    ):
        assert report["findings"][path]["classification"] == CLASS_WAITING
        assert report["findings"][path]["current_issues"] == []


def test_x_robots_noindex_is_a_current_bug() -> None:
    responses = healthy_responses()
    path = "/articles/personality/personality-0017"
    responses[path] = ResponseSnapshot(
        status=200,
        headers={"x-robots-tag": "googlebot: noindex, follow"},
        body=page(path),
    )

    finding = audit_snapshots(responses, discovery_complete=True)["findings"][path]

    assert finding["classification"] == CLASS_CURRENT_BUG
    assert "x_robots_noindex" in finding["current_issues"]


def test_meta_robots_noindex_is_a_current_bug() -> None:
    responses = healthy_responses()
    path = "/articles/tarot/tarot-0048"
    responses[path] = ResponseSnapshot(status=200, headers={}, body=page(path, robots="noindex,follow"))

    finding = audit_snapshots(responses, discovery_complete=True)["findings"][path]

    assert finding["classification"] == CLASS_CURRENT_BUG
    assert "meta_robots_noindex" in finding["current_issues"]


def test_canonical_mismatch_is_a_current_bug() -> None:
    responses = healthy_responses()
    path = "/articles/tarot/tarot-0009"
    responses[path] = ResponseSnapshot(
        status=200,
        headers={},
        body=page(path, canonical="https://mysticpantheon.com/articles/tarot/tarot-0008"),
    )

    finding = audit_snapshots(responses, discovery_complete=True)["findings"][path]

    assert finding["classification"] == CLASS_CURRENT_BUG
    assert "canonical_mismatch" in finding["current_issues"]


def test_undiscoverable_page_requires_complete_crawl_before_bug_classification() -> None:
    responses = healthy_responses()
    responses["/discovery"] = ResponseSnapshot(status=200, headers={}, body="<p>no links</p>")
    path = "/articles/career/career-0001"

    complete = audit_snapshots(responses, discovery_complete=True)["findings"][path]
    partial = audit_snapshots(responses, discovery_complete=False)["findings"][path]

    assert complete["classification"] == CLASS_CURRENT_BUG
    assert "no_internal_inbound_link" in complete["current_issues"]
    assert partial["classification"] == CLASS_MORE_EVIDENCE
    assert "no_internal_inbound_link" not in partial["current_issues"]


def test_cli_executes_saved_fixture(tmp_path, capsys) -> None:
    responses = healthy_responses()
    fixture = tmp_path / "responses.json"
    fixture.write_text(
        json.dumps(
            {
                "discovery_complete": True,
                "responses": {
                    path: {
                        "status": response.status,
                        "headers": response.headers,
                        "body": response.body,
                    }
                    for path, response in responses.items()
                },
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(["--fixture", str(fixture)])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["source"]["fixture"] == str(fixture)
    assert output["classification_counts"][CLASS_CURRENT_BUG] == 0
