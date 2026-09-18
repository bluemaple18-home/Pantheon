"""以完整 candidate、hash-bound review 與已提交 release 驗證舊 control。"""
import inspect
import json
from pathlib import Path

import pytest

from scripts import agy_content_publisher as publisher
from tests.test_agy_content_publisher import (
    _write_rewrite_run, make_schema_conformant_rewrite_article,
)


@pytest.fixture
def release(tmp_path, monkeypatch):
    for name in ("_stage_commit_tag_push", "_seed_pending_translations", "_recover_failed_publish"):
        monkeypatch.setattr(publisher, name, lambda *_a, **_k: pytest.fail("recovery must not publish, seed, or rollback"))
    repo, queue, state = (tmp_path / name for name in ("repo", "queue", "state"))
    repo.mkdir()
    article = make_schema_conformant_rewrite_article()
    run_dir = tmp_path / "runs" / "reconcile-fixture"
    _write_rewrite_run(queue, run_dir, article)
    _, candidate, review = publisher._load_completed_run(queue / "runs" / f"{run_dir.name}.json")
    article = candidate["articles"][0]
    assert publisher._review_is_clean_approve(review)
    brief = publisher._read_json(run_dir / "brief.json")
    record = {**article["identity"], "articleCategory": "astrology", "urlSlug": article["identity"]["slug"]}
    static = repo / "app/web/static"
    static.mkdir(parents=True)
    (repo / "package.json").write_text(json.dumps({"type": "module", "version": "0.3.98"}))
    (repo / "pyproject.toml").write_text('version = "0.3.98"\n')
    (repo / "CHANGELOG.md").write_text('# Changelog\n\n## [0.3.98] - 2026-09-17\n')
    (static / "article-registry.js").write_text(
        'export const ARTICLE_REGISTRY = ' + json.dumps([record], ensure_ascii=False) + ';\n'
        'export function listArticleRecords() { return ARTICLE_REGISTRY; }\n'
        'export function getArticlePath(r) { return "/articles/astrology/" + r.urlSlug; }\n'
    )
    (static / "article-meta.js").write_text(
        'const ARTICLE_BODY_LIBRARY = ' + json.dumps({record["slug"]: brief["articles"][0]["current_body"]}, ensure_ascii=False) + ';\n'
        'export function buildArticleContent() { return {bodySections: ARTICLE_BODY_LIBRARY[' + json.dumps(record["slug"]) + ']}; }\n'
    )
    inventory = publisher._assert_rewrite_source_matches(repo, [candidate])
    assert inventory[article["article_id"]]["record"] == record
    base = {p.relative_to(repo).as_posix(): p.read_text() for p in repo.rglob("*") if p.is_file()}
    release_id = "rewrite-20260918-01"
    _, identifier = publisher.pipeline._safe_identifier(release_id)
    body_export = f"AGY_{identifier}_REWRITE_BODY_OVERRIDES"
    policy_export = f"AGY_{identifier}_REWRITE_POLICY_OVERRIDES"
    module_path = f"app/web/static/article-rewrite-{release_id}.js"
    module = (
        f"export const {body_export} = {json.dumps({record['slug']: article['bodySections']}, ensure_ascii=False, indent=2)};\n\n"
        f"export const {policy_export} = {json.dumps({article['article_id']: {'updated': article['publicationPolicy']['modified'], 'publicationPolicy': article['publicationPolicy']}}, ensure_ascii=False, indent=2)};\n"
    )
    (repo / module_path).write_text(module)
    with (static / "article-registry.js").open("a") as stream:
        stream.write(f'import {{ {policy_export} }} from "./article-rewrite-{release_id}.js";\n')
    with (static / "article-meta.js").open("a") as stream:
        stream.write(f'import {{ {body_export} }} from "./article-rewrite-{release_id}.js";\n')
    registry = static / "article-registry.js"
    registry.write_text(registry.read_text().replace(
        "return ARTICLE_REGISTRY;", f"return ARTICLE_REGISTRY.map(r => ({{...r, ...{policy_export}[r.id]}}));"))
    meta = static / "article-meta.js"
    meta.write_text(meta.read_text().replace("bodySections: ARTICLE_BODY_LIBRARY[", f"bodySections: {body_export}["))
    evidence = state / "evidence/rewrite-0.3.99/rewrite-evidence.json"
    publisher._prepend_rewrite_changelog(repo, version="0.3.99", article_count=1,
        run_ids=[run_dir.name], article_ids=[article["article_id"]], evidence_path=str(evidence.parent))
    (repo / "package.json").write_text(json.dumps({"type": "module", "version": "0.3.99"}))
    (repo / "pyproject.toml").write_text('version = "0.3.99"\n')
    committed = {p.relative_to(repo).as_posix(): p.read_text() for p in repo.rglob("*") if p.is_file()}
    control = {"schema_version": 1, "status": "PUSH_OUTCOME_UNKNOWN", "phase": "rewrite",
        "candidate_sha": "c" * 40, "version": "0.3.99", "run_ids": [run_dir.name], "publish_evidence": str(evidence)}
    publisher._atomic_write_json(publisher._unresolved_push_path(state), control)
    calls = []
    refs = {"main": "c" * 40, "tag": "c" * 40}

    def git(_repo, args, _input=None):
        assert _repo == repo
        calls.append(args)
        if args == ["rev-parse", "--git-common-dir"]:
            return str(repo / ".git")
        if args == ["fetch", "origin", "main"]:
            return ""
        ref = "refs/agy-publisher-reconcile/v0.3.99"
        if args == ["ls-remote", "origin", "refs/tags/v0.3.99", "refs/tags/v0.3.99^{}"]:
            return f"{'d' * 40}\trefs/tags/v0.3.99\n{refs['tag']}\trefs/tags/v0.3.99^{{}}\n"
        if args == ["fetch", "--force", "origin", f"refs/tags/v0.3.99:{ref}"] or args == ["update-ref", "-d", ref]:
            return ""
        if args == ["rev-parse", "origin/main"]:
            return refs["main"]
        if args == ["rev-parse", f"{ref}^{{}}"]:
            return refs["tag"]
        if args == ["rev-list", "--parents", "-n", "1", "c" * 40]:
            return "c" * 40 + " " + "b" * 40
        if args == ["show", "-s", "--format=%cI", "c" * 40]:
            return "2026-09-18T10:00:00+08:00"
        if args[:2] == ["show", "--format="]:
            sha, path = args[2].split(":", 1)
            assert sha in {"b" * 40, "c" * 40}
            return (base if sha == "b" * 40 else committed)[path]
        if args[:3] == ["ls-tree", "-r", "--name-only"]:
            assert args[3] in {"b" * 40, "c" * 40}
            return "\n".join((base if args[3] == "b" * 40 else committed))
        if args == ["diff", "--name-only", "b" * 40, "c" * 40, "--"]:
            return "\n".join(p for p in committed if committed[p] != base.get(p))
        raise AssertionError(f"unexpected git operation: {args}")

    return dict(repo=repo, queue=queue, state=state, evidence=evidence, git=git,
        control=control, candidate=candidate, run_dir=run_dir, committed=committed, base=base,
        module_path=module_path, refs=refs, calls=calls)


def reconcile(f):
    kwargs = {"queue_root": f["queue"]} if "queue_root" in inspect.signature(publisher._reconcile_unresolved_push).parameters else {}
    return publisher._reconcile_unresolved_push(f["repo"], f["state"], f["git"], **kwargs)


def test_remote_published_missing_accounts_can_reconcile(release):
    f = release
    reconcile(f)
    entries = publisher._load_ledger(f["state"])["rewrite_released_runs"]
    assert len(entries) == 1
    assert entries[0]["article_ids"] == [f["candidate"]["articles"][0]["article_id"]]
    evidence = publisher._read_json(f["evidence"])
    assert evidence["input_hash"] == publisher._bytes_sha256(publisher.pipeline.compact_json_bytes([f["candidate"]]))
    assert evidence["commit_sha"] == "c" * 40
    assert not publisher._unresolved_push_path(f["state"]).exists()


def restore_control(f):
    publisher._atomic_write_json(publisher._unresolved_push_path(f["state"]), f["control"])


def accounts(f):
    return {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in
        (publisher._ledger_path(f["state"]), f["evidence"]) if path.exists()}


@pytest.mark.parametrize("missing", ["ledger", "evidence", "neither"])
def test_partial_or_complete_accounts_are_idempotent(release, missing):
    f = release
    reconcile(f)
    restore_control(f)
    path = {"ledger": publisher._ledger_path(f["state"]), "evidence": f["evidence"]}.get(missing)
    if path:
        path.unlink()
    before = accounts(f)
    reconcile(f)
    after = accounts(f)
    assert all(after[path] == value for path, value in before.items())
    assert len(publisher._load_ledger(f["state"])["rewrite_released_runs"]) == 1
    restore_control(f)
    reconcile(f)
    assert accounts(f) == after


@pytest.mark.parametrize("ref", ["main", "tag"])
def test_remote_unknown_or_mismatched_does_not_write(release, ref):
    f = release
    f["refs"][ref] = "e" * 40
    with pytest.raises(publisher.PublishBlocked, match="remote refs"):
        reconcile(f)
    assert accounts(f) == {}
    assert publisher._unresolved_push_path(f["state"]).exists()


@pytest.mark.parametrize("mismatch", ["candidate", "review", "run", "version", "module", "active", "parent", "incomplete", "missing_queue", "control_commit", "control_tag", "extra_run"])
def test_legacy_authority_mismatch_fails_before_account_write(release, mismatch):
    f = release
    candidate_path = f["run_dir"] / "candidate.json"
    if mismatch == "candidate":
        candidate = publisher._read_json(candidate_path)
        candidate["articles"][0]["bodySections"][0]["paragraphs"][0] += "候選已變更。"
        publisher._write_json(candidate_path, candidate)
    elif mismatch == "review":
        review_path = f["run_dir"] / "review.json"
        review = publisher._read_json(review_path)
        review["articles"][0]["verdict"] = "REJECT"
        publisher._write_json(review_path, review)
    elif mismatch == "run":
        f["committed"]["CHANGELOG.md"] = f["committed"]["CHANGELOG.md"].replace("reconcile-fixture", "another-run")
    elif mismatch == "version":
        f["committed"]["package.json"] = '{"version": "0.3.98"}'
    elif mismatch == "module":
        f["committed"][f["module_path"]] += "// payload drift\n"
    elif mismatch == "active":
        f["committed"]["app/web/static/article-meta.js"] = f["base"]["app/web/static/article-meta.js"]
    elif mismatch == "parent":
        f["base"]["app/web/static/article-meta.js"] = f["base"]["app/web/static/article-meta.js"].replace("舊內容", "來源已變")
    elif mismatch == "incomplete":
        publisher._write_json(candidate_path, {"run_id": f["control"]["run_ids"][0], "articles": [{"article_id": "LEGACY-SCHEMA-CONFORMANT"}]})
    elif mismatch == "missing_queue":
        candidate_path.unlink()
    elif mismatch == "control_commit":
        f["control"]["candidate_sha"] = "a" * 40
        restore_control(f)
    elif mismatch == "control_tag":
        f["control"]["version"] = "0.3.98"
        restore_control(f)
    elif mismatch == "extra_run":
        f["control"]["run_ids"].append("unproven-run")
        restore_control(f)
    with pytest.raises(publisher.PublishBlocked):
        reconcile(f)
    assert accounts(f) == {}
    assert publisher._unresolved_push_path(f["state"]).exists()


@pytest.mark.parametrize("kind,field", [(kind, field) for kind in ("ledger", "evidence")
    for field in ("version", "commit_sha", "run_id", "article_ids", "input_hash")
    if (kind, field) != ("ledger", "input_hash")])
def test_existing_conflict_is_preserved_without_other_writes(release, kind, field):
    f = release
    reconcile(f)
    restore_control(f)
    if kind == "ledger":
        path = publisher._ledger_path(f["state"])
        value = publisher._read_json(path)
        value["rewrite_released_runs"][0][field] = ["wrong"] if field == "article_ids" else "wrong"
        f["evidence"].unlink()
    else:
        path = f["evidence"]
        value = publisher._read_json(path)
        field = "run_ids" if field == "run_id" else field
        value[field] = ["wrong"] if field in {"article_ids", "run_ids"} else "wrong"
        publisher._ledger_path(f["state"]).unlink()
    publisher._atomic_write_json(path, value)
    before = accounts(f)
    with pytest.raises(publisher.PublishBlocked):
        reconcile(f)
    assert accounts(f) == before
    assert publisher._unresolved_push_path(f["state"]).exists()


@pytest.mark.parametrize("target", ["ledger", "evidence"])
@pytest.mark.parametrize("when", ["before", "after"])
def test_interrupted_recovery_resumes_without_duplicate_or_rewrite(release, monkeypatch, target, when):
    f = release
    original = publisher._atomic_write_json
    path = publisher._ledger_path(f["state"]) if target == "ledger" else f["evidence"]
    class Interrupted(BaseException):
        pass
    def interrupt(destination, payload):
        if destination == path and when == "before":
            raise Interrupted()
        original(destination, payload)
        if destination == path and when == "after":
            raise Interrupted()
    with monkeypatch.context() as patch:
        patch.setattr(publisher, "_atomic_write_json", interrupt)
        with pytest.raises(Interrupted):
            reconcile(f)
    assert publisher._unresolved_push_path(f["state"]).exists()
    before = accounts(f)
    reconcile(f)
    after = accounts(f)
    assert all(after[path] == value for path, value in before.items())
    assert len(publisher._load_ledger(f["state"])["rewrite_released_runs"]) == 1


def test_readback_failure_retains_control(release, monkeypatch):
    f = release
    original = publisher._atomic_write_json
    def corrupt(destination, payload):
        original(destination, payload)
        if destination == f["evidence"]:
            original(destination, {**payload, "input_hash": "wrong"})
    with monkeypatch.context() as patch:
        patch.setattr(publisher, "_atomic_write_json", corrupt)
        with pytest.raises(publisher.PublishBlocked, match="readback"):
            reconcile(f)
    assert publisher._unresolved_push_path(f["state"]).exists()


@pytest.mark.parametrize("scope", ["repo", "state"])
def test_reconciliation_obeys_publisher_locks(release, scope):
    import fcntl
    f = release
    path = publisher._repo_lock_path(f["repo"], f["git"]) if scope == "repo" else f["state"] / "publisher.lock"
    with path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = len(f["calls"])
        with pytest.raises(publisher.PublishBlocked, match="lock is busy"):
            reconcile(f)
        assert all(call == ["rev-parse", "--git-common-dir"] for call in f["calls"][before:])
    assert accounts(f) == {}
    reconcile(f)


def test_queue_authority_is_required(release):
    f = release
    with pytest.raises(publisher.PublishBlocked, match="source unavailable"):
        publisher._reconcile_unresolved_push(f["repo"], f["state"], f["git"])
    assert accounts(f) == {}


@pytest.fixture
def create_release(release):
    from tests.test_agy_content_publisher import _write_run, make_publishable_article
    f = release
    _write_run(f["queue"], f["run_dir"], make_publishable_article("RECONCILE-CREATE"))
    _, candidate, _ = publisher._load_completed_run(f["queue"] / "runs" / f"{f['run_dir'].name}.json")
    f["candidate"] = candidate
    article = candidate["articles"][0]
    slug, identifier = publisher.pipeline._safe_identifier(candidate["run_id"])
    records = [{k: v for k, v in article.items() if k != "bodySections"}]
    bodies = {article["slug"]: article["bodySections"]}
    module_path = f"app/web/static/article-expansion-agy-{slug}.js"
    module = (
        "// AGY 核准文章批次；由 scripts/agy_seo_copy_pipeline.py 產生。\n\n"
        f"export const AGY_{identifier}_ARTICLE_RECORDS = {json.dumps(records, ensure_ascii=False, indent=2)};\n\n"
        f"export const AGY_{identifier}_ARTICLE_BODY_LIBRARY = {json.dumps(bodies, ensure_ascii=False, indent=2)};\n"
    )
    f["committed"].pop(f["module_path"])
    f["module_path"] = module_path
    f["committed"][module_path] = module
    f["committed"]["app/web/static/article-registry.js"] = (
        f'import {{ AGY_{identifier}_ARTICLE_RECORDS }} from "./{Path(module_path).name}";\n'
        f'export function listArticleRecords() {{ return AGY_{identifier}_ARTICLE_RECORDS; }}\n'
        'export function getArticlePath(r) { return "/articles/personality/" + r.urlSlug; }\n'
    )
    f["committed"]["app/web/static/article-meta.js"] = (
        f'import {{ AGY_{identifier}_ARTICLE_BODY_LIBRARY }} from "./{Path(module_path).name}";\n'
        f'export function buildArticleContent() {{ return {{bodySections: AGY_{identifier}_ARTICLE_BODY_LIBRARY[{json.dumps(article["slug"])}]}}; }}\n'
    )
    f["evidence"] = f["state"] / "evidence/publish-0.3.99/publish-evidence.json"
    f["control"].update(phase="create", publish_evidence=str(f["evidence"]))
    (f["repo"] / "CHANGELOG.md").write_text(f["base"]["CHANGELOG.md"])
    publisher._prepend_changelog(f["repo"], version="0.3.99", article_count=1,
        run_ids=f["control"]["run_ids"], evidence_path=str(f["evidence"].parent))
    f["committed"]["CHANGELOG.md"] = (f["repo"] / "CHANGELOG.md").read_text()
    restore_control(f)
    return f


def test_create_legacy_control_uses_same_canonical_contract(create_release):
    f = create_release
    reconcile(f)
    ledger = publisher._load_ledger(f["state"])
    assert len(ledger["published_runs"]) == 1
    assert ledger["published_runs"][0]["article_ids"] == ["RECONCILE-CREATE"]
    assert ledger["published_runs"][0]["translation_seed_status"] == "pending"
    evidence = publisher._read_json(f["evidence"])
    assert evidence["status"] == "PUBLISHED"
    assert evidence["input_hash"] == publisher._bytes_sha256(publisher.pipeline.compact_json_bytes([f["candidate"]]))
    restore_control(f)
    before = accounts(f)
    reconcile(f)
    assert accounts(f) == before


def test_create_candidate_with_new_review_must_still_match_commit(create_release):
    f = create_release
    candidate = f["candidate"]
    candidate["articles"][0]["title"] += "另一版本"
    publisher._write_json(f["run_dir"] / "candidate.json", candidate)
    publisher._write_json(f["run_dir"] / "review.json", publisher.pipeline.deterministic_review_payload(candidate["run_id"], candidate["articles"], []))
    with pytest.raises(publisher.PublishBlocked, match="candidate payload differs"):
        reconcile(f)
    assert accounts(f) == {}


def test_rewrite_candidate_with_new_review_must_still_match_commit(release):
    f = release
    candidate = f["candidate"]
    candidate["articles"][0]["bodySections"][0]["paragraphs"][0] += "另一版本"
    publisher._write_json(f["run_dir"] / "candidate.json", candidate)
    publisher._write_json(f["run_dir"] / "review.json", publisher.pipeline.deterministic_review_payload(candidate["run_id"], candidate["articles"], []))
    with pytest.raises(publisher.PublishBlocked, match="candidate payload differs"):
        reconcile(f)
    assert accounts(f) == {}


def test_normal_canonical_accounts_preserve_timestamp_and_seed_metadata(release, monkeypatch):
    f = release
    article = f["candidate"]["articles"][0]
    entry = {"run_id": f["candidate"]["run_id"], "version": "0.3.99", "commit_sha": "c" * 40,
        "published_at": "2026-09-18T10:00:02+08:00", "article_ids": [article["article_id"]],
        "translation_seed_status": "seeded", "translation_run_ids": ["translation-run"],
        "translation_seeded_at": "2026-09-18T10:00:03+08:00"}
    evidence = {"schema_version": 1, "status": "PUBLISHED_REWRITE", "base_sha": "b" * 40,
        "commit_sha": "c" * 40, "version": "0.3.99", "run_ids": [entry["run_id"]],
        "article_ids": entry["article_ids"], "changed": [f["module_path"]], "public_article_count": 1,
        "legacy_cutoff_count": publisher.LEGACY_ARTICLE_COUNT_CUTOFF, "legacy_rewrite_backlog": {"remaining": 0},
        "seeded_translation_runs": ["translation-run"], "pushed": True,
        "policy_version": article["publicationPolicy"]["policyVersion"], "validator_result": "PASS",
        "failure_codes": [], "input_hash": publisher._bytes_sha256(publisher.pipeline.compact_json_bytes([f["candidate"]])),
        "translation_seed_status": "seeded", "translation_seed_errors": {}}
    ledger = publisher._load_ledger(f["state"])
    ledger["rewrite_released_runs"].append(entry)
    publisher._atomic_write_json(publisher._ledger_path(f["state"]), ledger)
    publisher._atomic_write_json(f["evidence"], evidence)
    before = accounts(f)
    monkeypatch.setattr(publisher, "_seed_pending_translations", lambda *_a, **_k: pytest.fail("recovery must not seed"))
    monkeypatch.setattr(publisher, "_atomic_write_json", lambda *_a, **_k: pytest.fail("complete accounts must not be rewritten"))
    reconcile(f)
    assert accounts(f) == before


def test_transport_failure_keeps_control(release):
    import subprocess
    f = release
    original = f["git"]
    def unavailable(repo, args, value=None):
        if args == ["fetch", "origin", "main"]:
            raise subprocess.CalledProcessError(128, ["git", *args])
        return original(repo, args, value)
    f["git"] = unavailable
    with pytest.raises(publisher.PublishBlocked, match="source unavailable"):
        reconcile(f)
    assert accounts(f) == {}
    assert publisher._unresolved_push_path(f["state"]).exists()


def test_control_removal_interruption_retries_without_account_write(release, monkeypatch):
    f = release
    control_path = publisher._unresolved_push_path(f["state"])
    original = Path.unlink
    def interrupt(path, *args, **kwargs):
        if path == control_path:
            raise OSError("fixture interrupted control removal")
        return original(path, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", interrupt)
        with pytest.raises(publisher.PublishBlocked):
            reconcile(f)
    before = accounts(f)
    assert len(before) == 2 and control_path.exists()
    reconcile(f)
    assert accounts(f) == before


def test_lifecycle_lock_precedes_remote_read(release):
    import fcntl
    import threading
    from concurrent.futures import ThreadPoolExecutor
    f = release
    path = publisher._repo_lock_path(f["repo"], f["git"]).with_name("agy-content-publisher.lifecycle.lock")
    reached = threading.Event()
    original = f["git"]
    def observed(repo, args, value=None):
        if args == ["fetch", "origin", "main"]:
            reached.set()
        return original(repo, args, value)
    f["git"] = observed
    with path.open("a+") as lock, ThreadPoolExecutor(max_workers=1) as pool:
        fcntl.flock(lock, fcntl.LOCK_EX)
        future = pool.submit(reconcile, f)
        try:
            assert not reached.wait(0.1)
            assert not future.done()
            assert accounts(f) == {}
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
        assert future.result(timeout=5)["status"] == "PUSH_OUTCOME_RECONCILED"


def test_normal_record_builder_keeps_runtime_policy_source(monkeypatch):
    monkeypatch.setattr(publisher.pipeline, "publication_policy_version", lambda: "normal-policy")
    for phase, key in (("create", "id"), ("rewrite", "article_id")):
        entries, evidence = publisher._publication_records(phase,
            [{"run_id": "mock-normal-run", "articles": [{key: "ARTICLE"}]}],
            version="0.3.99", commit_sha="c" * 40, base_sha="b" * 40,
            changed=[], article_count=1, published_at="now", pushed=True)
        assert evidence["policy_version"] == "normal-policy"
        assert entries[0]["article_ids"] == ["ARTICLE"]


@pytest.mark.parametrize("missing", [None, "ledger", "evidence"])
def test_legacy_translation_only_reconciles_existing_accounts(release, missing, monkeypatch):
    f = release
    f["evidence"] = f["state"] / "evidence/translation-0.3.99/translation-evidence.json"
    f["control"].update(phase="translation", publish_evidence=str(f["evidence"]))
    restore_control(f)
    ledger = publisher._load_ledger(f["state"])
    ledger["translation_published_runs"].append({"run_id": f["control"]["run_ids"][0],
        "version": "0.3.99", "commit_sha": "c" * 40})
    if missing != "ledger":
        publisher._atomic_write_json(publisher._ledger_path(f["state"]), ledger)
    if missing != "evidence":
        publisher._atomic_write_json(f["evidence"], {"status": "PUBLISHED_TRANSLATION",
            "version": "0.3.99", "commit_sha": "c" * 40, "run_ids": f["control"]["run_ids"]})
    before = accounts(f)
    monkeypatch.setattr(publisher, "_atomic_write_json", lambda *_a, **_k: pytest.fail("legacy translation must not auto-recover"))
    if missing:
        with pytest.raises(publisher.PublishBlocked, match="existing converged"):
            publisher._reconcile_unresolved_push(f["repo"], f["state"], f["git"])
        assert publisher._unresolved_push_path(f["state"]).exists()
    else:
        publisher._reconcile_unresolved_push(f["repo"], f["state"], f["git"])
        assert not publisher._unresolved_push_path(f["state"]).exists()
    assert accounts(f) == before


def test_completed_recovery_second_call_is_idle_without_remote_or_write(release):
    f = release
    reconcile(f)
    before = accounts(f)
    calls = len(f["calls"])
    assert reconcile(f)["status"] == "idle"
    assert all(call == ["rev-parse", "--git-common-dir"] for call in f["calls"][calls:])
    assert accounts(f) == before


def revision_snapshot(f):
    """連同 control 的 bytes／mtime 核對拒絕前後完全未變。"""
    control = publisher._unresolved_push_path(f["state"])
    return {**accounts(f), control: (control.read_bytes(), control.stat().st_mtime_ns)}


@pytest.mark.parametrize("field", ["id", "section", "product", "slug", "serial", "urlSlug",
    "primaryKeyword", "secondaryKeywords", "title", "description", "answer", "faq",
    "published", "updated", "tags", "canonicalPath"])
@pytest.mark.parametrize("complete", [False, True])
def test_revision_create_active_identity_conflict_preserves_all_artifacts(create_release, field, complete):
    f = create_release
    if complete:
        reconcile(f)
        restore_control(f)
    name = "app/web/static/article-registry.js"
    _, identifier = publisher.pipeline._safe_identifier(f["candidate"]["run_id"])
    source = f["committed"][name]
    if field == "canonicalPath":
        source = source.replace('"/articles/personality/" + r.urlSlug', '"/articles/test/" + r.slug')
    else:
        value = ["wrong"] if field in {"secondaryKeywords", "faq", "tags"} else "wrong"
        source = source.replace(f"return AGY_{identifier}_ARTICLE_RECORDS;",
            f"return AGY_{identifier}_ARTICLE_RECORDS.map(r => ({{...r, {field}: {json.dumps(value)}}}));")
    assert source != f["committed"][name]
    f["committed"][name] = source
    before = revision_snapshot(f)
    with pytest.raises(publisher.PublishBlocked, match="active"):
        reconcile(f)
    assert revision_snapshot(f) == before


@pytest.mark.parametrize("payload", [None, [], [{}], "existing", 42, False])
@pytest.mark.parametrize("existing_ledger", [False, True])
def test_revision_nonobject_evidence_blocks_before_any_ledger_write(release, payload, existing_ledger):
    f = release
    if existing_ledger:
        publisher._atomic_write_json(publisher._ledger_path(f["state"]), publisher._load_ledger(f["state"]))
    publisher._atomic_write_json(f["evidence"], payload)
    before = revision_snapshot(f)
    with pytest.raises(publisher.PublishBlocked, match="must be an object"):
        reconcile(f)
    assert revision_snapshot(f) == before


@pytest.mark.parametrize("bucket", ["published_runs", "translation_published_runs", "superseded_runs",
    "quarantined_runs", "translation_deferred_runs"])
@pytest.mark.parametrize("claim", ["same_run_old_release", "same_run_same_release", "other_run_same_release", "other_run_version", "other_run_commit"])
def test_revision_cross_bucket_run_and_release_conflict_preserves_all_artifacts(release, bucket, claim):
    f = release
    ledger = publisher._load_ledger(f["state"])
    same_run = claim.startswith("same_run")
    ledger[bucket].append({"run_id": f["candidate"]["run_id"] if same_run else "another-run",
        "version": "0.3.99" if claim in {"same_run_same_release", "other_run_same_release", "other_run_version"} else "0.3.98",
        "commit_sha": "c" * 40 if claim in {"same_run_same_release", "other_run_same_release", "other_run_commit"} else "a" * 40,
        "article_ids": ["DIFFERENT-ARTICLE"], "published_at": "2026-09-17T10:00:00+08:00",
        "translation_seed_status": "seeded"})
    publisher._atomic_write_json(publisher._ledger_path(f["state"]), ledger)
    before = revision_snapshot(f)
    with pytest.raises(publisher.PublishBlocked, match="ownership conflicts"):
        reconcile(f)
    assert revision_snapshot(f) == before


@pytest.mark.parametrize("bucket", ["published_runs", "rewrite_released_runs", "translation_published_runs",
    "superseded_runs", "quarantined_runs", "translation_deferred_runs"])
def test_revision_other_run_historical_article_ownership_remains_valid(release, bucket):
    f = release
    ledger = publisher._load_ledger(f["state"])
    history = {"run_id": "historical-run", "version": "0.3.98", "commit_sha": "a" * 40,
        "article_ids": [f["candidate"]["articles"][0]["article_id"]],
        "published_at": "2026-09-17T10:00:00+08:00", "translation_seed_status": "seeded"}
    ledger[bucket].append(history)
    publisher._atomic_write_json(publisher._ledger_path(f["state"]), ledger)
    reconcile(f)
    assert publisher._load_ledger(f["state"])[bucket][0] == history
    restore_control(f)
    before = accounts(f)
    reconcile(f)
    assert accounts(f) == before


def test_revision_create_real_registry_derived_fields_are_compatible(create_release):
    f = create_release
    name = "app/web/static/article-registry.js"
    production_registry = (Path(publisher.__file__).resolve().parents[1] / name).read_text()
    # 直接使用既有純函式，保持實際 tags／keywords／articleCategory 衍生契約。
    policy = production_registry.split("export function enforceArticlePolicy(", 1)[1].split("export function fallbackArticleSectionLabel", 1)[0]
    unique = production_registry.split("function uniqueList(", 1)[1].split("function humanizeSlug", 1)[0]
    source = f["committed"][name]
    _, identifier = publisher.pipeline._safe_identifier(f["candidate"]["run_id"])
    source = source.replace(f"return AGY_{identifier}_ARTICLE_RECORDS;",
        f'return AGY_{identifier}_ARTICLE_RECORDS.map(r => enforceArticlePolicy(r, {{requiredTags: ["合法衍生標籤"], primaryKeyword: "section keyword"}}));')
    source += '\nconst GLOBAL_ARTICLE_POLICY = {requiredTags: ["必要標籤"], requiredKeywordTags: []};\nconst ARTICLE_SERIAL_REGISTRY = {};\n'
    source += "export function enforceArticlePolicy(" + policy + "function uniqueList(" + unique
    f["committed"][name] = source
    with publisher._committed_article_view(f["repo"], "c" * 40, f["git"]) as root:
        active = publisher.pipeline._existing_rewrite_inventory(root)["RECONCILE-CREATE"]
    assert active["record"]["tags"] != f["candidate"]["articles"][0]["tags"]
    assert active["record"]["originalTags"] == f["candidate"]["articles"][0]["tags"]
    assert active["canonicalPath"] == publisher._article_path(f["candidate"]["articles"][0])
    reconcile(f)
    restore_control(f)
    before = accounts(f)
    reconcile(f)
    assert accounts(f) == before


def test_revision_actual_create_apply_with_canonical_path_can_reconcile(create_release, tmp_path):
    from tests.test_agy_content_publisher import _minimal_article_static
    f = create_release
    normal = tmp_path / "normal-create-output"
    _minimal_article_static(normal)
    (normal / "package.json").write_text(json.dumps({"type": "module", "version": "0.3.98"}))
    (normal / "pyproject.toml").write_text('version = "0.3.98"\n')
    (normal / "CHANGELOG.md").write_text(f["base"]["CHANGELOG.md"])
    article = f["candidate"]["articles"][0]
    registry = normal / "app/web/static/article-registry.js"
    registry.write_text(registry.read_text() + '\nexport function getArticlePath(r) { return "/articles/" + r.serial.replace(/-\\d+$/, "") + "/" + r.urlSlug; }\n')
    meta = normal / "app/web/static/article-meta.js"
    meta.write_text(meta.read_text().replace("legacy-001", article["slug"]).replace("return customBody;", "return {bodySections: customBody};"))
    def snapshot():
        return {path.relative_to(normal).as_posix(): path.read_text() for path in normal.rglob("*") if path.is_file()}
    f["base"].clear()
    f["base"].update(snapshot())
    review = publisher._read_json(f["run_dir"] / "review.json")
    approval = publisher.pipeline.build_approval(f["candidate"]["run_id"], [article], review,
        {article["id"]: "APPROVE"}, publisher.PUBLISHER_ID)
    publisher.pipeline.apply_approved_candidates(normal, f["candidate"]["run_id"], [article], review, approval)
    changelog = f["committed"]["CHANGELOG.md"]
    f["committed"].clear()
    f["committed"].update(snapshot())
    f["committed"].update({"CHANGELOG.md": changelog,
        "package.json": json.dumps({"type": "module", "version": "0.3.99"}),
        "pyproject.toml": 'version = "0.3.99"\n'})
    with publisher._committed_article_view(f["repo"], "c" * 40, f["git"]) as root:
        active = publisher.pipeline._existing_rewrite_inventory(root)[article["id"]]
    assert active["canonicalPath"] == publisher._article_path(article)
    assert article["publicationPolicy"]["canonical"] == "https://www.mysticpantheon.com" + active["canonicalPath"]
    assert reconcile(f)["status"] == "PUSH_OUTCOME_RECONCILED"
    restore_control(f)
    before = accounts(f)
    reconcile(f)
    assert accounts(f) == before
