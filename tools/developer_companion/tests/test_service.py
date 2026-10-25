from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from pathlib import Path

from tools.developer_companion.service import CompanionError, DeveloperCompanion


OWNER = "test-owner-session-0123456789"


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, check=True)
    return result.stdout.decode("utf-8").strip()


class FixtureExecutor:
    """Protocol fixture only; its receipts must remain TEST_DOUBLE."""
    def __init__(self, *, cwd, env, command, notification_sink):
        self.cwd, self.sink = cwd, notification_sink
        self.pid = os.getpid()
    def initialize(self, **kwargs):
        return {"name": "test-double"}
    def run_turn(self, *, session_id, **kwargs):
        self.sink("session.event", {"sessionId": session_id, "event": {"type": "tool/call", "data": {"callId": "fixture", "name": "edit_file", "arguments": json.dumps({"path": "calculator.py"})}}})
        (self.cwd / "calculator.py").write_text("answer = 42\n", encoding="utf-8")
        git(self.cwd, "add", "--", "calculator.py")
        git(self.cwd, "commit", "-qm", "fixture source change")
        artifacts = self.cwd / ".developer-companion" / "artifacts"
        artifacts.mkdir(parents=True)
        (artifacts / "result.json").write_text('{"evidence":"TEST_DOUBLE"}', encoding="utf-8")
        return {"status": "idle"}
    def cancel(self):
        pass
    def close(self):
        pass


class BlockingExecutor(FixtureExecutor):
    ready = threading.Event()
    stopped = threading.Event()
    def run_turn(self, **kwargs):
        self.ready.set()
        if not self.stopped.wait(8):
            raise RuntimeError("fixture was not cancelled")
        raise RuntimeError("fixture cancelled")
    def cancel(self):
        self.stopped.set()


class UncommittedExecutor(FixtureExecutor):
    def run_turn(self, *, session_id, **kwargs):
        self.sink("session.event", {"sessionId": session_id, "event": {"type": "tool/call", "data": {"callId": "proposal", "name": "edit_file", "arguments": json.dumps({"path": "calculator.py"})}}})
        (self.cwd / "calculator.py").write_text("answer = 42\n", encoding="utf-8")
        (self.cwd / "new_check.py").write_text("assert 6 * 7 == 42\n", encoding="utf-8")
        return {"status": "idle"}


class CompanionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        git(self.source, "init", "-q")
        git(self.source, "config", "user.name", "Fixture")
        git(self.source, "config", "user.email", "fixture@localhost")
        (self.source / "calculator.py").write_text("answer = 0\n", encoding="utf-8")
        git(self.source, "add", "--", "calculator.py")
        git(self.source, "commit", "-qm", "fixture base")
        (self.source / ".env").write_text("PRIVATE_TEST_CANARY=must-not-enter-snapshot\n", encoding="utf-8")
        self.state = self.root / "state"
    def tearDown(self):
        self.temp.cleanup()
    def companion(self, factory=FixtureExecutor):
        return DeveloperCompanion(source_checkout=self.source, state_dir=self.state, executor_factory=factory)
    def test_private_snapshot_real_git_diff_and_persistent_owner_boundary(self):
        companion = self.companion()
        task = companion.create_task("Correct the answer", self.source, OWNER, allowed_paths=["calculator.py"])
        checkout = Path(task["checkout"])
        self.assertEqual(git(checkout, "rev-parse", "HEAD"), git(self.source, "rev-parse", "HEAD"))
        self.assertFalse((checkout / ".env").exists())
        self.assertEqual(git(checkout, "remote"), "")
        result = companion.run_task(task["task_id"], OWNER, provider="fixture", model="fixture")
        self.assertEqual(result["status"], "COMPLETED_UNVERIFIED")
        self.assertEqual(result["execution_kind"], "TEST_DOUBLE")
        self.assertEqual(result["changed_paths"], ["calculator.py"])
        self.assertIn("+answer = 42", companion.get_diff(task["task_id"], OWNER))
        patch_path = self.state / task["task_id"] / "diff.patch"
        self.assertNotIn(b"\r\r\n", patch_path.read_bytes())
        git(self.source, "apply", "--check", str(patch_path))
        self.assertEqual((self.source / "calculator.py").read_text(), "answer = 0\n")
        restored = self.companion()
        self.assertEqual(restored.get_task_progress(task["task_id"], OWNER)["head_sha"], result["head_sha"])
        self.assertEqual(len(restored.get_preview_or_test_artifacts(task["task_id"], OWNER)), 1)
        with self.assertRaisesRegex(CompanionError, "authentication"):
            restored.get_task_progress(task["task_id"], "wrong-owner-session")
        with self.assertRaisesRegex(CompanionError, "Invalid task"):
            restored.get_task_progress("../source", OWNER)
        verified = restored.verify_task(task["task_id"], OWNER, [[sys.executable, "-c", "from calculator import answer; assert answer == 42; print('verification PASS')"]])
        self.assertEqual(verified["status"], "VERIFIED_LOCAL")
        self.assertNotEqual(verified["verification"]["checkout"], str(checkout))
        rolled_back = restored.rollback_task(task["task_id"], OWNER)
        self.assertEqual(rolled_back["status"], "ROLLED_BACK")
        self.assertEqual(git(checkout, "diff", "--name-only", task["base_sha"]), "")
    def test_cancel_running_task_from_a_separate_control_plane_instance(self):
        BlockingExecutor.ready.clear()
        BlockingExecutor.stopped.clear()
        companion = self.companion(BlockingExecutor)
        task = companion.create_task("Wait until cancelled", self.source, OWNER)
        result = {}
        thread = threading.Thread(target=lambda: result.update(companion.run_task(task["task_id"], OWNER, provider="fixture", model="fixture")))
        thread.start()
        self.assertTrue(BlockingExecutor.ready.wait(3))
        self.companion(BlockingExecutor).stop_task(task["task_id"], OWNER)
        thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result["status"], "CANCELLED")
        self.assertTrue(BlockingExecutor.stopped.is_set())
    def test_stop_before_run_never_starts_executor(self):
        companion = self.companion()
        task = companion.create_task("Cancel before model request", self.source, OWNER)
        companion.stop_task(task["task_id"], OWNER)
        result = companion.run_task(task["task_id"], OWNER, provider="fixture", model="fixture")
        self.assertEqual(result["status"], "CANCELLED")
        self.assertNotIn("executor_pid", result)
    def test_task_timeout_cancels_executor_and_persists_result(self):
        BlockingExecutor.ready.clear()
        BlockingExecutor.stopped.clear()
        companion = self.companion(BlockingExecutor)
        task = companion.create_task("Stop at the task deadline", self.source, OWNER)
        result = companion.run_task(task["task_id"], OWNER, provider="fixture", model="fixture", timeout_seconds=0.25)
        self.assertEqual(result["status"], "TIMED_OUT")
        self.assertTrue(BlockingExecutor.stopped.is_set())
        self.assertEqual(self.companion().get_task_progress(task["task_id"], OWNER)["status"], "TIMED_OUT")
    def test_state_directory_cannot_be_inside_source(self):
        with self.assertRaisesRegex(CompanionError, "outside"):
            DeveloperCompanion(source_checkout=self.source, state_dir=self.source / "tasks")

    def test_controller_commits_allowed_new_source_when_agent_cannot_write_git(self):
        companion = self.companion(UncommittedExecutor)
        task = companion.create_task("Propose a source fix", self.source, OWNER, allowed_paths=["calculator.py", "new_check.py"])
        result = companion.run_task(task["task_id"], OWNER, provider="fixture", model="fixture")
        self.assertEqual(result["status"], "COMPLETED_UNVERIFIED")
        self.assertNotEqual(result["head_sha"], task["base_sha"])
        self.assertEqual(result["untracked_paths"], [])
        self.assertEqual(result["changed_paths"], ["calculator.py", "new_check.py"])
        self.assertEqual(git(Path(result["checkout"]), "status", "--porcelain"), "")
        self.assertIn("+assert 6 * 7", companion.get_diff(task["task_id"], OWNER))

    def test_out_of_scope_proposal_is_preserved_and_not_committed(self):
        companion = self.companion(UncommittedExecutor)
        task = companion.create_task("Only fix calculator", self.source, OWNER, allowed_paths=["calculator.py"])
        result = companion.run_task(task["task_id"], OWNER, provider="fixture", model="fixture")
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error_code"], "OUTPUT_SCOPE_VIOLATION")
        self.assertEqual(result["head_sha"], task["base_sha"])
        self.assertIn("new_check.py", result["scope_violations"])
        self.assertTrue((Path(result["checkout"]) / "new_check.py").is_file())

    def test_disk_preflight_refuses_snapshot_before_allocating_task(self):
        from types import SimpleNamespace
        companion = self.companion()
        with patch("tools.developer_companion.service.shutil.disk_usage", return_value=SimpleNamespace(free=1)):
            with self.assertRaisesRegex(CompanionError, "Insufficient task disk"):
                companion.create_task("No space", self.source, OWNER)
        self.assertEqual(list(self.state.iterdir()), [])

    def test_progress_redacts_environment_tokens_and_bearer(self):
        from tools.developer_companion.runtime import redact
        value = 'RESET_TOKEN="local-test-value"; TOKEN=another-value; Authorization: Bearer private-value'
        actual = redact(value)
        for secret in ("local-test-value", "another-value", "private-value"):
            self.assertNotIn(secret, actual)


if __name__ == "__main__":
    unittest.main()
