#!/usr/bin/env python3
"""渲染並驗證一次性、可完全 teardown 的四軌 acceptance cohort。"""
from __future__ import annotations

from contextlib import suppress
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import stat
import time
from typing import Any, Callable, Mapping

from scripts import pantheon_content_runtime_manifest as runtime

LANES = ("new", "rewrite", "i18n-new", "i18n-rewrite")
PUBLISHER = "com.pantheon.agy-content-publisher"
COORDINATOR = "com.pantheon.agy-gemini-coordinator"
CAPACITY = "com.pantheon.content-capacity-guard"
SERVICE_LABELS = runtime.SERVICE_LABELS
PRODUCTION_ROOT_KEYS = frozenset(("queue", "ledger", "publisher", "public"))
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class AcceptanceBlocked(ValueError):
    """disposable acceptance 契約不成立。"""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_dir(path: Path, label: str) -> Path:
    if not path.is_absolute() or not path.is_dir() or path.is_symlink():
        raise AcceptanceBlocked(f"{label} must be an absolute canonical directory")
    resolved = path.resolve(strict=True)
    if resolved != path:
        raise AcceptanceBlocked(f"{label} must use canonical realpath")
    mode = stat.S_IMODE(path.stat().st_mode)
    if path.stat().st_uid != os.getuid() or mode & 0o022:
        raise AcceptanceBlocked(f"{label} is not owner-safe")
    return resolved


def _canonical_file(path: Path, label: str) -> Path:
    if not path.is_absolute() or not path.is_file() or path.is_symlink() or path.resolve(strict=True) != path:
        raise AcceptanceBlocked(f"{label} must be an absolute canonical regular file")
    if path.stat().st_uid != os.getuid() or stat.S_IMODE(path.stat().st_mode) & 0o022:
        raise AcceptanceBlocked(f"{label} is not owner-safe")
    return path


def _descendant(path: Path, root: Path, label: str) -> Path:
    resolved = _canonical_dir(path, label)
    if resolved == root or not resolved.is_relative_to(root):
        raise AcceptanceBlocked(f"{label} must be a strict acceptance descendant")
    return resolved


def _overlap(left: Path, right: Path) -> bool:
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def _write_plist(path: Path, payload: dict[str, Any]) -> None:
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        data = plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True)
        view = memoryview(data)
        while view:
            view = view[os.write(descriptor, view):]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _tree_digest(root: Path) -> str:
    """非 follow lstat snapshot；涵蓋空目錄、metadata 與 symlink target。"""
    root = _canonical_dir(root, "production root")
    rows: list[dict[str, Any]] = []
    for path in [root, *sorted(root.rglob("*"))]:
        info = os.lstat(path)
        mode = stat.S_IFMT(info.st_mode)
        kind = "dir" if stat.S_ISDIR(info.st_mode) else "file" if stat.S_ISREG(info.st_mode) else "symlink" if stat.S_ISLNK(info.st_mode) else "other"
        if kind == "other":
            raise AcceptanceBlocked("production fingerprint contains unsupported entry")
        row: dict[str, Any] = {"path": "." if path == root else str(path.relative_to(root)), "type": kind, "uid": info.st_uid, "gid": info.st_gid, "mode": stat.S_IMODE(info.st_mode), "mtime_ns": info.st_mtime_ns, "size": info.st_size}
        if kind == "file": row["sha256"] = _sha(path)
        if kind == "symlink": row["target"] = os.readlink(path)
        rows.append(row)
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def production_fingerprint(paths: Mapping[str, Path], service_state: Callable[[], Mapping[str, Any]]) -> dict[str, Any]:
    if set(paths) != PRODUCTION_ROOT_KEYS:
        raise AcceptanceBlocked("production root keys differ")
    roots = {
        name: {
            "canonical_path": str(_canonical_dir(Path(value), f"production {name}")),
            "tree_digest": _tree_digest(Path(value)),
        }
        for name, value in sorted(paths.items())
    }
    identities_digest = hashlib.sha256(json.dumps(roots, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    state = service_state()
    if not isinstance(state, Mapping): raise AcceptanceBlocked("production service state is invalid")
    state_digest = hashlib.sha256(json.dumps(state, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "root_identities": roots,
        "root_identities_digest": identities_digest,
        "filesystem_digest": identities_digest,
        "service_state_digest": state_digest,
    }


def _env(manifest: Mapping[str, Any], label: str, barrier: Path) -> dict[str, str]:
    fields = {"PANTHEON_RUNTIME_MANIFEST": "manifest_path", "PANTHEON_RUNTIME_MANIFEST_DIGEST": "manifest_digest", "PANTHEON_RUNTIME_IDENTITY": "identity", "PANTHEON_RUNTIME_IDENTITY_DIGEST": "runtime_identity_digest", "PANTHEON_RUNTIME_CODE_DIGEST": "runtime_digest", "PANTHEON_RUNTIME_CONFIG_VERSION": "config_version", "PANTHEON_RUNTIME_GENERATION": "generation", "PANTHEON_RUNTIME_ACTOR_ROOT": "actor_root", "PANTHEON_RUNTIME_QUEUE_ROOT": "queue_root", "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": "publisher_state_root", "PANTHEON_RUNTIME_LOG_ROOT": "log_root"}
    result = {key: str(manifest[value]) for key, value in fields.items()}
    result.update({"PANTHEON_FORMAL_RUNTIME": "1", "PANTHEON_RUNTIME_SERVICE_LABEL": label, "PANTHEON_RUNTIME_ACTIVATION_TOKEN": str(barrier)})
    for key in ("actor_head", "python_executable", "uv_executable"):
        if key in manifest: result["PANTHEON_RUNTIME_" + key.upper()] = str(manifest[key])
    return result


def _prefix(python: str, manifest: Mapping[str, Any], label: str, barrier: Path, ready: Path, activation_only: bool) -> list[str]:
    value = [python, "-m", "scripts.pantheon_content_runtime_manifest", "barrier-exec", "--barrier", str(barrier), "--expected-digest", str(manifest["manifest_digest"]), "--manifest", str(manifest["manifest_path"]), "--service-label", label, "--ready-root", str(ready), "--timeout", "1"]
    return [*value, *( ["--activation-only"] if activation_only else [])]


def _binding(value: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, str]:
    required = {"lane", "run_id", "bundle", "bundle_digest", "actor_digest", "generation", "identity_digest"}
    if set(value) != required: raise AcceptanceBlocked("lane binding fields differ")
    lane, run_id = str(value["lane"]), str(value["run_id"])
    bundle = _canonical_file(Path(str(value["bundle"])), "sealed bundle")
    if lane not in LANES or not run_id or _sha(bundle) != str(value["bundle_digest"]): raise AcceptanceBlocked("sealed lane binding differs")
    if (str(value["actor_digest"]), str(value["generation"]), str(value["identity_digest"])) != (str(manifest["runtime_digest"]), str(manifest["generation"]), str(manifest["runtime_identity_digest"])): raise AcceptanceBlocked("sealed binding identity differs")
    return {"lane": lane, "run_id": run_id, "bundle": str(bundle), "bundle_digest": str(value["bundle_digest"])}


def _validate_children(paths: list[Path], bindings: list[dict[str, str]], manifest: Mapping[str, Any], publisher_run_id: str) -> None:
    by_label = {path.stem: plistlib.loads(path.read_bytes())["ProgramArguments"] for path in paths}
    child = lambda arguments: arguments[arguments.index("--") + 1 :]
    values = lambda arguments, flag: [arguments[index + 1] for index, value in enumerate(arguments[:-1]) if value == flag]
    coordinator = child(by_label[COORDINATOR])
    if values(coordinator, "--exact-run-id") != [item["run_id"] for item in bindings] or coordinator.count("--external-workers-only") != 1 or coordinator.count("cycle") != 1 or any(flag in coordinator for flag in ("--new-matrix-sweep", "--legacy-sweep")): raise AcceptanceBlocked("coordinator child exact contract differs")
    for item in bindings:
        runner_child = child(by_label[f"com.pantheon.agy-gemini-{item['lane']}"])
        expected_root = str(Path(manifest["queue_root"]) / "lanes" / item["lane"])
        if runner_child.count("--exact-run-id") != 1 or "sealed-replay-bundle-process-once" not in runner_child or "process-once" in runner_child or "operator-exact-process-once" in runner_child or expected_root not in runner_child or item["run_id"] not in runner_child or item["bundle"] not in runner_child or item["bundle_digest"] not in runner_child: raise AcceptanceBlocked("runner child exact contract differs")
    publisher = child(by_label[PUBLISHER])
    if values(publisher, "--max-runs") != ["1"] or values(publisher, "--exact-run-id") != [publisher_run_id] or "--push" in publisher: raise AcceptanceBlocked("publisher child exact contract differs")
    capacity = child(by_label[CAPACITY])
    if capacity[-1] != "preflight" or str(manifest["queue_root"]) not in capacity or str(manifest["publisher_state_root"]) not in capacity: raise AcceptanceBlocked("capacity child exact contract differs")


def _session_plan(
    *, path: Path, expected_digest: str, root: Path, manifest: Mapping[str, Any],
    bindings: list[dict[str, str]], publisher_run_id: str, productions: Mapping[str, Path],
) -> tuple[dict[str, Any], str]:
    plan_path = _canonical_file(path, "acceptance session plan")
    if not plan_path.is_relative_to(root) or SHA256_PATTERN.fullmatch(expected_digest) is None:
        raise AcceptanceBlocked("acceptance session plan authority is invalid")
    actual_digest = _sha(plan_path)
    if actual_digest != expected_digest:
        raise AcceptanceBlocked("acceptance session plan digest differs")
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise AcceptanceBlocked("acceptance session plan is invalid") from error
    required = {"schema_version", "session_id", "session_nonce_digest", "generation", "actor_sha", "manifest_digest", "runtime_identity_digest", "service_labels", "exact_runs", "publisher_run_id", "roots"}
    if not isinstance(plan, dict) or set(plan) != required or plan.get("schema_version") != 1:
        raise AcceptanceBlocked("acceptance session plan fields differ")
    nonce = plan.get("session_nonce_digest")
    if not isinstance(nonce, str) or SHA256_PATTERN.fullmatch(nonce) is None:
        raise AcceptanceBlocked("acceptance session nonce differs")
    generation = f"acceptance-{nonce[:32]}"
    if plan.get("generation") != generation or plan.get("session_id") != f"four-lane-acceptance-{nonce[:32]}":
        raise AcceptanceBlocked("acceptance session generation differs")
    expected_roots = {
        "acceptance_root": str(root), "actor_root": str(manifest["actor_root"]),
        "queue_root": str(manifest["queue_root"]), "publisher_state_root": str(manifest["publisher_state_root"]),
        "log_root": str(manifest["log_root"]),
        **{f"production_{name}": str(value) for name, value in productions.items()},
    }
    expected_runs = [{"lane": item["lane"], "run_id": item["run_id"], "bundle_digest": item["bundle_digest"]} for item in bindings]
    if plan.get("actor_sha") != manifest.get("actor_head") or plan.get("manifest_digest") != manifest["manifest_digest"] or plan.get("runtime_identity_digest") != manifest["runtime_identity_digest"] or plan.get("generation") != manifest["generation"] or plan.get("service_labels") != list(SERVICE_LABELS) or plan.get("exact_runs") != expected_runs or plan.get("publisher_run_id") != publisher_run_id or plan.get("roots") != expected_roots:
        raise AcceptanceBlocked("acceptance session plan binding differs")
    return plan, actual_digest


def render_plists(*, manifest_path: Path, expected_manifest_digest: str, acceptance_root: Path, bindings: list[Mapping[str, Any]], publisher_run_id: str, production_paths: Mapping[str, Path], session_plan_path: Path, expected_session_plan_digest: str) -> dict[str, Any]:
    root = _canonical_dir(acceptance_root, "acceptance root")
    if set(production_paths) != PRODUCTION_ROOT_KEYS:
        raise AcceptanceBlocked("production root keys differ")
    manifest_file = _canonical_file(manifest_path, "disposable manifest")
    if not manifest_file.is_relative_to(root):
        raise AcceptanceBlocked("disposable manifest must be an acceptance descendant")
    manifest = {**runtime.load_manifest(manifest_path, expected_manifest_digest), "manifest_path": str(manifest_path)}
    owned = {name: _descendant(Path(manifest[field]), root, name) for name, field in (("queue", "queue_root"), ("state", "publisher_state_root"), ("logs", "log_root"))}
    productions = {name: _canonical_dir(Path(value), f"production {name}") for name, value in production_paths.items()}
    if any(_overlap(root, production) or any(_overlap(owned_path, production) for owned_path in owned.values()) for production in productions.values()) or any(_overlap(left, right) for index, left in enumerate(productions.values()) for right in list(productions.values())[index + 1 :]): raise AcceptanceBlocked("acceptance or production roots overlap")
    parsed = [_binding(item, manifest) for item in bindings]
    if {item["lane"] for item in parsed} != set(LANES) or len({item["run_id"] for item in parsed}) != 4 or len({item["bundle"] for item in parsed}) != 4 or not publisher_run_id: raise AcceptanceBlocked("acceptance exact bindings differ")
    plan, plan_digest = _session_plan(path=session_plan_path, expected_digest=expected_session_plan_digest, root=root, manifest=manifest, bindings=parsed, publisher_run_id=publisher_run_id, productions=productions)
    generation = str(plan["generation"])
    plist_parent, readiness_parent, barrier_parent, lock_parent, evidence_parent = (root / "plists", root / "readiness", root / "barriers", root / "locks", root / "evidence")
    for path, label in ((plist_parent, "plist parent"), (readiness_parent, "readiness parent"), (barrier_parent, "barrier parent"), (lock_parent, "lock parent"), (evidence_parent, "evidence parent")):
        _descendant(path, root, label)
    final, staging = plist_parent / generation, root / f".plists-staging.{generation}"
    ready, barrier, lock, evidence = readiness_parent / generation, barrier_parent / f"{generation}.json", lock_parent / f"{generation}.lock", evidence_parent / generation
    if any(path.exists() for path in (final, staging, ready, barrier, lock, evidence)):
        raise AcceptanceBlocked("acceptance residue exists before render")
    staging.mkdir(mode=0o700)
    python = str(manifest.get("python_executable") or os.sys.executable)
    children: dict[str, list[str]] = {COORDINATOR: [python,"-m","scripts.agy_gemini_coordinator","--queue-root",str(manifest["queue_root"]),"--repo-root",str(manifest["actor_root"]),"cycle",*(token for item in parsed for token in ("--exact-run-id",item["run_id"])),"--external-workers-only"], PUBLISHER: [python,"-m","scripts.agy_content_publisher","--repo-root",str(manifest["actor_root"]),"--queue-root",str(manifest["queue_root"]),"--state-root",str(manifest["publisher_state_root"]),"--max-runs","1","--exact-run-id",publisher_run_id], CAPACITY: [python,"-m","scripts.pantheon_content_capacity_guard","--queue-root",str(manifest["queue_root"]),"--publisher-root",str(manifest["publisher_state_root"]),"--log-root",str(manifest["log_root"]),"preflight"]}
    for item in parsed: children[f"com.pantheon.agy-gemini-{item['lane']}"] = [python,"-m","scripts.agy_gemini_runner","--queue-root",str(Path(manifest["queue_root"])/"lanes"/item["lane"]),"--lane",item["lane"],"--exact-run-id",item["run_id"],"sealed-replay-bundle-process-once","--bundle",item["bundle"],"--expected-bundle-digest",item["bundle_digest"]]
    paths: list[Path] = []
    try:
        for label in SERVICE_LABELS:
            activation_only = label == PUBLISHER
            path = staging / f"{label}.plist"
            _write_plist(path, {"Label": label, "ProgramArguments": [*_prefix(python,manifest,label,barrier,ready,activation_only),"--",*children[label]], "EnvironmentVariables": _env(manifest,label,barrier), "WorkingDirectory": str(manifest["actor_root"]), "RunAtLoad": False})
            paths.append(path)
        receipts = [runtime.plist_receipt(path, expected_activation_mode="activation-only" if path.stem == PUBLISHER else "normal") for path in paths]
        runtime.validate_receipts(manifest, [{key:value for key,value in item.items() if key != "plist_realpath"} for item in receipts])
        runtime.publisher_plist_receipt(staging / f"{PUBLISHER}.plist", expected_activation_mode="activation-only")
        _validate_children(paths, parsed, manifest, publisher_run_id)
        _fsync_directory(staging)
        os.replace(staging, final)
        _fsync_directory(root)
    except Exception:
        with suppress(FileNotFoundError):
            for path in staging.iterdir(): path.unlink()
            staging.rmdir()
        raise
    return {"manifest":manifest,"acceptance_root":root,"plist_paths":[final/path.name for path in paths],"ready_root":ready,"evidence_root":evidence,"barrier":barrier,"lock":lock,"bindings":parsed,"production_paths":productions,"session_plan":plan,"session_plan_path":Path(session_plan_path),"session_plan_digest":plan_digest,"publisher_run_id":publisher_run_id}


def run_once(rendered: Mapping[str, Any], *, launch: Callable[[str,Path],None], bootout: Callable[[str],None], production_service_state: Callable[[],Mapping[str,Any]], monotonic: Callable[[],float]=time.monotonic, sleep: Callable[[float],None]=time.sleep) -> dict[str, Any]:
    root = _canonical_dir(Path(rendered["acceptance_root"]), "acceptance root")
    plan, plan_digest = _session_plan(path=Path(rendered["session_plan_path"]), expected_digest=str(rendered["session_plan_digest"]), root=root, manifest=rendered["manifest"], bindings=rendered["bindings"], publisher_run_id=str(rendered["publisher_run_id"]), productions=rendered["production_paths"])
    if plan != rendered["session_plan"] or plan_digest != rendered["session_plan_digest"]:
        raise AcceptanceBlocked("acceptance session plan revalidation differs")
    generation = str(plan["generation"])
    ready, barrier, lock, evidence = Path(rendered["ready_root"]), Path(rendered["barrier"]), Path(rendered["lock"]), Path(rendered["evidence_root"])
    if ready != root / "readiness" / generation or barrier != root / "barriers" / f"{generation}.json" or lock != root / "locks" / f"{generation}.lock" or evidence != root / "evidence" / generation:
        raise AcceptanceBlocked("acceptance session authority differs")
    if ready.exists() or barrier.exists() or lock.exists() or evidence.exists():
        raise AcceptanceBlocked("acceptance generation residue exists before launch")
    before = production_fingerprint(rendered["production_paths"], production_service_state)
    os.close(os.open(lock, os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)); launched: list[str]=[]; primary: Exception|None=None; teardown: list[str]=[]; result: dict[str,Any]|None=None
    try:
        for path in rendered["plist_paths"]: launch(path.stem,path); launched.append(path.stem)
        deadline=monotonic()+1
        while any(not (ready/f"{label}.json").is_file() for label in SERVICE_LABELS):
            if monotonic()>=deadline: raise AcceptanceBlocked("readiness timeout")
            sleep(0.01)
        if {path.name for path in ready.iterdir()} != {f"{label}.json" for label in SERVICE_LABELS}:
            raise AcceptanceBlocked("readiness acknowledgement set differs")
        activation=runtime.activate_barrier(barrier,ready,dict(rendered["manifest"])); result={"status":"PASS","activation_token_digest":runtime.validate_barrier(barrier,dict(rendered["manifest"]))["activation_token_digest"],"ack_digests":[item["ack_digest"] for item in activation["acknowledgements"]],"launched":list(launched),"bootouts":[]}
    except Exception as error: primary=error
    for label in reversed(launched):
        try: bootout(label); result and result["bootouts"].append(label)
        except Exception as error: teardown.append(f"{label}:{error}")
    known_ready={f"{label}.json" for label in SERVICE_LABELS}
    unknown=[] if not ready.exists() else [path.name for path in ready.iterdir() if path.name not in known_ready]
    for name in known_ready:
        with suppress(FileNotFoundError): (ready/name).unlink()
    if ready.exists() and not unknown:
        with suppress(OSError): ready.rmdir()
    for path in (barrier,lock):
        with suppress(FileNotFoundError): path.unlink()
    plist_root=Path(rendered["plist_paths"][0]).parent
    if plist_root.exists() and {path.name for path in plist_root.iterdir()}=={f"{label}.plist" for label in SERVICE_LABELS}:
        for path in plist_root.iterdir(): path.unlink()
        plist_root.rmdir()
    else: unknown.append("plists")
    after=production_fingerprint(rendered["production_paths"],production_service_state)
    if primary is not None:
        if teardown or unknown: raise AcceptanceBlocked(f"acceptance failed after {primary}: teardown residue: "+",".join([*teardown,*unknown])) from primary
        raise primary
    if len(launched)!=7 or not result or len(result["bootouts"])!=7 or teardown or unknown or before!=after or evidence.exists():
        raise AcceptanceBlocked("acceptance teardown or fingerprint proof failed")
    receipt={**result,"session_id":plan["session_id"],"session_nonce_digest":plan["session_nonce_digest"],"session_plan_path":str(rendered["session_plan_path"]),"session_plan_digest":plan_digest,"actor_sha":plan["actor_sha"],"exact_runs":plan["exact_runs"],"publisher_run_id":plan["publisher_run_id"],"service_labels":list(SERVICE_LABELS),"before_fingerprint":before,"after_fingerprint":after,"production_root_identities":before["root_identities"],"production_root_identities_digest":before["root_identities_digest"],"teardown_terminal":True,"residue_free":True,"manifest_digest":rendered["manifest"]["manifest_digest"],"generation":rendered["manifest"]["generation"],"runtime_identity_digest":rendered["manifest"]["runtime_identity_digest"]}
    evidence.mkdir(mode=0o700)
    output=evidence/"one-shot-session-receipt.json"
    descriptor=os.open(output,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        view=memoryview(json.dumps(receipt,sort_keys=True,separators=(",",":")).encode()+b"\n")
        while view:
            view=view[os.write(descriptor,view):]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_directory(evidence)
    return receipt
