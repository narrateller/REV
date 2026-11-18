"""Regression tests for lossless archive and retired-owner protection."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from verify_output import blob, claims


class OperatorRotationTests(unittest.TestCase):
    def test_archive_corruption_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "archive.bin").write_bytes(b"original\r\n")
            record = {"path": "archive.bin", "sha256": hashlib.sha256(b"original\r\n").hexdigest()}
            self.assertEqual(blob(root, record), b"original\r\n")
            (root / "archive.bin").write_bytes(b"original\n")
            with self.assertRaisesRegex(ValueError, "Hash mismatch"):
                blob(root, record)

    def fixture(self, root, task_id, owner):
        directory = root / "coordination/claims"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{task_id}.json").write_text(json.dumps({
            "task_id": task_id, "role": "R3", "status": "ACCEPTED_MAIN", "owner_session": owner,
            "proposed_at_utc": "2026-11-18T00:00:00Z", "lease_expires_at": "2026-11-19T00:00:00Z"}))
        task = root / "coordination/tasks" / task_id
        task.mkdir(parents=True)
        (task / "task.json").write_text(json.dumps({"role": "R3"}))

    def test_retired_owner_cannot_reappear(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root, "NEW-TASK", "old-session")
            with self.assertRaisesRegex(ValueError, "Retired session"):
                claims(root, {"old-session"})

    def test_one_owner_cannot_hold_two_tasks(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root, "TASK-A", "new-session")
            self.assertEqual(claims(root, set()), 1)
            self.fixture(root, "TASK-B", "new-session")
            with self.assertRaisesRegex(ValueError, "multiple tasks"):
                claims(root, set())
