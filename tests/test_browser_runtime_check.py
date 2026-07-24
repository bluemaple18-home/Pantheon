from scripts.browser_runtime_check import (
    configure_playwright_browsers_path,
    evaluate_evidence,
)


def clean_evidence() -> dict[str, object]:
    return {
        "traceback": [],
        "console": [],
        "pageerror": [],
        "requestfailed": [],
        "http_errors": [],
        "javascript_ready": True,
    }


def test_clean_runtime_evidence_passes() -> None:
    assert evaluate_evidence(clean_evidence()) == "PASS"


def test_console_error_fails_runtime_check() -> None:
    evidence = clean_evidence()
    evidence["console"] = [{"type": "error", "text": "boom"}]

    assert evaluate_evidence(evidence) == "FAIL"


def test_page_or_network_failure_fails_runtime_check() -> None:
    page_error = clean_evidence()
    page_error["pageerror"] = ["ReferenceError"]
    request_failure = clean_evidence()
    request_failure["requestfailed"] = [{"url": "https://invalid.test/app.js"}]

    assert evaluate_evidence(page_error) == "FAIL"
    assert evaluate_evidence(request_failure) == "FAIL"


def test_missing_javascript_readiness_fails_runtime_check() -> None:
    evidence = clean_evidence()
    evidence["javascript_ready"] = False

    assert evaluate_evidence(evidence) == "FAIL"


def test_resolves_ai_core_browser_cache_when_environment_is_missing(tmp_path) -> None:
    browser_cache = tmp_path / "ai-core/.tools/cache/ms-playwright"
    browser_cache.mkdir(parents=True)
    environ: dict[str, str] = {}

    resolved = configure_playwright_browsers_path(environ, home=tmp_path)

    assert resolved == str(browser_cache)
    assert environ["PLAYWRIGHT_BROWSERS_PATH"] == str(browser_cache)


def test_preserves_explicit_browser_cache(tmp_path) -> None:
    explicit = str(tmp_path / "custom-playwright")
    environ = {"PLAYWRIGHT_BROWSERS_PATH": explicit}

    assert configure_playwright_browsers_path(environ, home=tmp_path) == explicit
    assert environ["PLAYWRIGHT_BROWSERS_PATH"] == explicit
