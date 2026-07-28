from pathlib import Path

from scripts.verify_host_canonical import (
    Response,
    build_probe_urls,
    evaluate_apex_redirect,
    evaluate_canonical_response,
)


def test_deployment_workflow_examples_use_canonical_host() -> None:
    workflow = Path("docs/pantheon_deployment_workflow.md").read_text(encoding="utf-8")

    assert "URL: https://mysticpantheon.com/articles/" not in workflow
    assert "URL: https://www.mysticpantheon.com/articles/" in workflow


def test_build_probe_urls_covers_http_https_and_preserves_path_query() -> None:
    probes = build_probe_urls("/articles/tarot/tarot-0003", "a=1&b=two")

    assert probes == (
        (
            "http://mysticpantheon.com/articles/tarot/tarot-0003?a=1&b=two",
            "https://www.mysticpantheon.com/articles/tarot/tarot-0003?a=1&b=two",
        ),
        (
            "https://mysticpantheon.com/articles/tarot/tarot-0003?a=1&b=two",
            "https://www.mysticpantheon.com/articles/tarot/tarot-0003?a=1&b=two",
        ),
    )


def test_apex_permanent_redirect_passes_for_301_and_308() -> None:
    source = "https://mysticpantheon.com/example?x=1"
    target = "https://www.mysticpantheon.com/example?x=1"

    assert evaluate_apex_redirect(source, target, Response(301, target)).passed
    assert evaluate_apex_redirect(source, target, Response(308, target)).passed


def test_apex_temporary_redirect_fails() -> None:
    check = evaluate_apex_redirect(
        "https://mysticpantheon.com/example",
        "https://www.mysticpantheon.com/example",
        Response(302, "https://www.mysticpantheon.com/example"),
    )

    assert not check.passed
    assert "301/308" in check.detail


def test_apex_redirect_fails_when_path_or_query_is_lost() -> None:
    check = evaluate_apex_redirect(
        "https://mysticpantheon.com/example?x=1",
        "https://www.mysticpantheon.com/example?x=1",
        Response(301, "https://www.mysticpantheon.com/"),
    )

    assert not check.passed
    assert "Location 預期" in check.detail


def test_canonical_https_2xx_does_not_loop() -> None:
    check = evaluate_canonical_response(
        "https://www.mysticpantheon.com/example",
        Response(200),
    )

    assert check.passed


def test_canonical_redirect_to_apex_is_rejected_as_loop() -> None:
    check = evaluate_canonical_response(
        "https://www.mysticpantheon.com/example",
        Response(301, "https://mysticpantheon.com/example"),
    )

    assert not check.passed
    assert "不應轉址" in check.detail
