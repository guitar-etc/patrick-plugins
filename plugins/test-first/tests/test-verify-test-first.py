#!/usr/bin/env python3
"""Tests for verify-test-first.py and verify-test-first-stop.py hook scripts."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

VERIFY_SCRIPT = os.path.join(
    os.path.dirname(__file__),
    "..", "hooks", "scripts", "verify-test-first.py"
)
STOP_SCRIPT = os.path.join(
    os.path.dirname(__file__),
    "..", "hooks", "scripts", "verify-test-first-stop.py"
)
FLAG_DIR = "/tmp/test-first-verified"


def run_hook(script_path, input_data):
    """Execute a hook script with JSON input via stdin."""
    proc = subprocess.run(
        ["python3", script_path],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip(), proc.returncode


def write_requirements_yaml(cwd, req_ids):
    """Write a requirements.yaml file with given REQ IDs."""
    lines = ["requirements:"]
    for rid in req_ids:
        lines.append(f"  - id: {rid}")
        lines.append(f"    prompt: \"test prompt\"")
        lines.append(f"    rephrase: \"test rephrase\"")
        lines.append(f"    status: reviewed")
    with open(os.path.join(cwd, "requirements.yaml"), "w") as f:
        f.write("\n".join(lines) + "\n")


def write_test_file(cwd, filename, content):
    """Write a test file in the cwd."""
    path = os.path.join(cwd, filename)
    with open(path, "w") as f:
        f.write(content)
    return path


class TestVerifyTestFirst(unittest.TestCase):
    """Tests for the PreToolUse verify-test-first.py gate."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.session_id = "test-session-tf"
        flag_file = os.path.join(FLAG_DIR, self.session_id)
        if os.path.exists(flag_file):
            os.remove(flag_file)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        flag_file = os.path.join(FLAG_DIR, self.session_id)
        if os.path.exists(flag_file):
            os.remove(flag_file)

    def base_input(self, file_path="app.py"):
        return {
            "session_id": self.session_id,
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": os.path.join(self.tmpdir, file_path)},
            "cwd": self.tmpdir,
        }

    # --- PASS cases ---

    def test_pass_no_requirements_yaml(self):
        """Should pass when no requirements.yaml exists."""
        stdout, rc = run_hook(VERIFY_SCRIPT, self.base_input())
        self.assertEqual(stdout, "")

    def test_pass_subagent_bypass(self):
        """Should pass when agent_id is present."""
        write_requirements_yaml(self.tmpdir, ["REQ-001"])
        inp = self.base_input()
        inp["agent_id"] = "sub-123"
        stdout, rc = run_hook(VERIFY_SCRIPT, inp)
        self.assertEqual(stdout, "")

    def test_pass_non_code_file(self):
        """Should pass for non-code file extensions (.md, .json, .yaml)."""
        write_requirements_yaml(self.tmpdir, ["REQ-001"])
        for ext in ["README.md", "config.json", "data.yaml", "notes.txt"]:
            stdout, rc = run_hook(VERIFY_SCRIPT, self.base_input(ext))
            self.assertEqual(stdout, "", f"Should allow {ext}")

    def test_pass_test_file(self):
        """Should pass when target is a test file."""
        write_requirements_yaml(self.tmpdir, ["REQ-001"])
        for fname in ["test_auth.py", "auth_test.py", "auth.test.js", "auth.spec.ts"]:
            stdout, rc = run_hook(VERIFY_SCRIPT, self.base_input(fname))
            self.assertEqual(stdout, "", f"Should allow test file {fname}")

    def test_pass_all_reqs_covered(self):
        """Should pass when all requirements have test annotations."""
        write_requirements_yaml(self.tmpdir, ["REQ-001", "REQ-002"])
        write_test_file(self.tmpdir, "test_features.py", """\
# REQ-001
def test_feature_one():
    pass

# REQ-002
def test_feature_two():
    pass
""")
        stdout, rc = run_hook(VERIFY_SCRIPT, self.base_input())
        self.assertEqual(stdout, "")

    def test_pass_empty_requirements(self):
        """Should pass when requirements.yaml exists but has no entries."""
        with open(os.path.join(self.tmpdir, "requirements.yaml"), "w") as f:
            f.write("requirements:\n")
        stdout, rc = run_hook(VERIFY_SCRIPT, self.base_input())
        self.assertEqual(stdout, "")

    def test_pass_no_file_path(self):
        """Should pass when tool_input has no file_path."""
        write_requirements_yaml(self.tmpdir, ["REQ-001"])
        inp = self.base_input()
        inp["tool_input"] = {}
        stdout, rc = run_hook(VERIFY_SCRIPT, inp)
        self.assertEqual(stdout, "")

    # --- DENY cases ---

    def test_deny_missing_test_for_req(self):
        """Should deny when a requirement has no test annotation."""
        write_requirements_yaml(self.tmpdir, ["REQ-001"])
        stdout, rc = run_hook(VERIFY_SCRIPT, self.base_input())
        result = json.loads(stdout)
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("REQ-001", result["hookSpecificOutput"]["permissionDecisionReason"])

    def test_deny_partial_coverage(self):
        """Should deny when some but not all requirements have tests."""
        write_requirements_yaml(self.tmpdir, ["REQ-001", "REQ-002"])
        write_test_file(self.tmpdir, "test_features.py", """\
# REQ-001
def test_feature_one():
    pass
""")
        stdout, rc = run_hook(VERIFY_SCRIPT, self.base_input())
        result = json.loads(stdout)
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("REQ-002", result["hookSpecificOutput"]["permissionDecisionReason"])
        self.assertNotIn("REQ-001", result["hookSpecificOutput"]["permissionDecisionReason"])

    # --- Edge cases ---

    def test_js_comment_annotation(self):
        """Should recognize // REQ-NNN in JS/TS test files."""
        write_requirements_yaml(self.tmpdir, ["REQ-001"])
        write_test_file(self.tmpdir, "auth.test.ts", """\
// REQ-001
test('auth works', () => {});
""")
        stdout, rc = run_hook(VERIFY_SCRIPT, self.base_input())
        self.assertEqual(stdout, "")

    def test_cache_works(self):
        """Should use cache on second call with same state."""
        write_requirements_yaml(self.tmpdir, ["REQ-001"])
        write_test_file(self.tmpdir, "test_auth.py", "# REQ-001\ndef test_auth(): pass\n")
        # First call: verify and cache
        stdout, rc = run_hook(VERIFY_SCRIPT, self.base_input())
        self.assertEqual(stdout, "")
        # Second call: cache hit
        stdout, rc = run_hook(VERIFY_SCRIPT, self.base_input())
        self.assertEqual(stdout, "")


class TestVerifyTestFirstStop(unittest.TestCase):
    """Tests for the Stop hook verify-test-first-stop.py."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def base_input(self):
        return {
            "hook_event_name": "Stop",
            "cwd": self.tmpdir,
        }

    def test_pass_no_requirements_yaml(self):
        """Should pass when no requirements.yaml exists."""
        stdout, rc = run_hook(STOP_SCRIPT, self.base_input())
        self.assertEqual(stdout, "")

    def test_pass_all_covered(self):
        """Should pass when all requirements have tests."""
        write_requirements_yaml(self.tmpdir, ["REQ-001"])
        write_test_file(self.tmpdir, "test_auth.py", "# REQ-001\ndef test_auth(): pass\n")
        stdout, rc = run_hook(STOP_SCRIPT, self.base_input())
        self.assertEqual(stdout, "")

    def test_block_missing_coverage(self):
        """Should block when requirements lack tests."""
        write_requirements_yaml(self.tmpdir, ["REQ-001", "REQ-002"])
        stdout, rc = run_hook(STOP_SCRIPT, self.base_input())
        result = json.loads(stdout)
        self.assertEqual(result["decision"], "block")
        self.assertIn("0/2", result["reason"])
        self.assertIn("REQ-001", result["reason"])
        self.assertIn("REQ-002", result["reason"])

    def test_block_partial_coverage(self):
        """Should block with correct count when partial coverage."""
        write_requirements_yaml(self.tmpdir, ["REQ-001", "REQ-002"])
        write_test_file(self.tmpdir, "test_auth.py", "# REQ-001\ndef test_auth(): pass\n")
        stdout, rc = run_hook(STOP_SCRIPT, self.base_input())
        result = json.loads(stdout)
        self.assertEqual(result["decision"], "block")
        self.assertIn("1/2", result["reason"])
        self.assertIn("REQ-002", result["reason"])
        self.assertNotIn("REQ-001", result["reason"])

    def test_pass_empty_requirements(self):
        """Should pass when requirements.yaml has no entries."""
        with open(os.path.join(self.tmpdir, "requirements.yaml"), "w") as f:
            f.write("requirements:\n")
        stdout, rc = run_hook(STOP_SCRIPT, self.base_input())
        self.assertEqual(stdout, "")


class TestRemindTestFirst(unittest.TestCase):
    """Tests for the PostToolUse remind-test-first.py hook."""

    SCRIPT = os.path.join(
        os.path.dirname(__file__),
        "..", "hooks", "scripts", "remind-test-first.py"
    )

    def test_reminds_on_requirements_yaml(self):
        """Should output reminder when requirements.yaml is modified."""
        inp = {
            "tool_name": "Write",
            "tool_input": {"file_path": "/some/path/requirements.yaml"},
        }
        stdout, rc = run_hook(self.SCRIPT, inp)
        self.assertEqual(stdout, "Invoke the test-first skill.")

    def test_silent_on_other_files(self):
        """Should output nothing when other files are modified."""
        inp = {
            "tool_name": "Write",
            "tool_input": {"file_path": "/some/path/app.py"},
        }
        stdout, rc = run_hook(self.SCRIPT, inp)
        self.assertEqual(stdout, "")

    def test_silent_on_no_file_path(self):
        """Should output nothing when no file_path in tool_input."""
        inp = {
            "tool_name": "Write",
            "tool_input": {},
        }
        stdout, rc = run_hook(self.SCRIPT, inp)
        self.assertEqual(stdout, "")


if __name__ == "__main__":
    unittest.main()
