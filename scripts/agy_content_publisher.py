#!/usr/bin/env python3
"""發布已通過 Gemini Reviewer 的文章 run。"""

from __future__ import annotations

import argparse
from datetime import date, datetime
import fcntl
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable

from scripts import agy_seo_copy_pipeline as pipeline


SCHEMA_VERSION = 1
DEFAULT_MAX_RUNS = 1
PUBLISHER_ID = "agy-content-publisher"
GitRunner = Callable[[Path, list[str], str | None], str]
TEST_COMMAND = [sys.executable, "-m", "pytest", "tests/test_web.py", "tests/test_agy_seo_copy_pipeline.py", "tests/test_release_record.py", "-q"]


class PublishBlocked(ValueError):
    """發布 gate fail-closed。"""


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    pipeline.write_json(path, payload)


def run_git(repo_root: Path, args: list[str], input_text: str | None = None) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        input=input_text,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repo_clean(repo_root: Path, git: GitRunner = run_git) -> bool:
    return git(repo_root, ["status", "--porcelain"], None) == ""


def _assert_clean_origin_head(repo_root: Path, git: GitRunner = run_git) -> str:
    git(repo_root, ["fetch", "origin", "main"], None)
    if not _repo_clean(repo_root, git):
        raise PublishBlocked("repo worktree is not clean")
    local = git(repo_root, ["rev-parse", "HEAD"], None)
    remote = git(repo_root, ["rev-parse", "origin/main"], None)
    if local != remote:
        raise PublishBlocked(f"local HEAD differs from origin/main: {local[:12]} != {remote[:12]}")
    return local


def _run_files(queue_root: Path) -> list[Path]:
    runs_dir = queue_root / "runs"
    if not runs_dir.exists():
        return []
    return sorted(runs_dir.glob("*.json"), key=lambda path: path.name)


def _ledger_path(state_root: Path) -> Path:
    return state_root / "ledger.json"


def _load_ledger(state_root: Path) -> dict[str, Any]:
    path = _ledger_path(state_root)
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "published_runs": [], "quarantined_runs": [], "rewrite_released_runs": []}
    ledger = _read_json(path)
    if ledger.get("schema_version") != SCHEMA_VERSION:
        raise PublishBlocked("publisher ledger schema is invalid")
    ledger.setdefault("published_runs", [])
    ledger.setdefault("quarantined_runs", [])
    ledger.setdefault("rewrite_released_runs", [])
    return ledger


def _record_quarantine(state_root: Path, state: dict[str, Any], reason: str) -> None:
    ledger = _load_ledger(state_root)
    existing = {str(item.get("run_id")) for item in ledger["quarantined_runs"]}
    run_id = str(state.get("run_id") or "")
    if run_id and run_id not in existing:
        ledger["quarantined_runs"].append({"run_id": run_id, "reason": reason, "recorded_at": _now()})
        _write_json(_ledger_path(state_root), ledger)


def _load_completed_run(state_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    state = _read_json(state_path)
    if state.get("schema_version") != SCHEMA_VERSION or state.get("status") != "complete":
        raise PublishBlocked("run state is not complete")
    run_dir = Path(str(state.get("run_dir") or ""))
    result = state.get("result") if isinstance(state.get("result"), dict) else {}
    candidate_path = Path(str(result.get("candidate") or run_dir / "candidate.json"))
    review_path = run_dir / "review.json"
    if not candidate_path.is_file() or not review_path.is_file():
        raise PublishBlocked("candidate or review json is missing")
    candidate = _read_json(candidate_path)
    review = _read_json(review_path)
    if candidate.get("run_id") != state.get("run_id") or review.get("run_id") != state.get("run_id"):
        raise PublishBlocked("run id drift between state, candidate, and review")
    pipeline.validate_candidate(candidate)
    pipeline.validate_review(review, candidate["articles"])
    return state, candidate, review


def _review_is_clean_approve(review: dict[str, Any]) -> bool:
    for item in review["articles"]:
        if item.get("verdict") != "APPROVE" or item.get("hard_failure") is True:
            return False
        if item.get("findings"):
            return False
    return True


def _article_path(article: dict[str, Any]) -> str:
    category = str(article["serial"]).rsplit("-", 1)[0]
    return f"/articles/{category}/{article['urlSlug']}"


def _assert_batch_unique(candidates: list[dict[str, Any]]) -> None:
    ids: set[str] = set()
    paths: set[str] = set()
    paragraph_owners: dict[str, str] = {}
    for candidate in candidates:
        for article in candidate["articles"]:
            article_id = str(article["id"])
            path = _article_path(article)
            if article_id in ids:
                raise PublishBlocked(f"duplicate article id in publish batch: {article_id}")
            if path in paths:
                raise PublishBlocked(f"duplicate article path in publish batch: {path}")
            ids.add(article_id)
            paths.add(path)
            for section in article["bodySections"]:
                for paragraph in section["paragraphs"]:
                    normalized = re.sub(r"\s+", "", str(paragraph))
                    if len(normalized) < 40:
                        continue
                    owner = paragraph_owners.get(normalized)
                    if owner and owner != article_id:
                        raise PublishBlocked(f"duplicate paragraph across batch: {owner} and {article_id}")
                    paragraph_owners[normalized] = article_id


def collect_ready_runs(queue_root: Path, state_root: Path, *, limit: int = DEFAULT_MAX_RUNS) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    ledger = _load_ledger(state_root)
    published = {str(item.get("run_id")) for item in ledger["published_runs"]}
    quarantined = {str(item.get("run_id")) for item in ledger["quarantined_runs"]}
    ready: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    for state_path in _run_files(queue_root):
        try:
            state, candidate, review = _load_completed_run(state_path)
        except PublishBlocked:
            continue
        run_id = str(state["run_id"])
        if run_id in published or run_id in quarantined:
            continue
        if candidate.get("mode") != "create":
            _record_quarantine(state_root, state, "publisher only supports create mode")
            continue
        if not _review_is_clean_approve(review):
            _record_quarantine(state_root, state, "reviewer did not cleanly approve every article")
            continue
        findings = pipeline.quality_findings(candidate["articles"])
        if findings:
            _record_quarantine(state_root, state, f"deterministic findings: {len(findings)}")
            continue
        ready.append((state, candidate, review))
        if len(ready) >= limit:
            break
    _assert_batch_unique([candidate for _, candidate, _ in ready])
    return ready


def _load_rewrite_brief(run_dir: Path, run_id: str) -> dict[str, Any]:
    brief_path = run_dir / "brief.json"
    if not brief_path.is_file():
        raise PublishBlocked(f"rewrite brief is missing for {run_id}")
    brief = _read_json(brief_path)
    if brief.get("run_id") != run_id:
        raise PublishBlocked(f"rewrite brief run id drift for {run_id}")
    pipeline.validate_rewrite_brief(brief)
    return brief


def _rewrite_findings_for_run(candidate: dict[str, Any], brief: dict[str, Any]) -> list[dict[str, str]]:
    quality, uniqueness = pipeline.rewrite_aggregate_findings(brief, candidate["articles"])
    return [*quality, *uniqueness]


def collect_ready_rewrite_runs(
    queue_root: Path,
    state_root: Path,
    *,
    limit: int = DEFAULT_MAX_RUNS,
) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]]:
    ledger = _load_ledger(state_root)
    released = {str(item.get("run_id")) for item in ledger["rewrite_released_runs"]}
    ready: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    seen_article_ids: set[str] = set()
    seen_body_hashes: dict[str, str] = {}
    for state_path in _run_files(queue_root):
        try:
            state, candidate, review = _load_completed_run(state_path)
        except PublishBlocked:
            continue
        run_id = str(state["run_id"])
        if run_id in released or candidate.get("mode") != "rewrite_existing_body":
            continue
        if not _review_is_clean_approve(review):
            continue
        run_dir = Path(str(state["run_dir"]))
        brief = _load_rewrite_brief(run_dir, run_id)
        findings = _rewrite_findings_for_run(candidate, brief)
        if findings:
            continue
        for article in candidate["articles"]:
            article_id = str(article["article_id"])
            if article_id in seen_article_ids:
                raise PublishBlocked(f"duplicate rewrite article id in release batch: {article_id}")
            body_hash = pipeline.body_sha256(article["bodySections"])
            owner = seen_body_hashes.get(body_hash)
            if owner:
                raise PublishBlocked(f"duplicate rewrite body across batch: {owner} and {article_id}")
            seen_article_ids.add(article_id)
            seen_body_hashes[body_hash] = article_id
        ready.append((state, candidate, review, brief))
        if len(ready) >= limit:
            break
    return ready


def _current_version(repo_root: Path) -> tuple[int, int, int]:
    pyproject = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "(\d+)\.(\d+)\.(\d+)"$', pyproject, flags=re.MULTILINE)
    if not match:
        raise PublishBlocked("pyproject version is missing")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def _bump_patch_version(repo_root: Path) -> str:
    major, minor, patch = _current_version(repo_root)
    version = f"{major}.{minor}.{patch + 1}"
    pyproject = repo_root / "pyproject.toml"
    package = repo_root / "package.json"
    pyproject.write_text(
        re.sub(r'^version = "\d+\.\d+\.\d+"$', f'version = "{version}"', pyproject.read_text(encoding="utf-8"), flags=re.MULTILINE),
        encoding="utf-8",
    )
    package_payload = json.loads(package.read_text(encoding="utf-8"))
    package_payload["version"] = version
    package.write_text(json.dumps(package_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return version


def _public_article_count(repo_root: Path) -> int:
    return len(pipeline._registry_inventory(repo_root))


def _prepend_changelog(repo_root: Path, *, version: str, article_count: int, run_ids: list[str], evidence_path: str) -> None:
    changelog = repo_root / "CHANGELOG.md"
    body = changelog.read_text(encoding="utf-8")
    today = date.today().isoformat()
    section = "\n".join(
        [
            f"## [{version}] - {today}",
            "",
            f"- Release tag：`v{version}`",
            f"- 公開文章總數：{article_count}",
            f"- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 {len(run_ids)} 個 run；run_id：{', '.join(run_ids)}。",
            "- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。",
            f"- 證據：`{evidence_path}`",
            "",
        ]
    )
    changelog.write_text(body.replace("\n## [", "\n" + section + "\n## [", 1), encoding="utf-8")


def _prepend_rewrite_changelog(repo_root: Path, *, version: str, article_count: int, run_ids: list[str], article_ids: list[str], evidence_path: str) -> None:
    changelog = repo_root / "CHANGELOG.md"
    body = changelog.read_text(encoding="utf-8")
    today = date.today().isoformat()
    section = "\n".join(
        [
            f"## [{version}] - {today}",
            "",
            f"- Release tag：`v{version}`",
            f"- 公開文章總數：{article_count}（舊文重寫，不新增 registry 條目）",
            f"- 發布範圍：套用 Gemini Reviewer APPROVE 且 deterministic gate 通過的舊文 body override {len(article_ids)} 篇；run_id：{', '.join(run_ids)}。",
            "- 驗證：publisher clean-origin gate、Reviewer hash gate、rewrite deterministic gate、source body drift gate、focused article pipeline tests 與 release record gate。",
            f"- 證據：`{evidence_path}`",
            "",
        ]
    )
    changelog.write_text(body.replace("\n## [", "\n" + section + "\n## [", 1), encoding="utf-8")


def _sync_web_test_release_fixture(repo_root: Path, *, cache_token: str, articles: list[dict[str, Any]]) -> Path:
    test_path = repo_root / "tests/test_web.py"
    text = test_path.read_text(encoding="utf-8")
    text = re.sub(r'ARTICLE_CACHE_TOKEN = "[^"]+"', f'ARTICLE_CACHE_TOKEN = "{cache_token}"', text, count=1)
    paths = [_article_path(article) for article in articles]
    marker = "DAILY_PUBLIC_ARTICLE_PATHS = [\n"
    start = text.index(marker) + len(marker)
    end = text.index("]\n\nPUBLIC_ARTICLE_PATHS", start)
    block = text[start:end]
    for path in paths:
        line = f'    "{path}",\n'
        if line not in block:
            block += line
    text = text[:start] + block + text[end:]
    if (repo_root / "app/web/static/articles.js").exists():
        records = _hub_display_records(repo_root)
        category_list = _python_string_list([str(record["category"]) for record in records])
        path_list = _python_string_list([str(record["path"]) for record in records])
        pattern = re.compile(
            r'assert \[record\["category"\] for record in data\["records"\]\] == \[\n.*?\n    \]\n'
            r'    assert \[record\["path"\] for record in data\["records"\]\] == \[\n.*?\n    \]',
            flags=re.DOTALL,
        )
        replacement = (
            'assert [record["category"] for record in data["records"]] == [\n'
            f"{category_list}\n"
            "    ]\n"
            '    assert [record["path"] for record in data["records"]] == [\n'
            f"{path_list}\n"
            "    ]"
        )
        text, replaced = pattern.subn(replacement, text, count=1)
        if replaced != 1:
            raise PublishBlocked("test_web hub display fixture marker not found")
    test_path.write_text(text, encoding="utf-8")
    return test_path


def _python_string_list(values: list[str]) -> str:
    return "\n".join(f'        "{value}",' for value in values)


def _hub_display_records(repo_root: Path) -> list[dict[str, str]]:
    script = """
import { getArticlePath, listArticleRecords } from "./app/web/static/article-registry.js";
import { pickLatestArticles } from "./app/web/static/articles.js";
const selected = pickLatestArticles(listArticleRecords());
console.log(JSON.stringify(selected.map((article) => ({
  path: getArticlePath(article),
  category: article.articleCategory,
}))));
"""
    result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=repo_root, check=True, capture_output=True, text=True)
    return list(json.loads(result.stdout))


def _run_prerender(repo_root: Path) -> None:
    _run_checked(repo_root, [sys.executable, "scripts/prerender_article_shells.py"])


def _run_feed(repo_root: Path) -> None:
    _run_checked(repo_root, [sys.executable, "scripts/generate_feed.py"])


def _run_checked(repo_root: Path, args: list[str]) -> None:
    subprocess.run(args, cwd=repo_root, check=True)


def _stage_commit_tag_push(
    repo_root: Path,
    version: str,
    git: GitRunner = run_git,
    *,
    push: bool,
    release_gate: bool,
    message: str | None = None,
) -> str:
    git(repo_root, ["add", "app/web", "tests/test_web.py", "pyproject.toml", "package.json", "CHANGELOG.md"], None)
    git(repo_root, ["commit", "-m", message or f"chore(content): publish Gemini approved articles v{version}"], None)
    git(repo_root, ["tag", "-a", f"v{version}", "-m", f"Pantheon content release v{version}"], None)
    commit_sha = git(repo_root, ["rev-parse", "HEAD"], None)
    if release_gate:
        _run_checked(repo_root, [sys.executable, "scripts/check_release_record.py", "--base-ref", "origin/main", "--require-head-tag"])
    if push:
        git(repo_root, ["push", "origin", "HEAD:main", f"v{version}"], None)
    return commit_sha


def _rewrite_identity_for_inventory_item(item: dict[str, Any]) -> dict[str, str]:
    record = item["record"]
    return {
        "id": str(record["id"]),
        "product": str(record["product"]),
        "category": str(record["articleCategory"]),
        "serial": str(record["serial"]),
        "slug": str(record["urlSlug"]),
        "primaryKeyword": str(record["primaryKeyword"]),
        "title": str(record["title"]),
    }


def _assert_rewrite_source_matches(repo_root: Path, candidates: list[dict[str, Any]]) -> None:
    inventory = pipeline._existing_rewrite_inventory(repo_root)
    for candidate in candidates:
        for article in candidate["articles"]:
            article_id = str(article["article_id"])
            current = inventory.get(article_id)
            if current is None:
                raise PublishBlocked(f"rewrite source article no longer exists: {article_id}")
            if article["identity"] != _rewrite_identity_for_inventory_item(current):
                raise PublishBlocked(f"rewrite identity drift for {article_id}")
            actual_hash = pipeline.body_sha256(current["currentBody"])
            approved_hash = pipeline.body_sha256(article["bodySections"])
            if actual_hash not in {str(article["current_body_sha256"]), approved_hash}:
                raise PublishBlocked(f"rewrite body drift for {article_id}")


def _update_rewrite_body_override_lookup(meta_path: Path, export_name: str) -> None:
    text = meta_path.read_text(encoding="utf-8")
    pattern = re.compile(r"(?m)^(\s*const customBody = )(.+?);$")
    match = pattern.search(text)
    if not match:
        raise PublishBlocked("article-meta customBody lookup marker not found")
    expression = match.group(2)
    token = f"{export_name}[article.slug]"
    if token in expression:
        return
    updated_expression = f"{token} || {expression}"
    text = text[: match.start(2)] + updated_expression + text[match.end(2) :]
    meta_path.write_text(text, encoding="utf-8")


def apply_rewrite_release(repo_root: Path, release_id: str, candidates: list[dict[str, Any]]) -> list[Path]:
    if not candidates:
        return []
    _assert_rewrite_source_matches(repo_root, candidates)
    file_slug, identifier = pipeline._safe_identifier(release_id)
    export_name = f"AGY_{identifier}_REWRITE_BODY_OVERRIDES"
    module = repo_root / "app/web/static" / f"article-rewrite-{file_slug}.js"
    bodies: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        for article in candidate["articles"]:
            slug = str(article["identity"]["slug"])
            if slug in bodies:
                raise PublishBlocked(f"duplicate rewrite slug in release batch: {slug}")
            bodies[slug] = article["bodySections"]
    module.write_text(
        f"export const {export_name} = {json.dumps(bodies, ensure_ascii=False, indent=2)};\n",
        encoding="utf-8",
    )
    meta_path = repo_root / "app/web/static/article-meta.js"
    import_line = f'import {{ {export_name} }} from "./{module.name}?v={release_id}";\n'
    meta = meta_path.read_text(encoding="utf-8")
    meta = pipeline._insert_once(meta, "const ARTICLE_BODY_LIBRARY = {", import_line + "\n")
    meta_path.write_text(meta, encoding="utf-8")
    _update_rewrite_body_override_lookup(meta_path, export_name)
    changed = [module, meta_path]
    changed.extend(pipeline._bump_article_cache_queries(repo_root, release_id))
    return changed


def publish_ready_runs(
    repo_root: Path,
    queue_root: Path,
    state_root: Path,
    *,
    max_runs: int = DEFAULT_MAX_RUNS,
    dry_run: bool = False,
    push: bool = False,
    run_tests: bool = True,
    release_gate: bool = True,
    git: GitRunner = run_git,
) -> dict[str, Any]:
    state_root.mkdir(parents=True, exist_ok=True)
    lock_path = state_root / "publisher.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"schema_version": SCHEMA_VERSION, "status": "busy", "published": 0}
        base_sha = _assert_clean_origin_head(repo_root, git)
        ready = collect_ready_runs(queue_root, state_root, limit=max_runs)
        if not ready:
            return {"schema_version": SCHEMA_VERSION, "status": "idle", "published": 0, "base_sha": base_sha}
        run_ids = [str(state["run_id"]) for state, _, _ in ready]
        if dry_run:
            return {"schema_version": SCHEMA_VERSION, "status": "dry-run", "published": 0, "ready_runs": run_ids, "base_sha": base_sha}

        changed: list[str] = []
        approved_articles: list[dict[str, Any]] = []
        cache_token = ""
        for state, candidate, review in ready:
            decisions = {str(item["id"]): "APPROVE" for item in candidate["articles"]}
            approval = pipeline.build_approval(str(candidate["run_id"]), candidate["articles"], review, decisions, PUBLISHER_ID)
            run_dir = Path(str(state["run_dir"]))
            _write_json(run_dir / "approval.json", approval)
            changed.extend(str(path.relative_to(repo_root)) for path in pipeline.apply_approved_candidates(repo_root, str(candidate["run_id"]), candidate["articles"], review, approval))
            approved_articles.extend(candidate["articles"])
            cache_token = f"agy-{pipeline._safe_identifier(str(candidate['run_id']))[0]}"

        version = _bump_patch_version(repo_root)
        evidence_dir = state_root / "evidence" / f"publish-{version}"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        evidence_rel = evidence_dir.relative_to(repo_root).as_posix() if evidence_dir.is_relative_to(repo_root) else str(evidence_dir)
        article_count = _public_article_count(repo_root)
        fixture_path = _sync_web_test_release_fixture(repo_root, cache_token=cache_token, articles=approved_articles)
        changed.append(str(fixture_path.relative_to(repo_root)))
        _run_prerender(repo_root)
        _run_feed(repo_root)
        _prepend_changelog(repo_root, version=version, article_count=article_count, run_ids=run_ids, evidence_path=evidence_rel)
        if run_tests:
            _run_checked(repo_root, TEST_COMMAND)
        commit_sha = _stage_commit_tag_push(repo_root, version, git, push=push, release_gate=release_gate)
        ledger = _load_ledger(state_root)
        for run_id in run_ids:
            ledger["published_runs"].append({"run_id": run_id, "version": version, "commit_sha": commit_sha, "published_at": _now()})
        _write_json(_ledger_path(state_root), ledger)
        evidence = {
            "schema_version": SCHEMA_VERSION,
            "status": "PUBLISHED",
            "base_sha": base_sha,
            "commit_sha": commit_sha,
            "version": version,
            "run_ids": run_ids,
            "changed": sorted(set(changed)),
            "public_article_count": article_count,
            "pushed": push,
        }
        _write_json(evidence_dir / "publish-evidence.json", evidence)
        return evidence


def publish_ready_rewrite_runs(
    repo_root: Path,
    queue_root: Path,
    state_root: Path,
    *,
    max_runs: int = DEFAULT_MAX_RUNS,
    dry_run: bool = False,
    push: bool = False,
    run_tests: bool = True,
    release_gate: bool = True,
    git: GitRunner = run_git,
) -> dict[str, Any]:
    state_root.mkdir(parents=True, exist_ok=True)
    lock_path = state_root / "publisher.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"schema_version": SCHEMA_VERSION, "status": "busy", "rewritten": 0}
        base_sha = _assert_clean_origin_head(repo_root, git)
        ready = collect_ready_rewrite_runs(queue_root, state_root, limit=max_runs)
        if not ready:
            return {"schema_version": SCHEMA_VERSION, "status": "idle", "rewritten": 0, "base_sha": base_sha}
        run_ids = [str(state["run_id"]) for state, _, _, _ in ready]
        candidates = [candidate for _, candidate, _, _ in ready]
        article_ids = [str(article["article_id"]) for candidate in candidates for article in candidate["articles"]]
        if dry_run:
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "dry-run",
                "rewritten": 0,
                "ready_runs": run_ids,
                "article_ids": article_ids,
                "base_sha": base_sha,
            }

        release_id = f"agy-rewrite-{date.today().strftime('%Y%m%d')}-{len(run_ids):02d}"
        changed = [str(path.relative_to(repo_root)) for path in apply_rewrite_release(repo_root, release_id, candidates)]
        version = _bump_patch_version(repo_root)
        evidence_dir = state_root / "evidence" / f"rewrite-{version}"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        evidence_rel = evidence_dir.relative_to(repo_root).as_posix() if evidence_dir.is_relative_to(repo_root) else str(evidence_dir)
        article_count = _public_article_count(repo_root)
        _run_prerender(repo_root)
        _run_feed(repo_root)
        _prepend_rewrite_changelog(repo_root, version=version, article_count=article_count, run_ids=run_ids, article_ids=article_ids, evidence_path=evidence_rel)
        if run_tests:
            _run_checked(repo_root, TEST_COMMAND)
        commit_sha = _stage_commit_tag_push(
            repo_root,
            version,
            git,
            push=push,
            release_gate=release_gate,
            message=f"chore(content): publish Gemini rewrite release v{version}",
        )
        ledger = _load_ledger(state_root)
        for run_id in run_ids:
            ledger["rewrite_released_runs"].append({"run_id": run_id, "version": version, "commit_sha": commit_sha, "published_at": _now()})
        _write_json(_ledger_path(state_root), ledger)
        evidence = {
            "schema_version": SCHEMA_VERSION,
            "status": "PUBLISHED_REWRITE",
            "base_sha": base_sha,
            "commit_sha": commit_sha,
            "version": version,
            "run_ids": run_ids,
            "article_ids": article_ids,
            "changed": sorted(set(changed)),
            "public_article_count": article_count,
            "pushed": push,
        }
        _write_json(evidence_dir / "rewrite-evidence.json", evidence)
        return evidence


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--queue-root", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, default=Path(".work/content-publisher"))
    parser.add_argument("--max-runs", type=int, default=DEFAULT_MAX_RUNS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rewrite-release", action="store_true")
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-release-gate", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    publisher_fn = publish_ready_rewrite_runs if args.rewrite_release else publish_ready_runs
    result = publisher_fn(
        args.repo_root.resolve(),
        args.queue_root.resolve(),
        (args.repo_root / args.state_root).resolve() if not args.state_root.is_absolute() else args.state_root.resolve(),
        max_runs=args.max_runs,
        dry_run=args.dry_run,
        push=args.push,
        run_tests=not args.skip_tests,
        release_gate=not args.skip_release_gate,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("status") in {"PUBLISHED", "PUBLISHED_REWRITE", "idle", "busy", "dry-run"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
