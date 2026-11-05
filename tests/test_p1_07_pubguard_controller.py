"""離線 unit：合成 git／launchd runner，不代表真 wrapper、Git 或 production 驗收。"""
from __future__ import annotations

from dataclasses import replace
import importlib.util
import io
from contextlib import contextmanager, redirect_stderr
import json
import os
from pathlib import Path
import plistlib
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = Path(os.environ.get("P1_07_RUNTIME_ROOT", str(ROOT))).resolve()
sys.path.insert(0, str(RUNTIME_ROOT))
CONTROLLER_PATH = ROOT / "pantheon_content_runtime_promotion.py"
if not CONTROLLER_PATH.exists():
    CONTROLLER_PATH = ROOT / "scripts" / "pantheon_content_runtime_promotion.py"
SPEC = importlib.util.spec_from_file_location("pubguard_controller_under_test", CONTROLLER_PATH)
controller = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = controller
SPEC.loader.exec_module(controller)
manifest = controller.runtime_manifest
activation = controller._pg_activation()
PAIR = controller.PUBGUARD_LABELS
OLD = "1" * 40
TARGET = "2" * 40


class LaunchdUnitRunner:
    """只模擬 injected runner 邊界；所有可寫路徑皆是本測試的暫存 fixture。"""
    def __init__(self, case):
        self.case = case
        self.remote = OLD
        self.loaded = {label: label in PAIR for label in manifest.SERVICE_LABELS}
        self.commands = []
        self.bootstrap_failure = None
        self.timeout_after_bootstrap = None
        self.signal_after_bootstrap = None
        self.skip_ack = False
        self.fast_forward = True
        self.health_under_ex = []
        self.push_behavior = "accepted"
        self.push_under_ex = []
        self.publisher_running = False
        self.publisher_exit = 0

    def __call__(self, argv, *, timeout):
        assert timeout > 0
        self.commands.append(list(argv))
        output, code = "", 0
        if "validate" in argv and "--manifest" in argv:
            path = Path(argv[argv.index("--manifest") + 1])
            output = json.dumps({"status": "PASS", **manifest.load_manifest(path)})
        elif argv[0] == "/usr/bin/git":
            operation = argv[argv.index("-C") + 2:]
            while operation[:1] == ["-c"]:
                operation = operation[2:]
            if operation[:2] == ["rev-parse", "--path-format=absolute"]:
                output = str(self.case.actor / ".git")
            elif operation == ["rev-parse", "HEAD"] or operation == ["rev-parse", TARGET + "^{commit}"]:
                output = TARGET
            elif operation[:2] == ["remote", "get-url"]:
                output = self.case.request.expected_remote
            elif operation[0] == "push":
                manifest.assert_runtime_shutdown_lease(self.case.state)
                self.push_under_ex.append(manifest._SHUTDOWN_LEASE.get() is not None)
                receipt = self.case.receipt()
                assert any(event["action"] == "source-push" and event["outcome"] == "INTENT"
                           for event in receipt["events"])
                assert receipt["touched_labels"] == []
                if self.push_behavior in {"accepted", "error_accepted", "timeout_accepted"}:
                    self.remote = TARGET
                elif self.push_behavior == "unknown":
                    self.remote = "3" * 40
                if self.push_behavior in {"timeout_old", "timeout_accepted"}:
                    raise subprocess.TimeoutExpired(argv, timeout)
                code = 0 if self.push_behavior == "accepted" else 1
            elif operation[:2] == ["config", "--get"]:
                output = self.case.request.expected_remote
            elif operation[:2] == ["merge-base", "--is-ancestor"]:
                code = 0 if self.fast_forward else 1
            elif operation[0] == "ls-remote":
                output = f"{self.remote}\t{self.case.request.remote_ref}\n" if self.remote else ""
            elif operation[0] not in {"status", "ls-files", "fsck"}:
                raise AssertionError(operation)
        elif argv[:2] == ["/bin/launchctl", "print"]:
            label = argv[2].split("/", 2)[2]
            if not self.loaded[label]:
                code = 113
            else:
                path = self.case.launch / f"{label}.plist"
                output = (f"{argv[2]} = {{\n path = {path}\n state = not running\n"
                          " runs = 1\n last exit code = 0\n}\n")
                if self.case.barrier.exists() and label == PAIR[0]:
                    if self.publisher_running:
                        output = output.replace(" state = not running", " pid = 543219\n state = running")
                    output = output.replace(" last exit code = 0", f" last exit code = {self.publisher_exit}")
                if self.case.barrier.exists():
                    self.health_under_ex.append(manifest._SHUTDOWN_LEASE.get() is not None)
        elif argv[:2] == ["/bin/launchctl", "bootout"]:
            label = argv[2].split("/", 2)[2]
            assert label in PAIR
            self.loaded[label] = False
        elif argv[:2] == ["/bin/launchctl", "bootstrap"]:
            plist = plistlib.loads(Path(argv[3]).read_bytes())
            label = plist["Label"]
            assert label in PAIR
            if self.bootstrap_failure == label:
                self.bootstrap_failure = None
                code = 1
            else:
                self.loaded[label] = True
                if not self.skip_ack:
                    # unit 才由 runner 代寫合成 ack；正式 controller 從不寫 wrapper ack。
                    manifest.write_readiness_ack(self.case.ready, self.case.new, label)
                if self.timeout_after_bootstrap == label:
                    self.timeout_after_bootstrap = None
                    raise subprocess.TimeoutExpired(argv, timeout)
                if self.signal_after_bootstrap == label:
                    self.signal_after_bootstrap = None
                    os.kill(os.getpid(), signal.SIGTERM)
        elif argv[0] not in {"/bin/ps", "/usr/sbin/lsof"}:
            raise AssertionError(argv)
        return subprocess.CompletedProcess(argv, code, output, "")

    def mutations(self):
        return [argv for argv in self.commands if argv[:2] in (
            ["/bin/launchctl", "bootstrap"], ["/bin/launchctl", "bootout"])]


class PublisherGuardControllerUnit(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=Path(os.environ.get("TMPDIR", str(ROOT))), prefix="unit-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.actor = self.root / "sidecar"
        self.old_actor = self.root / "old-actor"
        self.source = self.root / "source"
        self.queue = self.root / "queue"
        self.state = self.root / "state"
        self.log = self.root / "logs"
        self.launch = self.root / "launch-agents"
        self.stage = self.root / "stage"
        for path in (self.actor, self.old_actor, self.source, self.queue, self.state, self.log, self.launch, self.stage):
            path.mkdir()
        (self.actor / ".git").mkdir()
        (self.actor / "scripts").mkdir()
        for module in (manifest, activation):
            (self.actor / "scripts" / Path(module.__file__).name).write_bytes(Path(module.__file__).read_bytes())
        (self.state / "runtime-work.lock").touch(mode=0o600)
        self.addCleanup(patch.stopall)
        patch.object(manifest, "_validate_actor_head", return_value=None).start()
        common = dict(queue_root=self.queue, publisher_state_root=self.state, log_root=self.log,
                      python_executable=Path(sys.executable).resolve())
        self.old = manifest.build_manifest(actor_root=self.old_actor, identity="unit-old", generation="old", **common)
        self.new = manifest.build_manifest(actor_root=self.actor, identity="unit-new", generation="new",
                                           actor_head=TARGET, activation_scope="publisher_guard", **common)
        self.old_path = self.root / "old-manifest.json"
        self.new_path = self.root / "new-manifest.json"
        manifest.write_manifest(self.old_path, self.old)
        manifest.write_manifest(self.new_path, self.new)
        self.barrier = self.state / "four-lane-activation-new.barrier"
        self.ready = self.root / "new-readiness"
        self.plists = []
        for label in manifest.SERVICE_LABELS:
            old_bytes = plistlib.dumps({"Label": label, "old": True})
            self.write_private(self.launch / f"{label}.plist", old_bytes)
            if label not in PAIR:
                continue
            fields = manifest.receipt_for_label(self.new, label)
            mapping = {
                "service_label": "SERVICE_LABEL", "identity": "IDENTITY", "manifest_digest": "MANIFEST_DIGEST",
                "runtime_identity_digest": "IDENTITY_DIGEST", "runtime_digest": "CODE_DIGEST",
                "config_version": "CONFIG_VERSION", "generation": "GENERATION", "actor_root": "ACTOR_ROOT",
                "queue_root": "QUEUE_ROOT", "publisher_state_root": "PUBLISHER_STATE_ROOT", "log_root": "LOG_ROOT",
                "actor_head": "ACTOR_HEAD", "python_executable": "PYTHON_EXECUTABLE",
            }
            environment = {"PANTHEON_RUNTIME_" + value: fields[key] for key, value in mapping.items()}
            environment.update(PANTHEON_FORMAL_RUNTIME="1", PANTHEON_RUNTIME_MANIFEST=str(self.new_path))
            args = [self.new["python_executable"], "-m", "scripts.pantheon_content_runtime_manifest", "barrier-exec",
                    "--barrier", str(self.barrier), "--expected-digest", self.new["manifest_digest"],
                    "--manifest", str(self.new_path), "--service-label", label, "--ready-root", str(self.ready),
                    "--timeout", "120", "--", self.new["python_executable"], "-m"]
            args.extend(["scripts.agy_content_publisher", "--repo-root", str(self.actor),
                         "--queue-root", str(self.queue), "--state-root", str(self.state), "--max-runs", "1",
                         "--continuous-tick", "--include-rewrites", "--push", "--expected-repo-root", str(self.actor),
                         "--expected-queue-root", str(self.queue), "--expected-state-root", str(self.state),
                         "--expected-runtime-sha", TARGET, "--expected-runtime-digest", self.new["runtime_digest"],
                         "--expected-push-mode", "push"] if label == PAIR[0]
                        else ["scripts.pantheon_content_capacity_guard", "--queue-root", str(self.queue),
                              "--publisher-root", str(self.state), "--log-root", str(self.log),
                              "--state-file", str(self.queue / "capacity-guard-state.json"), "check"])
            payload = {"Label": label, "EnvironmentVariables": environment, "ProgramArguments": args,
                       "WorkingDirectory": str(self.actor), "RunAtLoad": True,
                       "StartInterval": 60 if label == PAIR[0] else 300}
            path = self.stage / f"{label}.plist"
            self.write_private(path, plistlib.dumps(payload))
            self.plists.append(path)
        # 明示合成 unit-capacity；僅供既有 validator 契約測試，沒有實測容量證據。
        self.capacity_path = self.root / "unit-capacity.json"
        self.capacity_payload = {
            "schema_version": 1,
            "regression_id": "REG-PANTHEON-CAPACITY-WRITE-CYCLES-001",
            "status": "PASS", "mode": "bounded-synthetic-dry-run",
            "cycles": [{"rss_available": True, "swap_available": True},
                       {"rss_available": True, "swap_available": True}],
            "reclamation": {"bytes_before": 8192, "bytes_after": 4096},
            "stop_loss": {"status": "STOPPED", "triggered": True,
                          "remaining_loaded": [], "cross_project_deletions": []},
        }
        activation._write_private_json(self.capacity_path, self.capacity_payload)
        self.request = controller.PublisherGuardRequest(
            source_repo=self.source, expected_remote=str(self.root / "unit-remote.git"), remote_ref="refs/heads/main",
            before_sha=OLD, target_sha=TARGET, old_manifest_path=self.old_path, new_manifest_path=self.new_path,
            staged_plists=tuple(self.plists), launch_agents_dir=self.launch, transaction_root=self.root / "txn",
            capacity_receipt_path=self.capacity_path, capacity_receipt_digest=controller.file_sha256(self.capacity_path),
            lock_budget_seconds=5, command_timeout_seconds=1, health_timeout_seconds=1)
        self.runner = LaunchdUnitRunner(self)
        self.preserved = {path: path.read_bytes() for path in self.launch.iterdir() if path.stem not in PAIR}
        self.old_manifest_bytes = self.old_path.read_bytes()

    @staticmethod
    def write_private(path, data):
        path.write_bytes(data)
        path.chmod(0o600)

    def prepare(self, *, push_source=False):
        self.request = replace(self.request, push_source=push_source)
        result = controller.plan_publisher_guard(self.request, runner=self.runner)
        self.digest = result["plan_digest"]
        controller.prepare_publisher_guard(self.request, expected_plan_digest=self.digest, runner=self.runner)
        self.runner.remote = OLD if push_source else TARGET

    def apply(self):
        return controller.apply_publisher_guard(self.request, expected_plan_digest=self.digest, runner=self.runner)

    def recover(self):
        return controller.recover_publisher_guard(self.request, expected_plan_digest=self.digest, runner=self.runner)

    def receipt(self):
        return activation.load_action_receipt(controller._pg_receipt_path(self.request))

    def assert_preserved(self):
        self.assertEqual(self.old_manifest_bytes, self.old_path.read_bytes())
        self.assertTrue(self.old_actor.is_dir())
        for path, data in self.preserved.items():
            self.assertEqual(data, path.read_bytes())
            self.assertFalse(self.runner.loaded[path.stem])
        for argv in self.runner.mutations():
            self.assertTrue(any(label in argv[-1] for label in PAIR), argv)
        self.assertFalse(any("tag" in argv for argv in self.runner.commands))
        pushes = [argv for argv in self.runner.commands if "push" in argv]
        if not self.request.push_source:
            self.assertFalse(pushes)
        for argv in pushes:
            self.assertEqual(argv[-4:], ["push", "--atomic", "origin", f"{TARGET}:{self.request.remote_ref}"])
            self.assertFalse(any(arg.startswith("--force") or arg.startswith("+") for arg in argv))

    def assert_released(self):
        self.assertFalse(manifest.shutdown_readiness_permit_path(self.state).exists())
        with manifest.runtime_shutdown_lease(self.state, timeout_seconds=0):
            pass
        self.assertTrue(self.receipt()["ex_releases"][-1]["released"])

    def test_capacity_missing_cannot_plan(self):
        self.capacity_path.unlink()
        with self.assertRaises(controller.PromotionError):
            controller.plan_publisher_guard(self.request, runner=self.runner)
        self.assertFalse(self.request.transaction_root.exists())
        self.assertEqual(self.runner.mutations(), [])

    def test_capacity_uses_unchanged_validator_for_all_existing_policy_rejections(self):
        invalid = [
            ("status", "NO-GO"), ("mode", "unrecognized"), ("schema_version", 2),
            ("regression_id", "unit-wrong-id"),
            ("cycles", [{"rss_available": True, "swap_available": True}]),
            ("cycles", [{"rss_available": False, "swap_available": True}] * 2),
            ("cycles", [{"rss_available": True, "swap_available": False}] * 2),
            ("reclamation", {"bytes_before": 8192, "bytes_after": 8192}),
            ("reclamation", {}),
            ("stop_loss", {"status": "STOP_FAILED", "triggered": True,
                           "remaining_loaded": [], "cross_project_deletions": []}),
            ("stop_loss", {"status": "STOPPED", "triggered": False,
                           "remaining_loaded": [], "cross_project_deletions": []}),
            ("stop_loss", {"status": "STOPPED", "triggered": True,
                           "remaining_loaded": [PAIR[0]], "cross_project_deletions": []}),
            ("stop_loss", {"status": "STOPPED", "triggered": True,
                           "remaining_loaded": [], "cross_project_deletions": ["unit-forbidden"]}),
        ]
        original = controller._validate_capacity_receipt
        for field, value in invalid:
            with self.subTest(invalid_field=field, value=value):
                payload = {**self.capacity_payload, field: value}
                activation._write_private_json(self.capacity_path, payload)
                request = replace(self.request, capacity_receipt_digest=controller.file_sha256(self.capacity_path))
                with patch.object(controller, "_validate_capacity_receipt", wraps=original) as validator:
                    with self.assertRaisesRegex(controller.PromotionError, "capacity stop-loss is not PASS"):
                        controller.plan_publisher_guard(request, runner=self.runner)
                    validator.assert_called_once_with(request)
        self.assertFalse(self.request.transaction_root.exists())
        self.assertEqual(self.runner.mutations(), [])

    def test_capacity_validator_runs_for_plan_prepare_apply_and_recover(self):
        original = controller._validate_capacity_receipt
        with patch.object(controller, "_validate_capacity_receipt", wraps=original) as validator:
            self.prepare()
            self.assertEqual(validator.call_count, 2)
            self.assertEqual(self.apply()["status"], "HEALTHY")
            self.assertEqual(validator.call_count, 4)
            self.assertEqual(self.recover()["status"], "HEALTHY")
            self.assertEqual(validator.call_count, 5)
        self.assert_preserved()

    def test_capacity_digest_drift_cannot_prepare(self):
        plan = controller.plan_publisher_guard(self.request, runner=self.runner)
        self.capacity_path.write_bytes(self.capacity_path.read_bytes() + b"\n")
        with self.assertRaisesRegex(controller.PromotionError, "capacity receipt digest mismatch"):
            controller.prepare_publisher_guard(self.request, expected_plan_digest=plan["plan_digest"], runner=self.runner)
        self.assertFalse(self.request.transaction_root.exists())
        self.assertEqual(self.runner.mutations(), [])

    def test_capacity_same_bytes_new_inode_is_bound_to_plan(self):
        plan = controller.plan_publisher_guard(self.request, runner=self.runner)
        identity = plan["plan"]["capacity_receipt"]
        self.assertEqual(identity["path"], str(self.capacity_path))
        self.assertEqual(identity["sha256"], self.request.capacity_receipt_digest)
        activation.maintenance_atomic(self.capacity_path, self.capacity_path.read_bytes())
        self.assertNotEqual(identity, activation.capture_file_identity(self.capacity_path, require_private=False))
        with self.assertRaisesRegex(controller.PromotionError, "expected plan digest mismatch"):
            controller.prepare_publisher_guard(self.request, expected_plan_digest=plan["plan_digest"], runner=self.runner)
        self.assertFalse(self.request.transaction_root.exists())

    def test_capacity_missing_or_drift_prevents_apply_push_and_service_changes(self):
        self.prepare(push_source=True)
        original = self.capacity_path.read_bytes()
        self.capacity_path.unlink()
        with self.assertRaises(controller.PromotionError):
            self.apply()
        self.write_private(self.capacity_path, original + b"\n")
        with self.assertRaisesRegex(controller.PromotionError, "capacity receipt digest mismatch"):
            self.apply()
        self.assertEqual(self.runner.push_under_ex, [])
        self.assertEqual(self.runner.mutations(), [])
        self.assert_preserved()

    def test_capacity_replacement_after_prepare_cannot_apply(self):
        self.prepare(push_source=True)
        activation.maintenance_atomic(self.capacity_path, self.capacity_path.read_bytes())
        with self.assertRaisesRegex(controller.PromotionError, "sealed actor/manifest/controller/input drift"):
            self.apply()
        self.assertEqual(self.runner.push_under_ex, [])
        self.assertEqual(self.runner.mutations(), [])

    def test_capacity_revalidated_after_ex_acquire_before_source_push(self):
        self.prepare(push_source=True)
        original = manifest.runtime_shutdown_lease
        @contextmanager
        def drift_after_acquire(*args, **kwargs):
            with original(*args, **kwargs) as fd:
                self.capacity_path.write_bytes(self.capacity_path.read_bytes() + b"\n")
                yield fd
        with patch.object(manifest, "runtime_shutdown_lease", new=drift_after_acquire):
            with self.assertRaisesRegex(controller.PromotionError, "capacity receipt digest mismatch"):
                self.apply()
        self.assertEqual(self.runner.push_under_ex, [])
        self.assertEqual(self.runner.mutations(), [])
        self.assert_released()
        self.assert_preserved()

    def test_capacity_request_json_and_required_fields(self):
        payload = {key: str(value) if isinstance(value, Path) else [str(item) for item in value]
                   if key == "staged_plists" else value for key, value in vars(self.request).items()}
        path = self.root / "unit-request.json"
        activation._write_private_json(path, payload)
        restored = controller._pg_request_from_file(path)
        self.assertEqual(restored.capacity_receipt_path, self.capacity_path)
        self.assertEqual(restored.capacity_receipt_digest, self.request.capacity_receipt_digest)
        for missing in ("capacity_receipt_path", "capacity_receipt_digest"):
            activation._write_private_json(path, {key: value for key, value in payload.items() if key != missing})
            with self.assertRaises((KeyError, TypeError)):
                controller._pg_request_from_file(path)

    def test_running_natural_tick_pending_and_rechecks_never_restart(self):
        self.prepare()
        self.runner.publisher_running = True
        result = self.apply()
        self.assertEqual(result["status"], "POSTCHECK_PENDING")
        self.assertFalse(result["health"]["payload_completed"])
        self.assertFalse(result["health"]["normal_natural_tick_completed"])
        mutations = list(self.runner.mutations())
        acquisitions = sum(event["action"] == "acquire-ex" for event in result["events"])
        for recheck in (self.recover, self.apply):
            self.assertEqual(recheck()["status"], "POSTCHECK_PENDING")
            self.assertEqual(self.runner.mutations(), mutations)
            self.assertEqual(sum(event["action"] == "acquire-ex" for event in self.receipt()["events"]), acquisitions)
        self.runner.publisher_running = False
        result = self.recover()
        self.assertEqual(result["status"], "HEALTHY")
        self.assertTrue(result["health"]["payload_completed"])
        self.assertEqual(self.runner.mutations(), mutations)
        self.assert_preserved()

    def test_normal_publisher_rejects_missing_modes_and_semantic_flags(self):
        path = self.plists[0]
        original = path.read_bytes()
        payload = plistlib.loads(original)
        for flag in ("--continuous-tick", "--include-rewrites", "--push"):
            with self.subTest(missing=flag):
                changed = dict(payload)
                changed["ProgramArguments"] = [arg for arg in payload["ProgramArguments"] if arg != flag]
                self.write_private(path, plistlib.dumps(changed))
                with self.assertRaises(controller.PromotionError):
                    controller.plan_publisher_guard(self.request, runner=self.runner)
        for flags in (("--skip-tests",), ("--skip-release-gate",), ("--exact-run-id", "unit-exact"),
                      ("--exact-fresh-ja-run-id", "unit-exact"), ("--batch-new",), ("--new-only",),
                      ("--rewrite-release",), ("--dry-run",), ("--pages-deploy",),
                      ("--deployment-preflight",), ("--manifest-authorized-deployment-preflight",), ("--push",)):
            with self.subTest(forbidden=flags):
                changed = dict(payload)
                changed["ProgramArguments"] = payload["ProgramArguments"] + list(flags)
                self.write_private(path, plistlib.dumps(changed))
                with self.assertRaises((controller.PromotionError, manifest.RuntimeManifestError)):
                    controller.plan_publisher_guard(self.request, runner=self.runner)
        self.write_private(path, original)
        self.assertFalse(self.request.transaction_root.exists())
        self.assertEqual(self.runner.mutations(), [])

    def test_normal_publisher_rejects_wrong_roots_and_expected_identity(self):
        path = self.plists[0]
        original = path.read_bytes()
        payload = plistlib.loads(original)
        for flag in ("--repo-root", "--queue-root", "--state-root", "--expected-repo-root",
                     "--expected-queue-root", "--expected-state-root", "--expected-runtime-sha",
                     "--expected-runtime-digest", "--expected-push-mode"):
            with self.subTest(identity=flag):
                changed = dict(payload)
                args = payload["ProgramArguments"].copy()
                args[args.index(flag) + 1] = "unit-wrong-identity"
                changed["ProgramArguments"] = args
                self.write_private(path, plistlib.dumps(changed))
                with self.assertRaisesRegex(controller.PromotionError, "normal Publisher identity mismatch"):
                    controller.plan_publisher_guard(self.request, runner=self.runner)
        self.write_private(path, original)
        self.assertEqual(self.runner.mutations(), [])

    def test_pending_running_tick_can_recheck_under_shared_work_lease(self):
        self.prepare()
        self.runner.publisher_running = True
        self.assertEqual(self.apply()["status"], "POSTCHECK_PENDING")
        mutations = list(self.runner.mutations())
        with manifest.runtime_work_lease(self.state):
            self.assertEqual(self.recover()["status"], "POSTCHECK_PENDING")
            self.assertEqual(self.apply()["status"], "POSTCHECK_PENDING")
        self.assertEqual(self.runner.mutations(), mutations)
        self.assert_preserved()

    def test_partial_forward_cannot_resume_without_real_quiescence(self):
        self.prepare()
        with manifest.runtime_work_lease(self.state):
            with self.assertRaisesRegex(controller.PromotionError, "cannot upgrade"):
                self.recover()
        self.assertEqual(self.runner.mutations(), [])
        self.assertFalse(self.barrier.exists())
        self.assertEqual(self.recover()["status"], "HEALTHY")
        self.assert_preserved()

    def test_terminal_nonzero_never_healthy_and_never_restarts(self):
        self.prepare()
        self.runner.publisher_exit = 7
        with self.assertRaisesRegex(controller.PromotionError, "last exit nonzero"):
            self.apply()
        mutations = list(self.runner.mutations())
        for recheck in (self.recover, self.apply):
            with self.assertRaisesRegex(controller.PromotionError, "last exit nonzero"):
                recheck()
            self.assertEqual(self.runner.mutations(), mutations)
            self.assertNotEqual(self.receipt()["status"], "HEALTHY")
        self.runner.publisher_exit = 0
        self.assertEqual(self.recover()["status"], "HEALTHY")
        self.assertEqual(self.runner.mutations(), mutations)
        self.assert_preserved()

    def test_running_with_nonzero_exit_does_not_hide_failed_previous_tick(self):
        self.prepare()
        self.runner.publisher_running = True
        self.runner.publisher_exit = 9
        with self.assertRaisesRegex(controller.PromotionError, "last exit nonzero"):
            self.apply()
        self.assertNotEqual(self.receipt()["status"], "POSTCHECK_PENDING")
        self.assert_preserved()

    def test_activated_barrier_is_fence_even_if_health_status_is_lost(self):
        self.prepare()
        self.runner.publisher_running = True
        self.assertEqual(self.apply()["status"], "POSTCHECK_PENDING")
        receipt = self.receipt()
        receipt["status"] = "RECOVERY_REQUIRED"
        receipt.pop("health")
        controller._pg_save(self.request, receipt)
        mutations = list(self.runner.mutations())
        self.assertEqual(self.recover()["status"], "POSTCHECK_PENDING")
        self.assertEqual(self.runner.mutations(), mutations)
        self.assert_preserved()

    def test_published_handoff_with_missing_barrier_fails_readonly(self):
        self.prepare()
        self.assertEqual(self.apply()["status"], "HEALTHY")
        mutations = list(self.runner.mutations())
        self.barrier.unlink()
        with self.assertRaises(controller.PromotionError):
            self.recover()
        self.assertEqual(self.runner.mutations(), mutations)
        self.assert_preserved()

    def test_idle_without_completed_tick_is_pending_not_healthy(self):
        self.prepare()
        base_runner = self.runner
        def no_completed_tick(argv, *, timeout):
            result = base_runner(argv, timeout=timeout)
            if self.barrier.exists() and argv[:2] == ["/bin/launchctl", "print"] and argv[-1].endswith(PAIR[0]):
                result.stdout = result.stdout.replace(" runs = 1", " runs = 0").replace(" last exit code = 0\n", "")
            return result
        result = controller.apply_publisher_guard(self.request, expected_plan_digest=self.digest, runner=no_completed_tick)
        self.assertEqual(result["status"], "POSTCHECK_PENDING")
        self.assertEqual(result["health"]["pending_services"][PAIR[0]], "READY_PENDING_NATURAL_TICK")
        self.assertFalse(result["health"]["payload_completed"])
        self.assert_preserved()

    def test_pending_recheck_rejects_remote_guard_or_plist_drift_without_restart(self):
        self.prepare()
        self.runner.publisher_running = True
        self.assertEqual(self.apply()["status"], "POSTCHECK_PENDING")
        mutations = list(self.runner.mutations())
        self.runner.remote = "3" * 40
        with self.assertRaises(controller.PromotionError):
            self.recover()
        self.runner.remote = TARGET
        guard = self.queue / "capacity-guard-state.json"
        activation._write_private_json(guard, {"status": "STOP_FAILED"})
        with self.assertRaises(controller.PromotionError):
            self.recover()
        guard.unlink()
        plist = self.launch / f"{PAIR[0]}.plist"
        original = plist.read_bytes()
        self.write_private(plist, b"unit drift")
        with self.assertRaises(controller.PromotionError):
            self.recover()
        self.write_private(plist, original)
        self.assertEqual(self.recover()["status"], "POSTCHECK_PENDING")
        self.assertEqual(self.runner.mutations(), mutations)
        self.assert_preserved()

    def test_opt_in_push_holds_ex_and_health_follows_own_release(self):
        self.prepare(push_source=True)
        result = self.apply()
        self.assertEqual(result["status"], "HEALTHY")
        self.assertEqual(self.runner.push_under_ex, [True])
        self.assertTrue(self.runner.health_under_ex)
        self.assertFalse(any(self.runner.health_under_ex))
        self.assertTrue(result["plan"]["request"]["push_source"])
        self.assertEqual(result["health"]["remote"]["status"], "TARGET")
        self.assert_released()
        self.assert_preserved()

    def test_push_source_is_explicit_boolean_and_sealed_in_digest(self):
        default = controller.plan_publisher_guard(self.request, runner=self.runner)
        opted = controller.plan_publisher_guard(replace(self.request, push_source=True), runner=self.runner)
        self.assertFalse(default["plan"]["request"]["push_source"])
        self.assertTrue(opted["plan"]["request"]["push_source"])
        self.assertNotEqual(default["plan_digest"], opted["plan_digest"])
        with self.assertRaisesRegex(controller.PromotionError, "explicit boolean"):
            controller.plan_publisher_guard(replace(self.request, push_source="true"), runner=self.runner)
        self.assertEqual(self.runner.push_under_ex, [])

    def test_push_rejected_before_has_no_service_mutation_or_resend(self):
        self.prepare(push_source=True)
        self.runner.push_behavior = "rejected"
        with self.assertRaisesRegex(controller.PromotionError, "source push remote OLD/UNKNOWN"):
            self.apply()
        self.assertEqual(self.receipt()["remote"]["status"], "OLD")
        self.assertEqual(self.runner.mutations(), [])
        self.assertEqual(self.runner.push_under_ex, [True])
        self.assert_released()
        with self.assertRaisesRegex(controller.PromotionError, "remote OLD/UNKNOWN"):
            self.recover()
        with self.assertRaisesRegex(controller.PromotionError, "remote OLD/UNKNOWN"):
            self.apply()
        self.assertEqual(self.runner.push_under_ex, [True])
        self.assert_preserved()

    def test_push_timeout_before_is_not_a_bootstrap_or_retry_authority(self):
        self.prepare(push_source=True)
        self.runner.push_behavior = "timeout_old"
        with self.assertRaisesRegex(controller.PromotionError, "source push remote OLD/UNKNOWN"):
            self.apply()
        receipt = self.receipt()
        self.assertEqual(receipt["remote"]["status"], "OLD")
        self.assertTrue(any("TimeoutExpired" in item["error"] for item in receipt["errors"]))
        self.assertEqual(self.runner.mutations(), [])
        self.assert_released()
        with self.assertRaises(controller.PromotionError):
            self.recover()
        self.assertEqual(self.runner.push_under_ex, [True])
        self.assert_preserved()

    def test_push_timeout_but_target_accepted_finishes_forward(self):
        self.prepare(push_source=True)
        self.runner.push_behavior = "timeout_accepted"
        receipt = self.apply()
        self.assertEqual(receipt["status"], "HEALTHY")
        self.assertTrue(any("TimeoutExpired" in item["error"] for item in receipt["errors"]))
        push = next(event for event in receipt["events"] if event["action"] == "source-push")
        self.assertEqual(push["remote"]["status"], "TARGET")
        self.assertIn("terminal_verified_at", push)
        self.assert_released()
        self.assert_preserved()

    def test_push_nonzero_but_target_accepted_finishes_forward(self):
        self.prepare(push_source=True)
        self.runner.push_behavior = "error_accepted"
        receipt = self.apply()
        self.assertEqual(receipt["status"], "HEALTHY")
        self.assertTrue(any(item["phase"] == "source-push" for item in receipt["errors"]))
        self.assertEqual(self.runner.push_under_ex, [True])
        self.assert_released()
        self.assert_preserved()

    def test_push_unknown_stops_and_recover_only_revalidates_target(self):
        self.prepare(push_source=True)
        self.runner.push_behavior = "unknown"
        with self.assertRaisesRegex(controller.PromotionError, "source push remote OLD/UNKNOWN"):
            self.apply()
        self.assertEqual(self.receipt()["remote"]["status"], "UNKNOWN")
        self.assertEqual(self.runner.mutations(), [])
        self.assert_released()
        with self.assertRaises(controller.PromotionError):
            self.recover()
        self.runner.remote = TARGET
        self.assertEqual(self.recover()["status"], "HEALTHY")
        self.assertEqual(self.runner.push_under_ex, [True])
        self.assert_preserved()

    def test_recover_cannot_send_even_the_first_opted_in_push(self):
        self.prepare(push_source=True)
        with self.assertRaisesRegex(controller.PromotionError, "remote OLD/UNKNOWN"):
            self.recover()
        self.assertEqual(self.runner.push_under_ex, [])
        self.assertEqual(self.runner.mutations(), [])
        self.assert_preserved()

    def test_opted_in_target_already_accepted_does_not_push(self):
        self.prepare(push_source=True)
        self.runner.remote = TARGET
        self.assertEqual(self.apply()["status"], "HEALTHY")
        self.assertEqual(self.runner.push_under_ex, [])
        self.assert_released()
        self.assert_preserved()

    def test_push_unresolved_group_stops_before_remote_readback(self):
        self.prepare(push_source=True)
        original = controller._PublisherGuardCommands.__call__
        def unknown_group(commands, argv):
            if "push" not in argv:
                return original(commands, argv)
            manifest.assert_runtime_shutdown_lease(self.state)
            self.runner.commands.append(list(argv))
            controller._pg_event(self.request, commands.receipt, "command", argv=argv,
                child_terminal=True, group_terminal=False, pgid=os.getpgrp())
            raise subprocess.TimeoutExpired(argv, 1)
        with patch.object(controller._PublisherGuardCommands, "__call__", new=unknown_group):
            with self.assertRaisesRegex(controller.PromotionError, "prior child group lineage UNKNOWN"):
                self.apply()
        push_index = next(index for index, argv in enumerate(self.runner.commands) if "push" in argv)
        self.assertFalse(any("ls-remote" in argv for argv in self.runner.commands[push_index + 1:]))
        self.assertEqual(self.runner.mutations(), [])
        self.assert_released()
        self.assert_preserved()

    def test_plan_read_only_and_digest_required(self):
        before = sorted(str(path) for path in self.root.rglob("*"))
        result = controller.plan_publisher_guard(self.request, runner=self.runner)
        self.assertEqual(before, sorted(str(path) for path in self.root.rglob("*")))
        self.assertEqual(result["status"], "PLANNED")
        with self.assertRaises(controller.PromotionError):
            controller.prepare_publisher_guard(self.request, expected_plan_digest="0" * 64, runner=self.runner)
        self.assertFalse(self.request.transaction_root.exists())
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
            controller.parse_args(["apply-publisher-guard", "--request-json", "unit.json"])
        self.assertEqual(controller.parse_args(["plan-publisher-guard", "--request-json", "unit.json"]).command,
                         "plan-publisher-guard")

    def test_source_advanced_partial_bootstrap_failure_recovers_forward(self):
        self.prepare()
        self.runner.bootstrap_failure = PAIR[1]
        with self.assertRaisesRegex(controller.PromotionError, "bootstrap outcome UNKNOWN"):
            self.apply()
        original = self.receipt()
        old_journals = {Path(event["journal"]): Path(event["journal"]).read_bytes()
                        for event in original["events"] if event["action"] == "process-boundary"}
        self.assertEqual(original["remote"]["status"], "TARGET")
        self.assert_released()
        result = self.recover()
        self.assertEqual(result["status"], "HEALTHY")
        self.assertEqual(result["errors"][:len(original["errors"])], original["errors"])
        for path, data in old_journals.items():
            self.assertEqual(path.read_bytes(), data)
        self.assertTrue(result["health"]["after_ex_release"])
        self.assert_preserved()

    def test_remote_unknown_never_controls_or_repushes(self):
        self.prepare()
        self.runner.remote = "3" * 40
        with self.assertRaisesRegex(controller.PromotionError, "remote OLD/UNKNOWN"):
            self.apply()
        self.assertEqual(self.receipt()["remote"]["status"], "UNKNOWN")
        self.assertEqual(self.runner.mutations(), [])
        self.runner.remote = TARGET
        self.assertEqual(self.recover()["status"], "HEALTHY")
        self.assert_preserved()

    def test_remote_read_timeout_is_unknown_and_does_not_control(self):
        self.prepare()
        base_runner = self.runner
        def network_unknown(argv, *, timeout):
            if "ls-remote" in argv:
                raise subprocess.TimeoutExpired(argv, timeout)
            return base_runner(argv, timeout=timeout)
        with self.assertRaisesRegex(controller.PromotionError, "remote OLD/UNKNOWN"):
            controller.apply_publisher_guard(self.request, expected_plan_digest=self.digest, runner=network_unknown)
        self.assertEqual(self.receipt()["remote"]["status"], "UNKNOWN")
        self.assertEqual(self.runner.mutations(), [])
        self.assertEqual(self.receipt()["five_after_failure"]["status"], "PASS")
        self.assertEqual(self.recover()["status"], "HEALTHY")

    def test_remote_old_never_controls(self):
        self.prepare()
        self.runner.remote = OLD
        with self.assertRaisesRegex(controller.PromotionError, "remote OLD/UNKNOWN"):
            self.apply()
        self.assertEqual(self.runner.mutations(), [])

    def test_control_timeout_keeps_receipt_and_reconciles_before_forward(self):
        self.prepare()
        self.runner.timeout_after_bootstrap = PAIR[0]
        with self.assertRaises(controller.PromotionError):
            self.apply()
        self.assertTrue(any(event.get("outcome") == "UNKNOWN" for event in self.receipt()["events"]))
        self.assert_released()
        result = self.recover()
        self.assertEqual(result["status"], "HEALTHY")
        self.assertTrue(any("TimeoutExpired" in entry["error"] for entry in result["errors"]))
        self.assert_preserved()

    def test_sigterm_keeps_recoverable_receipt(self):
        self.prepare()
        self.runner.signal_after_bootstrap = PAIR[0]
        with self.assertRaisesRegex(controller.PromotionError, "SIGTERM"):
            self.apply()
        self.assert_released()
        self.assertEqual(self.recover()["status"], "HEALTHY")
        self.assert_preserved()

    def test_guard_normal_payload_rejects_invalid_action_roots_and_missing_flags(self):
        path = self.plists[1]
        original = plistlib.loads(path.read_bytes())
        for suffix in ([], ["preflight"], ["--queue-root", str(self.queue), "check"],
                       ["--queue-root", str(self.queue), "--publisher-root", str(self.state),
                        "--log-root", str(self.log), "--state-file", str(self.state / "wrong.json"), "check"]):
            with self.subTest(suffix=suffix):
                payload = dict(original)
                payload["ProgramArguments"] = original["ProgramArguments"][:20] + suffix
                self.write_private(path, plistlib.dumps(payload))
                with self.assertRaisesRegex(controller.PromotionError, "normal Guard"):
                    controller.plan_publisher_guard(self.request, runner=self.runner)
        self.write_private(path, plistlib.dumps(original))

    def test_release_tag_proof_preserves_object_and_rejects_ambiguous_or_wrong_targets(self):
        tag = "refs/tags/v0.0.1"
        commit, obj, wrong = "a" * 40, "b" * 40, "c" * 40
        cases = [
            (f"{obj}\t{tag}\n{commit}\t{tag}^{{}}\n", "annotated"),
            (f"{commit}\t{tag}^{{}}\n{obj}\t{tag}\n", "annotated"),
            (f"{commit}\t{tag}\n", "lightweight"),
            ("", None),
            (f"{commit}\t{tag}^{{}}\n", None),
            (f"{obj}\t{tag}\n", None),
            (f"{obj}\t{tag}\n{wrong}\t{tag}^{{}}\n", None),
            (f"{commit}\t{tag}\n{commit}\t{tag}\n", None),
            (f"{obj}\t{tag}\n{commit}\t{tag}^{{}}\n{commit}\t{tag}^{{}}\n", None),
            (f"{commit}\trefs/tags/other\n", None),
            (f"not-a-sha\t{tag}\n", None),
            (f"{commit} {tag} extra\n", None),
        ]
        for text, kind in cases:
            with self.subTest(kind=kind, text=text), patch.object(controller, "_pg_git", return_value=text) as call:
                if kind is None:
                    with self.assertRaises(controller.PromotionError):
                        controller._pg_release_tag_proof(self.request, None, tag, commit)
                else:
                    proof = controller._pg_release_tag_proof(self.request, None, tag, commit)
                    self.assertEqual(proof["tag_kind"], kind)
                    self.assertEqual(proof["tag_commit_sha"], commit)
                    self.assertEqual(proof["tag_object_sha"], obj if kind == "annotated" else commit)
                self.assertEqual(call.call_args.args[2:], ("ls-remote", self.request.expected_remote, tag, tag + "^{}"))

    def test_guard_normal_argv_is_accepted_by_real_parser(self):
        from scripts import pantheon_content_capacity_guard as guard
        payload = plistlib.loads(self.plists[1].read_bytes())
        argv = ["guard", *payload["ProgramArguments"][20:]]
        with patch.object(sys, "argv", argv):
            parsed = guard.parse_args()
        self.assertEqual(parsed.command, "check")
        self.assertEqual(parsed.publisher_root, self.state)
        self.assertEqual(parsed.state_file, self.queue / "capacity-guard-state.json")

    def test_published_barrier_cleanup_failure_recovers_without_restart(self):
        self.prepare()
        with patch.object(manifest, "revoke_shutdown_readiness_permit", side_effect=OSError("post barrier cleanup")):
            with self.assertRaisesRegex(controller.PromotionError, "post barrier cleanup"):
                self.apply()
        self.assertTrue(self.barrier.exists())
        mutations = self.runner.mutations()
        self.assertEqual(self.recover()["status"], "HEALTHY")
        self.assertEqual(self.runner.mutations(), mutations)
        self.assert_released()

    def test_published_barrier_release_receipt_gap_recovers_without_restart(self):
        self.prepare()
        self.apply()
        receipt = self.receipt()
        receipt["ex_releases"] = []
        controller._pg_save(self.request, receipt)
        mutations = self.runner.mutations()
        self.assertEqual(self.recover()["status"], "HEALTHY")
        self.assertEqual(self.runner.mutations(), mutations)
        self.assert_released()

    def test_original_and_cleanup_errors_both_retained(self):
        self.prepare()
        self.runner.bootstrap_failure = PAIR[1]
        with patch.object(manifest, "revoke_shutdown_readiness_permit", side_effect=OSError("unit cleanup failure")):
            with self.assertRaises(controller.PromotionError):
                self.apply()
        errors = self.receipt()["errors"]
        self.assertTrue(any("bootstrap outcome UNKNOWN" in item["error"] for item in errors))
        self.assertTrue(any("unit cleanup failure" in item["error"] for item in errors))
        with manifest.runtime_shutdown_lease(self.state, timeout_seconds=0):
            pass
        self.assertEqual(self.recover()["status"], "HEALTHY")
        self.assert_preserved()

    def test_unknown_process_journal_cannot_be_reset_by_recover(self):
        self.prepare()
        self.runner.bootstrap_failure = PAIR[1]
        with self.assertRaises(controller.PromotionError):
            self.apply()
        receipt = self.receipt()
        path = Path(receipt["boundaries"]["old-cohort"])
        record = activation.load_action_receipt(path)
        record.update(status="UNKNOWN_OR_FAILED", error="unit unresolved lineage")
        activation._write_private_json(path, record)
        original_bytes = path.read_bytes()
        count = len(self.runner.mutations())
        with self.assertRaisesRegex(controller.PromotionError, "prior process evidence unresolved"):
            self.recover()
        self.assertEqual(path.read_bytes(), original_bytes)
        self.assertEqual(count, len(self.runner.mutations()))
        self.assert_preserved()

    def test_five_service_drift_blocks_all_mutation(self):
        self.prepare()
        path = next(iter(self.preserved))
        self.write_private(path, b"unit drift")
        with self.assertRaisesRegex(controller.PromotionError, "drift"):
            self.apply()
        self.assertEqual(self.runner.mutations(), [])

    def test_unknown_guard_stop_is_preserved(self):
        self.prepare()
        path = self.queue / "capacity-guard-state.json"
        activation._write_private_json(path, {"status": "STOP_FAILED", "recovery_incident": {"unit": "unknown"}})
        before = path.read_bytes()
        with self.assertRaisesRegex(controller.PromotionError, "Guard stop/recovery"):
            self.apply()
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.runner.mutations(), [])

    def test_unknown_permit_is_preserved(self):
        self.prepare()
        path = manifest.shutdown_readiness_permit_path(self.state)
        activation._write_private_json(path, {"nonce": "unit-unknown"})
        before = path.read_bytes()
        with self.assertRaisesRegex(controller.PromotionError, "unknown permit lineage"):
            self.apply()
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.runner.mutations(), [])

    def test_unknown_child_spawn_window_cannot_be_cleared(self):
        self.prepare()
        receipt = self.receipt()
        receipt["events"].append({"action": "command", "outcome": "INTENT", "child_terminal": False})
        controller._pg_save(self.request, receipt)
        with self.assertRaisesRegex(controller.PromotionError, "unbound command lineage"):
            self.recover()
        self.assertEqual(self.runner.mutations(), [])
        self.assertEqual(self.receipt()["events"][-1]["outcome"], "READBACK")
        self.assertTrue(any(event.get("child_terminal") is False for event in self.receipt()["events"]))

    def test_non_fast_forward_and_helper_version_mismatch_fail_plan(self):
        self.runner.fast_forward = False
        with self.assertRaisesRegex(controller.PromotionError, "merge-base"):
            controller.plan_publisher_guard(self.request, runner=self.runner)
        self.runner.fast_forward = True
        (self.actor / "scripts" / Path(manifest.__file__).name).write_text("unit different code\n")
        with self.assertRaisesRegex(controller.PromotionError, "helper version mismatch"):
            controller.plan_publisher_guard(self.request, runner=self.runner)
        self.assertFalse(self.request.transaction_root.exists())

    def _unit_metadata_child(self, *, stdout_size, stderr_size=0):
        """用本機 Python 合成有效 Git metadata bytes，保留真 bounded process 邊界。"""
        stub = self.root / "unit-metadata-output.py"
        stub.write_text(
            "import sys\n"
            "line = '100644 ' + 'a' * 40 + ' 0\\tunit-metadata-file.py\\n'\n"
            "count = (int(sys.argv[1]) + len(line) - 1) // len(line)\n"
            "sys.stdout.write(line * count)\n"
            "sys.stderr.write('x' * int(sys.argv[2]))\n")
        real_popen = subprocess.Popen
        def metadata_process(argv, **kwargs):
            self.assertEqual(argv[0], "/usr/bin/git")
            self.assertIn("ls-files", argv)
            return real_popen([sys.executable, "-B", str(stub), str(stdout_size), str(stderr_size)], **kwargs)
        commands = controller._PublisherGuardCommands(self.request, self.receipt())
        with patch.object(controller.subprocess, "Popen", side_effect=metadata_process):
            return controller._pg_git(commands, self.actor, "ls-files", "--stage")

    def test_git_metadata_over_one_mib_valid_output_passes(self):
        self.prepare()
        output = self._unit_metadata_child(stdout_size=1382680)
        self.assertGreater(len(output.encode()), 1024 * 1024)
        self.assertLessEqual(len(output.encode()), 4 * 1024 * 1024)
        self.assertTrue(all(line.startswith("100644 ") and "\t" in line for line in output.splitlines()))
        self.assertTrue(self.receipt()["events"][-1]["group_terminal"])

    def test_git_metadata_over_four_mib_still_rejected(self):
        self.prepare()
        with self.assertRaisesRegex(controller.PromotionError, "command output exceeded bound"):
            self._unit_metadata_child(stdout_size=4 * 1024 * 1024 + 1)
        self.assertEqual(self.receipt()["events"][-1]["outcome"], "UNKNOWN")
        self.assertTrue(self.receipt()["events"][-1]["child_terminal"])
        self.assertTrue(self.receipt()["events"][-1]["group_terminal"])

    def test_git_metadata_stderr_stays_bounded_at_sixty_four_kib(self):
        self.prepare()
        with self.assertRaisesRegex(controller.PromotionError, "command output exceeded bound"):
            self._unit_metadata_child(stdout_size=100, stderr_size=65537)

    def test_real_local_child_timeout_has_terminal_receipt(self):
        self.prepare()
        receipt = self.receipt()
        commands = controller._PublisherGuardCommands(replace(self.request, command_timeout_seconds=0.03), receipt)
        started = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            commands(["/bin/sleep", "3"])
        self.assertLess(time.monotonic() - started, 1)
        event = self.receipt()["events"][-1]
        self.assertTrue(event["child_terminal"])
        self.assertTrue(event["group_terminal"])
        self.assertEqual(event["outcome"], "UNKNOWN")

    def test_total_ex_hold_deadline_interrupts_stuck_control(self):
        self.prepare()
        original_watchdog = controller._pg_watchdog
        def unit_budget(seconds):
            return original_watchdog(min(seconds, 0.15))
        base_runner = self.runner
        def stuck(argv, *, timeout):
            if argv[:2] == ["/bin/launchctl", "bootout"]:
                time.sleep(3)
            return base_runner(argv, timeout=timeout)
        started = time.monotonic()
        with patch.object(controller, "_pg_watchdog", side_effect=unit_budget):
            with self.assertRaisesRegex(controller.PromotionError, "SIGALRM"):
                controller.apply_publisher_guard(self.request, expected_plan_digest=self.digest, runner=stuck)
        self.assertLess(time.monotonic() - started, 1)
        self.assert_released()
        self.assert_preserved()

    def test_recovery_stops_waiting_wrapper_with_pid_before_drain(self):
        self.prepare()
        self.runner.bootstrap_failure = PAIR[1]
        with self.assertRaises(controller.PromotionError):
            self.apply()
        base_runner = self.runner
        fake_pid = 543219
        def waiting_wrapper(argv, *, timeout):
            result = base_runner(argv, timeout=timeout)
            alive = base_runner.loaded[PAIR[0]] and not self.barrier.exists()
            if alive and argv[:2] == ["/bin/launchctl", "print"] and argv[-1].endswith(PAIR[0]):
                result.stdout = result.stdout.replace(" state = not running", f" pid = {fake_pid}\n state = running")
            elif argv[0] == "/bin/ps" and alive:
                result.stdout = f"{fake_pid} 1 {fake_pid} S {self.actor}/wrapper\n"
            return result
        def birth(pid, row, record):
            return [123, 4] if base_runner.loaded[PAIR[0]] and not self.barrier.exists() else None
        with patch.object(activation, "_process_birth_identity", side_effect=birth):
            result = controller.recover_publisher_guard(self.request, expected_plan_digest=self.digest,
                                                        runner=waiting_wrapper)
        self.assertEqual(result["status"], "HEALTHY")
        self.assert_preserved()

    def test_scoped_receipts_and_legacy_cli_unchanged(self):
        self.assertEqual(manifest.activation_service_labels(self.new), PAIR)
        self.assertEqual(manifest.activation_service_labels(self.old), manifest.SERVICE_LABELS)
        self.assertEqual(self.new["service_labels"], list(manifest.SERVICE_LABELS))
        self.assertEqual(controller.ORDERED_STATES[-1], "COMMITTED")
        self.assertEqual(self.request.target_sha, TARGET)


    def test_normal_schedule_matches_guard_idle_authority(self):
        path=self.plists[0]
        original=path.read_bytes()
        for field,value in [("KeepAlive",False),("StartInterval",60.0)]:
            with self.subTest(field=field):
                payload=plistlib.loads(original);payload[field]=value
                self.write_private(path,plistlib.dumps(payload))
                with self.assertRaisesRegex(controller.PromotionError,"normal schedule mismatch"):
                    controller.plan_publisher_guard(self.request,runner=self.runner)
        self.write_private(path,original)


if __name__ == "__main__":
    unittest.main()
