"""供既有 publisher tick 呼叫的 Pages 批次部署與公開正文驗證。"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

INTERVAL_SECONDS = 7200
VERIFY_TIMEOUT_SECONDS = 1800
RETRY_SECONDS = 60
MAX_ATTEMPTS = 3
KEYCHAIN_SERVICE = "com.pantheon.pages-deploy-hook"
KEYCHAIN_ACCOUNT = "production"
PUBLIC_ORIGIN = "https://www.mysticpantheon.com"


def body_digest(paragraphs: list[str]) -> str:
    normalized = [" ".join(value.split()) for value in paragraphs]
    if not normalized or any(not value for value in normalized):
        raise ValueError("public body is empty")
    return hashlib.sha256(json.dumps(normalized, ensure_ascii=False).encode()).hexdigest()


def public_url_valid(url: object) -> bool:
    if not isinstance(url, str):
        return False
    parsed = urlsplit(url)
    return (url.startswith(PUBLIC_ORIGIN + "/") and parsed.netloc == "www.mysticpantheon.com"
            and not parsed.query and not parsed.fragment
            and re.fullmatch(r"/(?:en/|ja/|ko/)?articles/[A-Za-z0-9_/-]+", parsed.path) is not None
            and ".." not in parsed.path)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def post_from_keychain() -> dict:
    """秘密僅在記憶體；不回傳原回應、例外字串或 URL。"""
    try:
        result = subprocess.run(
            ["/usr/bin/security", "find-generic-password", "-s", KEYCHAIN_SERVICE,
             "-a", KEYCHAIN_ACCOUNT, "-w"], capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return {"status": "FAILED", "error": "secret_unavailable"}
        secret = result.stdout.strip()
        parsed = urlsplit(secret)
        if (parsed.scheme != "https" or parsed.netloc != "api.cloudflare.com"
                or parsed.query or parsed.fragment
                or re.fullmatch(r"/client/v4/pages/webhooks/deploy_hooks/[A-Za-z0-9_-]+", parsed.path) is None):
            return {"status": "FAILED", "error": "secret_unavailable"}
    except Exception:
        return {"status": "FAILED", "error": "secret_unavailable"}
    try:
        with build_opener(_NoRedirect()).open(Request(secret, data=b"", method="POST"), timeout=5) as response:
            code = response.status
            return {"status": "ACCEPTED" if 200 <= code < 300 else "UNKNOWN", "http_status": code}
    except HTTPError as error:
        # 逾時、5xx 或轉址不能證明 POST 沒被接受；不得自動重送。
        return {"status": "FAILED" if 400 <= error.code < 500 and error.code != 408 else "UNKNOWN",
                "http_status": error.code}
    except Exception:
        return {"status": "UNKNOWN", "error": "post_outcome_unconfirmed"}


def verify_public_body(target: dict) -> dict:
    """使用明確指定的既有 Playwright Python；不安裝套件、不啟新服務。"""
    python = os.environ.get("PANTHEON_PUBLIC_PROBE_PYTHON", "")
    browser = os.environ.get("PANTHEON_PUBLIC_PROBE_BROWSER", "")
    if not _valid_target(target) or not all(Path(p).is_absolute() and os.access(p, os.X_OK) for p in (python, browser)):
        return {"visible": False}
    try:
        from scripts import pantheon_content_runtime_manifest as runtime_manifest
        child = subprocess.Popen(
            [python, "-m", "scripts.pantheon_pages_deploy", "verify"],
            cwd=Path(__file__).resolve().parents[1],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, start_new_session=True,
            **runtime_manifest.runtime_work_child_transport(),
        )
        try:
            stdout, _ = child.communicate(json.dumps(target), timeout=35)
        except subprocess.TimeoutExpired:
            # 清理這次驗證的瀏覽器程序群，不影響使用者既有瀏覽器。
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.communicate()
            return {"visible": False}
        evidence = json.loads(stdout) if child.returncode == 0 else {}
        return {key: evidence.get(key) for key in ("http_status", "visible", "body_sha256", "paragraph_count")}
    except Exception:
        return {"visible": False}


def _verify_rendered_body(target: dict) -> dict:
    """在既有瀏覽器子程序中驗渲染後可見正文（含翻譯 CSR）。"""
    if not public_url_valid(target.get("url")):
        return {"visible": False}
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True, timeout=5000,
                executable_path=os.environ["PANTHEON_PUBLIC_PROBE_BROWSER"])
            try:
                page = browser.new_page()
                response = page.goto(target["url"], wait_until="domcontentloaded", timeout=10000)
                page.locator("[data-article-body] p:visible").first.wait_for(timeout=5000)
                deadline = time.monotonic() + 5
                while True:
                    paragraphs = page.locator("[data-article-body] p:visible").all_inner_texts()
                    if body_digest(paragraphs) == target["body_sha256"] or time.monotonic() >= deadline:
                        break
                    time.sleep(0.25)
                return {"http_status": response.status if response else None,
                        "visible": page.url.rstrip("/") == target["url"].rstrip("/"),
                        "body_sha256": body_digest(paragraphs), "paragraph_count": len(paragraphs)}
            finally:
                browser.close()
    except Exception:
        return {"visible": False}


def _safe_response(outcome: object) -> dict:
    """只保留白名單欄位，連替身錯誤與平台 echo 都不能洩露秘密。"""
    if not isinstance(outcome, dict):
        return {"status": "UNKNOWN"}
    status = outcome.get("status")
    result = {"status": status if status in {"ACCEPTED", "FAILED", "UNKNOWN"} else "UNKNOWN"}
    if type(outcome.get("http_status")) is int and 100 <= outcome["http_status"] <= 599:
        result["http_status"] = outcome["http_status"]
    if outcome.get("error") == "secret_unavailable":
        result["error"] = "secret_unavailable"
    return result


def _valid_target(target: dict) -> bool:
    return (isinstance(target, dict)
            and set(target) == {"observed_remote_commit", "url", "body_sha256", "paragraph_count"}
            and isinstance(target["observed_remote_commit"], str)
            and re.fullmatch(r"[0-9a-f]{40}", target["observed_remote_commit"]) is not None
            and public_url_valid(target["url"])
            and isinstance(target["body_sha256"], str)
            and re.fullmatch(r"[0-9a-f]{64}", target["body_sha256"]) is not None
            and type(target["paragraph_count"]) is int and target["paragraph_count"] > 0)


def tick(
    path: Path, publication_id: str | None, snapshot: Callable[[], dict],
    write: Callable[[Path, object], None], *, post: Callable[[], dict] = post_from_keychain,
    verify: Callable[[dict], dict] = verify_public_body, now: float | None = None,
) -> dict:
    """呼叫者持有現有 publisher 鎖；每 tick 最多一次 POST 或一次驗證。"""
    now = time.time() if now is None else now
    try:
        if path.is_symlink():
            raise ValueError("untrusted state")
        state = json.loads(path.read_text()) if path.exists() else {}
        if not isinstance(state, dict):
            raise ValueError("invalid state")
        attempt = state.get("attempt", {})
        if not isinstance(attempt, dict):
            raise ValueError("invalid attempt")
        if attempt and (attempt.get("status") not in {"TRIGGERING", "FAILED", "ACCEPTED", "VERIFIED", "UNKNOWN", "EXHAUSTED", "TIMED_OUT"}
                        or type(attempt.get("attempts")) is not int
                        or not 1 <= attempt["attempts"] <= MAX_ATTEMPTS
                        or type(attempt.get("attempted_epoch")) not in (int, float)
                        or not math.isfinite(attempt["attempted_epoch"])
                        or not isinstance(attempt.get("response", {}), dict)
                        or not isinstance(attempt.get("publication_id"), str)):
            raise ValueError("invalid attempt fields")
        for source, fields in ((state, ("last_triggered_epoch",)),
                               (attempt, ("last_probe_epoch", "deadline_epoch"))):
            for field in fields:
                if field in source and (type(source[field]) not in (int, float)
                                        or not math.isfinite(source[field]) or source[field] < 0):
                    raise ValueError("invalid clock field")
        if "verified_publication" in state and not isinstance(state["verified_publication"], str):
            raise ValueError("invalid publication identity")
        if attempt and now < attempt["attempted_epoch"]:
            raise ValueError("clock moved backwards")
    except (OSError, ValueError, TypeError):
        return {"status": "OPERATOR_REQUIRED", "reason": "pages_state_invalid"}

    def save() -> None:
        write(path, state)

    def stop(reason: str) -> dict:
        return {"status": "OPERATOR_REQUIRED", "reason": reason}

    status = attempt.get("status")
    if status == "TRIGGERING":
        attempt["status"] = "UNKNOWN"
        save()
        return stop("pages_hook_outcome_unknown")
    if status in {"UNKNOWN", "EXHAUSTED", "TIMED_OUT"}:
        return stop({"UNKNOWN": "pages_hook_outcome_unknown", "EXHAUSTED": "pages_hook_attempts_exhausted",
                     "TIMED_OUT": "pages_public_verification_timeout"}[status])
    if status == "ACCEPTED":
        if not _valid_target(attempt.get("target")) or type(attempt.get("deadline_epoch")) not in (int, float):
            return stop("pages_state_invalid")
        if now - attempt.get("last_probe_epoch", 0) < RETRY_SECONDS:
            return {"status": "WAITING_PUBLIC"}
        try:
            evidence = verify(attempt["target"])
        except Exception:
            evidence = {}
        evidence = evidence if isinstance(evidence, dict) else {}
        target = attempt["target"]
        matched = (evidence.get("http_status") == 200 and evidence.get("visible") is True
                   and evidence.get("body_sha256") == target["body_sha256"]
                   and evidence.get("paragraph_count") == target["paragraph_count"])
        attempt["last_probe_epoch"] = now
        attempt["last_probe"] = {"matched": matched, "http_200": evidence.get("http_status") == 200}
        if matched:
            attempt["status"] = "VERIFIED"
            state["verified_publication"] = attempt["publication_id"]
            attempt["verified_epoch"] = now
        elif now >= attempt["deadline_epoch"]:
            attempt["status"] = "TIMED_OUT"
        save()
        return (stop("pages_public_verification_timeout") if attempt["status"] == "TIMED_OUT"
                else {"status": "PUBLIC_BODY_VERIFIED" if matched else "WAITING_PUBLIC"})
    if not publication_id or state.get("verified_publication") == publication_id:
        return {"status": "idle"}
    if status == "FAILED":
        if attempt.get("response", {}).get("error") == "secret_unavailable":
            return stop("pages_hook_secret_unavailable")
        if attempt["attempts"] >= MAX_ATTEMPTS:
            return stop("pages_hook_attempts_exhausted")
        if now - attempt["attempted_epoch"] < RETRY_SECONDS:
            return {"status": "RETRY_WAIT"}
        count = attempt["attempts"] + 1
    else:
        last = state.get("last_triggered_epoch")
        if last is not None and (type(last) not in (int, float) or now < last):
            return stop("pages_state_invalid")
        if last is not None and now - last < INTERVAL_SECONDS:
            return {"status": "INTERVAL_WAIT"}
        count = 1
    try:
        target = snapshot()
        if not _valid_target(target):
            raise ValueError("invalid snapshot")
    except Exception:
        # 尚未 POST，留下失敗次數；不保存可能含敏感資訊的例外。
        state["attempt"] = {"status": "EXHAUSTED" if count >= MAX_ATTEMPTS else "FAILED",
                            "publication_id": publication_id, "attempts": count,
                            "attempted_epoch": now, "response": {"status": "FAILED"}}
        save()
        return stop("pages_hook_attempts_exhausted") if count >= MAX_ATTEMPTS else {"status": "FAILED"}
    attempt = {"status": "TRIGGERING", "publication_id": publication_id, "target": target,
               "attempts": count, "attempted_epoch": now}
    state["attempt"] = attempt
    state["last_triggered_epoch"] = now
    save()  # 未落盤不得 POST；中途死亡只會留下 UNKNOWN，不盲目重送。
    try:
        outcome = _safe_response(post())
    except Exception:
        outcome = {"status": "UNKNOWN"}
    attempt["response"] = outcome
    attempt["status"] = outcome["status"]
    if outcome["status"] == "ACCEPTED":
        attempt["deadline_epoch"] = now + VERIFY_TIMEOUT_SECONDS
    elif outcome["status"] == "FAILED" and count >= MAX_ATTEMPTS:
        attempt["status"] = "EXHAUSTED"
    save()
    if outcome.get("error") == "secret_unavailable":
        return stop("pages_hook_secret_unavailable")
    if attempt["status"] in {"UNKNOWN", "EXHAUSTED"}:
        return stop("pages_hook_outcome_unknown" if attempt["status"] == "UNKNOWN" else "pages_hook_attempts_exhausted")
    return {"status": attempt["status"]}


if __name__ == "__main__":
    if sys.argv[1:] != ["verify"]:
        raise SystemExit(2)
    try:
        target = json.loads(sys.stdin.read(16384))
        result = _verify_rendered_body(target) if _valid_target(target) else {"visible": False}
    except Exception:
        result = {"visible": False}
    print(json.dumps(result))
