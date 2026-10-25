from __future__ import annotations

import json
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path
from urllib.error import HTTPError

import pytest

from scripts import pantheon_pages_deploy as pages
from scripts import agy_content_publisher as publisher


def target():
    return {"observed_remote_commit": "a" * 40,
            "url": pages.PUBLIC_ORIGIN + "/articles/astrology/test-one",
            "body_sha256": pages.body_digest(["這是核准的正文。"]), "paragraph_count": 1}


def fixture(tmp_path):
    path = tmp_path / "pages-deployment.json"
    calls = []
    def post():
        calls.append("POST")
        return {"status": "ACCEPTED", "http_status": 200}
    def verify(t):
        calls.append("GET")
        return {"http_status": 200, "visible": True, "body_sha256": t["body_sha256"],
                "paragraph_count": t["paragraph_count"]}
    def tick(pub="first", now=10000, **kwargs):
        return pages.tick(path, pub, target, publisher._atomic_write_json,
                          post=kwargs.get("post", post), verify=kwargs.get("verify", verify), now=now)
    return path, calls, tick


def test_interval_pending_and_idle_use_exactly_one_build(tmp_path):
    path, calls, tick = fixture(tmp_path)
    assert tick(None)["status"] == "idle"
    assert calls == [] and not path.exists()
    assert tick()["status"] == "ACCEPTED"
    assert tick(now=10001)["status"] == "PUBLIC_BODY_VERIFIED"
    assert tick(now=20000)["status"] == "idle"
    assert tick("second", 17199)["status"] == "INTERVAL_WAIT"
    assert calls == ["POST", "GET"]
    assert tick("second", 17200)["status"] == "ACCEPTED"
    saved = json.loads(path.read_text())
    assert saved["attempt"]["target"]["observed_remote_commit"] == "a" * 40
    assert saved["verified_publication"] == "first"
    assert calls == ["POST", "GET", "POST"]


def test_known_failure_retries_bounded_and_never_reports_public(tmp_path):
    path, calls, tick = fixture(tmp_path)
    def fail():
        calls.append("failed")
        return {"status": "FAILED", "http_status": 429}
    assert tick(post=fail)["status"] == "FAILED"
    assert tick(now=10059, post=fail)["status"] == "RETRY_WAIT"
    assert tick(now=10060, post=fail)["status"] == "FAILED"
    assert tick(now=10120, post=fail)["status"] == "OPERATOR_REQUIRED"
    assert tick(now=20000, post=fail)["status"] == "OPERATOR_REQUIRED"
    assert calls == ["failed"] * 3
    assert "verified_publication" not in json.loads(path.read_text())


@pytest.mark.parametrize("mode", ["unknown", "exception", "interrupted"])
def test_unknown_post_never_blindly_repeats(tmp_path, mode):
    path, calls, tick = fixture(tmp_path)
    def unknown():
        calls.append("POST")
        if mode == "exception":
            raise RuntimeError("unconfirmed")
        return {"status": "UNKNOWN"}
    if mode == "interrupted":
        path.write_text(json.dumps({"attempt": {"status": "TRIGGERING", "attempts": 1,
                        "attempted_epoch": 9000, "publication_id": "first"}}))
    assert tick(post=unknown)["reason"] == "pages_hook_outcome_unknown"
    before = list(calls)
    assert tick(now=20000, post=unknown)["status"] == "OPERATOR_REQUIRED"
    assert calls == before


def test_missing_secret_alerts_without_claiming_sent(tmp_path):
    path, calls, tick = fixture(tmp_path)
    result = tick(post=lambda: {"status": "FAILED", "error": "secret_unavailable"})
    assert result["reason"] == "pages_hook_secret_unavailable"
    assert json.loads(path.read_text())["attempt"]["status"] == "FAILED"
    assert calls == []


@pytest.mark.parametrize("probe", [{"http_status": 404},
                                   {"http_status": 200, "visible": True, "body_sha256": "old", "paragraph_count": 1},
                                   {"http_status": 200, "visible": False, "body_sha256": target()["body_sha256"], "paragraph_count": 1}])
def test_public_timeout_including_old_or_hidden_body_is_operator_required(tmp_path, probe):
    path, calls, tick = fixture(tmp_path)
    tick()
    assert tick(now=10060, verify=lambda _: probe)["status"] == "WAITING_PUBLIC"
    assert tick(now=11800, verify=lambda _: probe)["reason"] == "pages_public_verification_timeout"
    assert json.loads(path.read_text())["attempt"]["status"] == "TIMED_OUT"
    assert calls == ["POST"]


def test_echoed_secret_is_not_saved_or_returned(tmp_path, capsys):
    path, _calls, tick = fixture(tmp_path)
    secret = "/".join(["https:/", "api.cloudflare.com", "client/v4/pages/webhooks/deploy_hooks", "test-secret-token"])
    result = tick(post=lambda: {"status": "FAILED", "http_status": 403,
                               "url": secret, "error": secret, "body": secret})
    assert secret not in path.read_text() + json.dumps(result) + str(capsys.readouterr())
    assert "test-secret-token" not in path.read_text()


@pytest.mark.parametrize("code,status", [(200, "ACCEPTED"), (403, "FAILED"), (429, "FAILED"),
                                         (408, "UNKNOWN"), (500, "UNKNOWN"), (302, "UNKNOWN")])
def test_keychain_adapter_preserves_only_safe_http_outcome(monkeypatch, code, status):
    secret = "/".join(["https:/", "api.cloudflare.com", "client/v4/pages/webhooks/deploy_hooks", "test-secret-token"])
    seen = []
    def keychain(command, **kwargs):
        assert command[:2] == ["/usr/bin/security", "find-generic-password"]
        return subprocess.CompletedProcess(command, 0, secret, "")
    class Response:
        status = code
        def __enter__(self): return self
        def __exit__(self, *_): pass
    class Opener:
        def open(self, request, timeout):
            seen.append((request.full_url, request.method, timeout))
            if code >= 300:
                raise HTTPError(secret, code, secret, {}, None)
            return Response()
    monkeypatch.setattr(pages.subprocess, "run", keychain)
    monkeypatch.setattr(pages, "build_opener", lambda *_: Opener())
    result = pages.post_from_keychain()
    assert result == {"status": status, "http_status": code}
    assert seen == [(secret, "POST", 5)]
    assert secret not in json.dumps(result)


def test_keychain_unavailable_never_opens_network(monkeypatch):
    monkeypatch.setattr(pages.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 1, "", ""))
    monkeypatch.setattr(pages, "build_opener", lambda *_: pytest.fail("network must not be opened"))
    assert pages.post_from_keychain() == {"status": "FAILED", "error": "secret_unavailable"}


def test_write_failure_before_post_does_not_trigger(tmp_path):
    calls = []
    def fail_write(*_): raise OSError("disk full")
    with pytest.raises(OSError):
        pages.tick(tmp_path / "state", "first", target, fail_write,
                   post=lambda: calls.append("POST"), now=10000)
    assert calls == []


@pytest.mark.parametrize("lane", ["new", "rewrite", "i18n-new", "i18n-rewrite"])
def test_snapshot_binds_remote_and_correct_locale_body(tmp_path, monkeypatch, lane):
    entry = {"commit_sha": "a" * 40, "article_ids": ["id"]}
    monkeypatch.setattr(publisher.pipeline, "_existing_rewrite_inventory", lambda _: {
        "id": {"canonicalPath": "/articles/astrology/test", "currentBody": [{"paragraphs": ["正文"]}]}})
    monkeypatch.setattr(publisher.multilingual, "_locale_inventory", lambda _: [
        {"articleId": "id", "locale": "ja", "sourcePath": "/articles/astrology/test",
         "bodySections": [{"paragraphs": ["日本語の本文"]}]}])
    if lane.startswith("i18n"):
        entry.update(article_id="id", locale="ja")
    def git(_repo, args, _input):
        if args[0] == "ls-remote": return "a" * 40 + "\trefs/heads/main"
        if args[0] == "rev-parse": return "a" * 40
        assert args == ["merge-base", "--is-ancestor", "a" * 40, "a" * 40]
        return ""
    snapshot = publisher._pages_snapshot(tmp_path, entry, git)
    assert snapshot["url"] == pages.PUBLIC_ORIGIN + ("/ja" if lane.startswith("i18n") else "") + "/articles/astrology/test"
    assert snapshot["body_sha256"] == pages.body_digest(["日本語の本文" if lane.startswith("i18n") else "正文"])


def test_rendered_verifier_waits_for_client_side_body(monkeypatch):
    sample = target()
    calls = []
    class Locator:
        @property
        def first(self): return self
        def wait_for(self, **kwargs): pass
        def all_inner_texts(self):
            calls.append("DOM")
            return ["placeholder"] if len(calls) == 1 else ["這是核准的正文。"]
    class Page:
        url = sample["url"]
        def goto(self, url, **kwargs): return SimpleNamespace(status=200)
        def locator(self, selector):
            assert selector == "[data-article-body] p:visible"
            return Locator()
    class Browser:
        def new_page(self): return Page()
        def close(self): pass
    class Runtime:
        chromium = SimpleNamespace(launch=lambda **kwargs: Browser())
        def __enter__(self): return self
        def __exit__(self, *_): pass
    monkeypatch.setitem(sys.modules, "playwright.sync_api",
                        SimpleNamespace(sync_playwright=lambda: Runtime()))
    monkeypatch.setattr(pages.time, "sleep", lambda _: None)
    monkeypatch.setenv("PANTHEON_PUBLIC_PROBE_BROWSER", "/fake/chrome")
    result = pages._verify_rendered_body(sample)
    assert result["http_status"] == 200 and result["visible"] is True
    assert result["body_sha256"] == sample["body_sha256"]
    assert calls == ["DOM", "DOM"]


def test_pages_cli_cannot_be_enabled_for_unbounded_publisher(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["publisher", "--pages-deploy"])
    with pytest.raises(SystemExit, match="requires continuous tick"):
        publisher.main.__wrapped__()


@pytest.mark.parametrize("failure", [None, "timeout", "bad_json", "exit"])
def test_public_probe_uses_explicit_existing_runtime_and_bounded_child(monkeypatch, failure):
    monkeypatch.setenv("PANTHEON_PUBLIC_PROBE_PYTHON", sys.executable)
    monkeypatch.setenv("PANTHEON_PUBLIC_PROBE_BROWSER", sys.executable)
    killed = []
    monkeypatch.setattr(pages.os, "killpg", lambda pid, sig: killed.append(pid))
    def popen(command, **kwargs):
        assert command == [sys.executable, "-m", "scripts.pantheon_pages_deploy", "verify"]
        assert kwargs["start_new_session"] is True
        assert kwargs["cwd"] == Path(pages.__file__).resolve().parents[1]
        class Child:
            pid = 12345
            returncode = 1 if failure == "exit" else 0
            def communicate(self, data=None, timeout=None):
                if data is None:
                    assert failure == "timeout" and killed == [self.pid]
                    return "", ""
                assert timeout == 35 and json.loads(data) == target()
                if failure == "timeout":
                    raise subprocess.TimeoutExpired(command, 35)
                result = {"visible": True, "http_status": 200, "body_sha256": target()["body_sha256"],
                          "paragraph_count": 1, "untrusted_extra": "drop"}
                return ("bad" if failure == "bad_json" else json.dumps(result)), ""
        return Child()
    monkeypatch.setattr(pages.subprocess, "Popen", popen)
    result = pages.verify_public_body(target())
    assert (result.get("visible") is True) == (failure is None)
    assert "untrusted_extra" not in result


def test_public_probe_missing_runtime_does_not_spawn(monkeypatch):
    monkeypatch.delenv("PANTHEON_PUBLIC_PROBE_PYTHON", raising=False)
    monkeypatch.setattr(pages.subprocess, "Popen", lambda *a, **k: pytest.fail("must not spawn"))
    assert pages.verify_public_body(target()) == {"visible": False}


def test_snapshot_rejects_checkout_differing_from_remote_before_reading_body(tmp_path, monkeypatch):
    def git(root, args, data):
        if args[0] == "ls-remote": return "a" * 40 + "\trefs/heads/main"
        if args[0] == "rev-parse": return "b" * 40
        pytest.fail("must stop before body lookup or any mutation")
    monkeypatch.setattr(publisher.pipeline, "_existing_rewrite_inventory", lambda *_: pytest.fail("stale body"))
    with pytest.raises(publisher.PublishBlocked, match="remote snapshot changed"):
        publisher._pages_snapshot(tmp_path, {"commit_sha": "a" * 40, "article_ids": ["id"]}, git)


@pytest.mark.parametrize("field,value", [("deadline_epoch", float("nan")), ("last_probe_epoch", "bad"),
                                         ("deadline_epoch", float("inf"))])
def test_corrupt_clock_fields_block_without_post_or_probe(tmp_path, field, value):
    path = tmp_path / "state"
    state = {"attempt": {"status": "ACCEPTED", "attempts": 1, "attempted_epoch": 1,
                         "publication_id": "one", "target": target(), "deadline_epoch": 10}}
    state["attempt"][field] = value
    path.write_text(json.dumps(state))
    result = pages.tick(path, "one", target, lambda *_: None, now=100,
        post=lambda: pytest.fail("must not post"), verify=lambda _: pytest.fail("must not probe"))
    assert result == {"status": "OPERATOR_REQUIRED", "reason": "pages_state_invalid"}
