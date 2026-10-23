#!/usr/bin/env python3
"""薄接 production runtime 的 bounded、無外部副作用 capability dry-run。"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Callable, Iterator

from scripts import agy_content_publisher as publisher
from scripts import agy_gemini_coordinator as coordinator
from scripts import agy_gemini_runner as runner
from scripts import agy_multilingual_pipeline as multilingual
from scripts import agy_seo_copy_pipeline as pipeline
from scripts.agy_gemini_v4_broker import AGY_MODEL_LABELS
from scripts import pantheon_content_capacity_guard as capacity_guard
from scripts import pantheon_content_runtime_manifest as runtime_manifest
from scripts.agy_gemini_outbox import create_external_request


CAPABILITIES = ("create", "run", "select", "publish", "transaction", "tag", "push")
PREVIOUS = dict(zip(CAPABILITIES, (None, *CAPABILITIES[:-1])))
RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
}


class AdapterBlocked(ValueError):
    """正式 production boundary 拒絕不連續或不完整 handoff。"""


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


OFFLINE_ARTICLE_ID = "PROBE-001"
OFFLINE_EXECUTABLE = b"#!/bin/sh\nprintf '%s\\n' '{\"ok\":true}'\n"


def prepare_offline_actor(sandbox_root: Path, source_root: Path) -> tuple[Path, str]:
    """用真 Git 綁定合成已發布來源；不寫入正式 actor 或發布 receipt。"""
    actor = sandbox_root / "actor"
    actor.mkdir()
    # 從實際 checkout 複製受版本控制的執行依賴，包含本卡未提交的修正。
    paths = subprocess.run(
        ["git", "-C", str(source_root), "ls-files", "-z", "--", "scripts", "config", "ops/launchd"],
        check=True, capture_output=True,
    ).stdout.decode().split("\0")
    for relative in sorted(set(filter(None, paths)) | set(publisher.TRANSACTION_RUNTIME_PATHS)):
        destination = actor / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((source_root / relative).read_bytes())
    static = actor / "app/web/static"
    static.mkdir(parents=True)
    article = {
        "article_id": OFFLINE_ARTICLE_ID,
        "canonical_path": "/articles/tarot/probe-0001",
        "title": "離線契約驗證",
        "description": "此合成內容只供離線契約驗證。",
        "answer": "以可重現的本地資料確認來源一致。",
        "tags": ["離線驗證"],
        "faq": [{"question": "用途是什麼？", "answer": "只供離線契約驗證。"}],
        "bodySections": [{"heading": "來源", "paragraphs": ["本內容沒有對外發布。"]}],
    }
    article["publication_policy"] = multilingual.source_publication_policy(
        pipeline._hydrate_create_publication_policy({
            "target": {**article, "published": "2026-09-15", "updated": "2026-09-15"},
        })
    )
    multilingual.validate_source_contract(article)
    (static / "article-registry.js").write_text(
        "export const getArticlePath = () => " + json.dumps(article["canonical_path"])
        + "; export const listArticleRecords = () => "
        + json.dumps([{"id": OFFLINE_ARTICLE_ID,
                       "publicationPolicy": article["publication_policy"]["article_policy"]}])
        + ";\n", encoding="utf-8",
    )
    (static / "article-meta.js").write_text(
        "export const buildArticleContent = () => ("
        + json.dumps({**article, "displayTags": article["tags"]}) + ");\n",
        encoding="utf-8",
    )
    for relative in ("pyproject.toml", "package.json"):
        (actor / relative).write_bytes((source_root / relative).read_bytes())
    git = ["git", "-c", "core.hooksPath=/dev/null", "-c", "user.name=Offline Probe",
           "-c", "user.email=offline-probe@example.invalid", "-C", str(actor)]
    def local_git(*args: str) -> str:
        return subprocess.run([*git, *args], check=True, capture_output=True, text=True).stdout.strip()
    local_git("init", "-q")
    local_git("add", ".")
    local_git("commit", "-qm", "離線來源 fixture")
    actor_sha = local_git("rev-parse", "HEAD")
    local_git("update-ref", "refs/remotes/origin/main", actor_sha)
    # 既有來源 authority 格式；所有 commit、文章與 run 都只屬於本輪 sandbox。
    ledger = {"schema_version": 1}
    for key in ("published_runs", "rewrite_released_runs"):
        ledger[key] = [{"run_id": "offline-source-" + key,
                        "article_ids": [OFFLINE_ARTICLE_ID], "commit_sha": actor_sha,
                        "translation_run_ids": [multilingual.translation_run_id(
                            "offline-source-" + key, OFFLINE_ARTICLE_ID, "en"
                        )]}]
    (sandbox_root / "publisher-state/ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
    return actor, actor_sha


def _prepare_offline_transport(sandbox_root: Path) -> None:
    """建立既有 V4 與 allocator 可實際讀取的合成契約，不使用 live credential。"""
    root = sandbox_root / "offline-transport"
    root.mkdir(mode=0o700)
    slots = []
    for slot in runner.PRODUCTION_SLOT_IDS:
        path = root / slot
        path.write_text("offline-probe-credential-" + slot + "\n", encoding="utf-8")
        path.chmod(0o600)
        slots.append({"slot_id": slot, "credential_file": str(path)})
    pool = root / "pool.json"
    pool.write_text(json.dumps({"schema_version": 1, "pool_id": "offline-probe", "slots": slots}), encoding="utf-8")
    pool.chmod(0o600)
    models = list(AGY_MODEL_LABELS)
    (root / "routes.json").write_text(json.dumps({
        "schema_version": 1, "routes": {"writer": [models[0]], "reviewer": [models[1]]},
    }), encoding="utf-8")
    executable = root / "generate-json"
    executable.write_bytes(OFFLINE_EXECUTABLE)
    executable.chmod(0o700)


@contextmanager
def _offline_transport(sandbox_root: Path) -> Iterator[str]:
    """只綁定本輪 owned 檔案；正式 process_once 與 admission 保持原函式。"""
    root = sandbox_root / "offline-transport"
    for name in ("pool.json", "routes.json", "generate-json", *runner.PRODUCTION_SLOT_IDS):
        path = root / name
        if root.is_symlink() or path.is_symlink() or path.resolve() != path or not path.is_file() or path.stat().st_uid != os.getuid():
            raise AdapterBlocked("offline transport path identity mismatch")
    executable = root / "generate-json"
    if executable.read_bytes() != OFFLINE_EXECUTABLE:
        raise AdapterBlocked("offline executable identity mismatch")
    route = pipeline.load_model_route_config(root / "routes.json")
    pool = json.loads((root / "pool.json").read_text(encoding="utf-8"))
    expected_slots = [{"slot_id": slot, "credential_file": str(root / slot)} for slot in runner.PRODUCTION_SLOT_IDS]
    if pool["pool_id"] != "offline-probe" or pool["slots"] != expected_slots:
        raise AdapterBlocked("offline credential pool identity mismatch")
    runner._read_production_pool(root / "pool.json")
    values = {
        "AGY_GEMINI_CREDENTIAL_POOL_FILE": str(root / "pool.json"),
        "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE": str(root / "pool-state.json"),
        "AGY_GEMINI_MODEL_ROUTE_CONFIG": str(route.path),
        "AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST": route.digest,
        "AGY_WRITER_MODEL": route.routes["writer"][0],
        "AGY_REVIEWER_MODEL": route.routes["reviewer"][0],
        "AGY_GEMINI_DAILY_PROVIDER_ADMISSION_CAP": str(runner.DAILY_PROVIDER_ADMISSION_CAP),
        "AGY_GEMINI_V4_BROKER": "1",
        "AGY_GEMINI_V4_EXECUTABLE": str(executable),
        "AGY_GEMINI_V4_EXECUTABLE_SHA256": hashlib.sha256(OFFLINE_EXECUTABLE).hexdigest(),
        "AGY_GEMINI_NEW_ONLY": "0",
    }
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        pipeline.model_route_config_from_environment()
        yield route.routes["writer"][0]
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@contextmanager
def _formal_environment(
    manifest_path: Path,
    manifest: dict[str, Any],
    service_label: str,
    activation_token: Path,
) -> Iterator[None]:
    values = {
        "PANTHEON_FORMAL_RUNTIME": "1",
        "PANTHEON_RUNTIME_MANIFEST": str(manifest_path),
        "PANTHEON_RUNTIME_MANIFEST_DIGEST": manifest["manifest_digest"],
        "PANTHEON_RUNTIME_IDENTITY": manifest["identity"],
        "PANTHEON_RUNTIME_IDENTITY_DIGEST": manifest["runtime_identity_digest"],
        "PANTHEON_RUNTIME_CODE_DIGEST": manifest["runtime_digest"],
        "PANTHEON_RUNTIME_CONFIG_VERSION": manifest["config_version"],
        "PANTHEON_RUNTIME_GENERATION": manifest["generation"],
        "PANTHEON_RUNTIME_SERVICE_LABEL": service_label,
        "PANTHEON_RUNTIME_ACTOR_ROOT": manifest["actor_root"],
        "PANTHEON_RUNTIME_QUEUE_ROOT": manifest["queue_root"],
        "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": manifest[
            "publisher_state_root"
        ],
        "PANTHEON_RUNTIME_LOG_ROOT": manifest["log_root"],
        "PANTHEON_RUNTIME_ACTIVATION_TOKEN": str(activation_token),
    }
    for field, name in (("actor_head", "PANTHEON_RUNTIME_ACTOR_HEAD"),
                        ("uv_executable", "PANTHEON_RUNTIME_UV_EXECUTABLE")):
        if field in manifest:
            values[name] = manifest[field]
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update({key: str(value) for key, value in values.items()})
    try:
        # 驗證入口沿正式 lifetime 持有工作鎖，Git 與 child 不可脫離同一 state root。
        with runtime_manifest.runtime_work_lease(Path(manifest["publisher_state_root"])):
            yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _load_contract(
    source: dict[str, Any],
) -> tuple[Path, dict[str, Any], Path, Path, Path, Path, dict[str, Any]]:
    manifest_path = Path(str(source.get("runtime_manifest", "")))
    sandbox_root = Path(str(source.get("sandbox_root", "")))
    if (
        not manifest_path.is_absolute()
        or not sandbox_root.is_absolute()
        or not sandbox_root.is_dir()
        or sandbox_root.resolve(strict=True) != sandbox_root
    ):
        raise AdapterBlocked("formal runtime sandbox is invalid")
    manifest = runtime_manifest.load_manifest(
        manifest_path,
        str(source.get("runtime_manifest_digest", "")),
    )
    if manifest["runtime_identity_digest"] != source.get(
        "runtime_identity_digest"
    ):
        raise AdapterBlocked("runtime identity digest mismatch")
    activation_token = Path(str(source.get("activation_token", "")))
    if not activation_token.is_absolute():
        raise AdapterBlocked("activation token is required")
    try:
        activation_receipt = runtime_manifest.validate_barrier(
            activation_token,
            manifest,
        )
    except runtime_manifest.RuntimeManifestError as error:
        raise AdapterBlocked(str(error)) from error
    try:
        queue_root = publisher._require_sandbox_descendant(
            sandbox_root, Path(manifest["queue_root"]), "queue root"
        )
        state_root = publisher._require_sandbox_descendant(
            sandbox_root,
            Path(manifest["publisher_state_root"]),
            "publisher state root",
        )
        if queue_root.is_relative_to(state_root) or state_root.is_relative_to(
            queue_root
        ):
            raise publisher.PublishBlocked("queue and publisher state roots overlap")
    except publisher.PublishBlocked as error:
        raise AdapterBlocked(str(error)) from error
    return (
        manifest_path,
        manifest,
        sandbox_root,
        queue_root,
        state_root,
        activation_token,
        activation_receipt,
    )


def _create_step(
    source: dict[str, Any],
    manifest_path: Path,
    manifest: dict[str, Any],
    sandbox_root: Path,
    activation_token: Path,
) -> dict[str, Any]:
    _prepare_offline_transport(sandbox_root)
    queue_root = Path(manifest["queue_root"])
    run_ids: dict[str, str] = {}
    states: dict[str, dict[str, Any]] = {}
    with _formal_environment(
        manifest_path,
        manifest,
        "com.pantheon.agy-gemini-coordinator",
        activation_token,
    ):
        for lane in coordinator.CONTENT_LANES:
            run_id = "probe-" + hashlib.sha256(
                f"{source['correlation_id']}:{lane}".encode()
            ).hexdigest()[:24]
            if lane == "i18n-new":
                record = multilingual.enqueue_article_translations(
                    Path(manifest["actor_root"]), queue_root,
                    source_run_id="offline-source-published_runs",
                    article_id=OFFLINE_ARTICLE_ID, locales=["en"], lane=lane,
                )[0]
                run_id = record["run_id"]
                namespace = hashlib.sha256(run_id.encode()).hexdigest()[:24]
                states[lane] = json.loads(
                    (queue_root / "runs" / f"{namespace}.json").read_text(encoding="utf-8")
                )
                run_ids[lane] = run_id
                continue
            if lane == "i18n-rewrite":
                brief_path = multilingual.prepare_translation_run(
                    Path(manifest["actor_root"]), run_id, OFFLINE_ARTICLE_ID, ["en"],
                    queue_root / "translation-runs",
                )
                brief = json.loads(brief_path.read_text(encoding="utf-8"))
                brief["lane"] = lane
                brief_path.write_text(json.dumps(brief), encoding="utf-8")
                run_dir = brief_path.parent
            else:
                run_dir = sandbox_root / "runs" / lane
                run_dir.mkdir(parents=True, exist_ok=True)
                (run_dir / "brief.json").write_text(json.dumps({
                    "schema_version": 1, "run_id": run_id,
                    "mode": "rewrite_existing_body" if lane == "rewrite" else "create",
                    "articles": [],
                }) + "\n", encoding="utf-8")
            states[lane] = coordinator.register_run(
                run_dir,
                queue_root,
                correlation_id=str(source["correlation_id"]),
            )
            run_ids[lane] = run_id
    return {
        "run_ids": run_ids,
        "coordinator_states": states,
        "production_entrypoints": [
            "scripts.agy_gemini_coordinator:register_run",
            "scripts.agy_multilingual_pipeline:enqueue_article_translations",
        ],
    }


def _long(text: str) -> str:
    value = text
    while len(value) < 96:
        value += "再核對一項具體資料，避免把通用描述當成個人結論。"
    return value[:108]

def _offline_ready_article(article_id: str = "AUTO-001") -> dict[str, object]:
    keyword = "測試關鍵字"
    scene_seeds = [
        "在工作會議收到臨時訊息時，先記錄期限、核對責任並確認仍缺少的資料。",
        "下班看到帳單與課程通知時，先列出支出、比較選項並安排可調整的順序。",
        "收到伴侶回覆時，先等待情緒緩和、詢問彼此期待，再談清楚分工。",
        "若現實資料不足，這個工具就不適用；先暫停推測並回到可查證的事實。",
    ]
    paragraphs = [
        _long(
            f"{keyword}在 {article_id} 測試案例中，"
            f"{scene_seeds[index % len(scene_seeds)]}"
        )
        for index in range(15)
    ]
    article = {
        "id": article_id,
        "section": "mbti",
        "product": "personality",
        "slug": article_id.lower(),
        "serial": "personality-9999",
        "urlSlug": f"{article_id.lower()}-9999",
        "primaryKeyword": keyword,
        "secondaryKeywords": ["具體場景", "通用觀察"],
        "title": "測試關鍵字是什麼？用生活場景理解限制與選擇",
        "description": "測試關鍵字適合整理具體情境、可觀察行動與使用限制；本文只提供通用理解，不替個人下結論，也不承諾任何結果，仍需回到現況判斷與實際資料再做選擇。",
        "answer": "測試關鍵字提供通用觀察，不能替個人下結論。",
        "tags": ["AEO", "GEO", "Pantheon", "SEO", "公開文章", "繁體中文", "通用知識", "人格", "自我理解"],
        "published": "2026-07-23",
        "updated": "2026-07-23",
        "faq": [
            {"question": "測試關鍵字能直接判定結果嗎？", "answer": "不能，仍要回到實際情境與行動。"},
            {"question": "應該先看什麼？", "answer": "先分開記錄事實、推測與期待。"},
            {"question": "什麼時候不適用？", "answer": "需要專業判斷時不應只靠這篇文章。"},
        ],
        "bodySections": [
            {"heading": f"測試關鍵字的觀察角度 {section + 1}", "paragraphs": paragraphs[section * 3 : section * 3 + 3]}
            for section in range(5)
        ],
    }
    article["publicationPolicy"] = pipeline._hydrate_create_publication_policy({"target": article})
    return article


def prepare_ready_fixture(queue_root: Path, sandbox_root: Path, run_id: str) -> None:
    """只將合成 create lane 補成身份一致、單篇且經現役規則驗證的 ready fixture。"""
    namespace = hashlib.sha256(run_id.encode()).hexdigest()[:24]
    state_path = queue_root / "runs" / f"{namespace}.json"
    state = json.loads(state_path.read_text())
    run_dir = publisher._require_sandbox_descendant(sandbox_root, Path(state["run_dir"]), "fixture run root")
    if state["run_id"] != run_id:
        raise AdapterBlocked("ready fixture state identity mismatch")
    article = _offline_ready_article("PROBE-READY-001")
    candidate = {"schema_version": 1, "run_id": run_id, "mode": "create", "articles": [article]}
    review = {"schema_version": 1, "run_id": run_id, "articles": [{
        "article_id": article["id"], "candidate_sha256": pipeline.article_sha256(article),
        "verdict": "APPROVE", "hard_failure": False, "findings": [],
    }]}
    pipeline.validate_candidate(candidate)
    pipeline.validate_review(review, candidate["articles"])
    for name, payload in (("candidate.json", candidate), ("review.json", review)):
        (run_dir / name).write_text(json.dumps(payload, ensure_ascii=False) + "\n")
    state.update(status="complete", result={"status": "complete", "run_id": run_id,
                                           "candidate": str(run_dir / "candidate.json")})
    state_path.write_text(json.dumps(state, ensure_ascii=False) + "\n")


def _run_step(
    source: dict[str, Any],
    manifest_path: Path,
    manifest: dict[str, Any],
    sandbox_root: Path,
    activation_token: Path,
) -> dict[str, Any]:
    run_ids = source.get("run_ids")
    if not isinstance(run_ids, dict) or set(run_ids) != set(coordinator.CONTENT_LANES):
        raise AdapterBlocked("four-lane run identity is incomplete")
    results: dict[str, dict[str, Any]] = {}
    for lane, run_id in run_ids.items():
        lane_root = Path(manifest["queue_root"]) / "lanes" / lane
        with _formal_environment(
            manifest_path,
            manifest,
            f"com.pantheon.agy-gemini-{lane}",
            activation_token,
        ), _offline_transport(sandbox_root) as model:
            runtime_manifest.validate_runtime_tick(
                f"com.pantheon.agy-gemini-{lane}",
                queue_root=lane_root,
                state_root=Path(manifest["publisher_state_root"]),
                actor_root=Path(manifest["actor_root"]),
                log_root=Path(manifest["log_root"]),
            )
            request = create_external_request(
                lane_root,
                namespace=hashlib.sha256(str(run_id).encode()).hexdigest()[:24],
                role="writer",
                model=model,
                prompt=f"bounded formal runtime {lane}",
                response_schema=RESPONSE_SCHEMA,
            )
            result = runner.process_once(
                lane_root,
                lane=lane,
                exact_run_ids=[str(run_id)],
            )
        if result.get("status") != "processed":
            raise AdapterBlocked(f"{lane} production runner did not process: {result}")
        results[lane] = {**result, "request_sha256": request["request_sha256"]}
    prepare_ready_fixture(Path(manifest["queue_root"]), sandbox_root, str(run_ids["new"]))
    return {
        "run_ids": run_ids,
        "publish_run_ids": [run_ids["new"]],
        "publish_max_runs": 1,
        "lane_results": results,
        "production_entrypoints": [
            "scripts.agy_gemini_outbox:create_external_request",
            "scripts.agy_gemini_runner:process_once",
        ],
    }


def _publisher_step(
    capability: str,
    source: dict[str, Any],
    manifest_path: Path,
    manifest: dict[str, Any],
    sandbox_root: Path,
    queue_root: Path,
    state_root: Path,
    activation_token: Path,
    activation_receipt: dict[str, Any],
) -> dict[str, Any]:
    run_ids = source.get("run_ids")
    if not isinstance(run_ids, dict):
        raise AdapterBlocked("publisher run identity is missing")
    with _formal_environment(
        manifest_path,
        manifest,
        "com.pantheon.agy-content-publisher",
        activation_token,
    ):
        runtime_receipt = runtime_manifest.validate_runtime_tick(
            "com.pantheon.agy-content-publisher",
            queue_root=Path(manifest["queue_root"]),
            state_root=Path(manifest["publisher_state_root"]),
            actor_root=Path(manifest["actor_root"]),
            log_root=Path(manifest["log_root"]),
        )
        result = publisher.formal_capability_preflight(
            "select" if capability == "publish" else capability,
            run_ids=(source["publish_run_ids"] if capability == "publish" else run_ids.values()),
            correlation_id=str(source["correlation_id"]),
            trusted_sandbox_root=sandbox_root,
            queue_root=queue_root,
            state_root=state_root,
            runtime_receipt=runtime_receipt,
        )
        if capability == "publish":
            selected = source["publish_run_ids"]
            actor_root = Path(manifest["actor_root"])
            actor_sha = publisher.run_git(actor_root, ["rev-parse", "HEAD"], None)
            if actor_sha != manifest["actor_head"]:
                raise AdapterBlocked("publisher actor runtime identity mismatch")
            git_trace: list[list[str]] = []
            with publisher.TrustedSandboxDirectoryAuthority(sandbox_root) as authority:
                lock_relative = (state_root / "publisher.lock").relative_to(sandbox_root)
                lock_before = authority.exists(lock_relative)

                def dry_run_git(repo: Path, args: list[str], input_text: str | None = None) -> str:
                    authority.assert_current()
                    git_trace.append(list(args))
                    return publisher._formal_capability_dry_run_git(
                        actor_root, sandbox_root, actor_sha, repo, args, input_text,
                        sandbox_authority=authority,
                    )

                published = publisher.publish_ready_runs(
                    actor_root, queue_root, state_root,
                    max_runs=source["publish_max_runs"], exact_run_ids=selected,
                    dry_run=True, push=False, run_tests=False, release_gate=False,
                    git=dry_run_git, seed_translations=False,
                )
                authority.assert_current()
                sandbox_mutation = lock_before != authority.exists(lock_relative)
            if (selected != [run_ids.get("new")]
                    or published.get("status") != "dry-run"
                    or published.get("ready_runs") != selected
                    or published.get("base_sha") != actor_sha):
                raise AdapterBlocked("publisher requires one exact ready dry-run; idle is not evidence")
            result = {
                **result, "capability": "publish", "boundary_status": "dry-run",
                "publisher_result": published, "max_runs": source["publish_max_runs"],
                "sandbox_mutation": result["sandbox_mutation"] or sandbox_mutation,
                "called_entrypoints": [*result["called_entrypoints"],
                                       "scripts.agy_content_publisher:publish_ready_runs"],
                "git_trace": [*result["git_trace"], *git_trace],
            }
    entrypoints = [
        str(result["entrypoint"]),
        *(str(value) for value in result.get("called_entrypoints", [])),
    ]
    output: dict[str, Any] = {
        "run_ids": run_ids,
        "publisher_result": result,
        "runtime_receipt": runtime_receipt,
        "production_entrypoints": entrypoints,
        "production_mutation": result["production_mutation"],
        "sandbox_mutation": result["sandbox_mutation"],
    }
    if result["production_mutation"]:
        raise AdapterBlocked("production mutation detected")
    if capability == "transaction":
        def fixture_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
            if command[:2] == ["launchctl", "print"]:
                return subprocess.CompletedProcess(command, 3, "", "")
            if command[:3] == ["sysctl", "-n", "vm.swapusage"]:
                return subprocess.CompletedProcess(
                    command,
                    0,
                    "total = 0.00M used = 0.00M free = 0.00M\n",
                    "",
                )
            return subprocess.CompletedProcess(command, 1, "", "unexpected command")

        def fixture_capacity(_path: Path) -> dict[str, Any]:
            return {
                "disk_total_bytes": 200 * capacity_guard.GIB,
                "disk_free_bytes": 100 * capacity_guard.GIB,
                "admission_available_bytes": 100 * capacity_guard.GIB,
                "capacity_source": "offline_fixture",
                "capacity_available": True,
                "capacity_error": None,
            }

        with _formal_environment(
            manifest_path,
            manifest,
            "com.pantheon.content-capacity-guard",
            activation_token,
        ):
            runtime_manifest.validate_runtime_tick(
                "com.pantheon.content-capacity-guard",
                queue_root=Path(manifest["queue_root"]),
                state_root=Path(manifest["publisher_state_root"]),
                actor_root=Path(manifest["actor_root"]),
                log_root=Path(manifest["log_root"]),
            )
            guard_result = capacity_guard.preflight(
                Path(manifest["queue_root"]),
                Path(manifest["publisher_state_root"]),
                Path(manifest["log_root"]),
                runner=fixture_runner,
                capacity_sensor=fixture_capacity,
            )
        if guard_result.get("status") != "PASS":
            raise AdapterBlocked("capacity guard production preflight failed")
        output["capacity_guard"] = guard_result
        output["production_entrypoints"].append(
            "scripts.pantheon_content_capacity_guard:preflight"
        )
    output["activation_receipt"] = activation_receipt
    return output


def _production_transition(
    capability: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    (
        manifest_path,
        manifest,
        sandbox_root,
        queue_root,
        state_root,
        activation_token,
        activation_receipt,
    ) = _load_contract(source)
    if capability == "create":
        return _create_step(
            source,
            manifest_path,
            manifest,
            sandbox_root,
            activation_token,
        )
    if capability == "run":
        return _run_step(
            source,
            manifest_path,
            manifest,
            sandbox_root,
            activation_token,
        )
    return _publisher_step(
        capability,
        source,
        manifest_path,
        manifest,
        sandbox_root,
        queue_root,
        state_root,
        activation_token,
        activation_receipt,
    )


def invoke(
    *,
    capability: str,
    input_path: Path,
    output_path: Path,
    expected_input_digest: str,
    actual_input_digest: str,
    execution_id: str,
    correlation_id: str,
    actor_identity: str,
    transition: Callable[[str, dict[str, Any]], dict[str, Any]] = _production_transition,
) -> dict[str, Any]:
    if capability not in CAPABILITIES:
        raise AdapterBlocked("capability is not registered")
    source = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(source, dict):
        raise AdapterBlocked("adapter input must be an object")
    if actual_input_digest != expected_input_digest:
        raise AdapterBlocked("input digest mismatch")
    if source.get("output_digest") != actual_input_digest:
        raise AdapterBlocked("input artifact digest mismatch")
    for field, value in (
        ("execution_id", execution_id),
        ("correlation_id", correlation_id),
        ("actor_identity", actor_identity),
    ):
        if source.get(field) != value:
            raise AdapterBlocked(f"{field} mismatch")
    if source.get("capability") != PREVIOUS[capability]:
        raise AdapterBlocked("previous capability mismatch")
    transition_result = transition(capability, source)
    payload: dict[str, Any] = {
        **source,
        "schema_version": 2,
        "capability": capability,
        "input_digest": actual_input_digest,
        "expected_input_digest": expected_input_digest,
        "entrypoint_outcome": "PASS",
        "mode": "formal-runtime-production-dry-run",
        "production_mutation": False,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        **transition_result,
    }
    payload.pop("output_digest", None)
    payload["output_digest"] = _digest(payload)
    output_path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capability", choices=CAPABILITIES, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-input-digest", required=True)
    parser.add_argument("--actual-input-digest", required=True)
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--correlation-id", required=True)
    parser.add_argument("--actor-identity", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = invoke(
            capability=args.capability,
            input_path=args.input,
            output_path=args.output,
            expected_input_digest=args.expected_input_digest,
            actual_input_digest=args.actual_input_digest,
            execution_id=args.execution_id,
            correlation_id=args.correlation_id,
            actor_identity=args.actor_identity,
        )
    except (AdapterBlocked, OSError, json.JSONDecodeError, KeyError, ValueError) as error:
        blocked = {
            "schema_version": 2,
            "capability": args.capability,
            "execution_id": args.execution_id,
            "correlation_id": args.correlation_id,
            "actor_identity": args.actor_identity,
            "input_digest": args.actual_input_digest,
            "expected_input_digest": args.expected_input_digest,
            "entrypoint_outcome": "BLOCKED",
            "output_digest": "",
            "error": str(error),
            "mode": "formal-runtime-production-dry-run",
            "production_mutation": False,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        }
        args.output.write_text(
            json.dumps(blocked, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(blocked, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
