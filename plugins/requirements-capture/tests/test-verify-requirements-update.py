#!/usr/bin/env python3
"""Tests for verify-requirements-update.py hook script."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "hooks", "scripts", "verify-requirements-update.py"
)
FLAG_DIR = "/tmp/requirements-capture"


def run_hook(input_data):
    """Execute the hook script with JSON input via stdin."""
    proc = subprocess.run(
        ["python3", SCRIPT_PATH],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip(), proc.returncode


def make_user_msg(text):
    return {"type": "user", "message": {"content": [{"type": "text", "text": text}]}}


def make_assistant_msg(text):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def make_transcript(path, entries):
    """Write JSONL transcript file."""
    with open(path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def write_requirements_yaml(cwd, entries):
    """Write a requirements.yaml file with given entries."""
    lines = ["requirements:"]
    for entry in entries:
        lines.append(f"  - id: {entry['id']}")
        lines.append(f"    prompt: \"{entry.get('prompt', 'test')}\"")
        lines.append(f"    rephrase: \"{entry.get('rephrase', 'test')}\"")
        lines.append(f"    status: {entry.get('status', 'reviewed')}")
    with open(os.path.join(cwd, "requirements.yaml"), "w") as f:
        f.write("\n".join(lines) + "\n")


class TestVerifyRequirementsUpdate(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.transcript_path = os.path.join(self.tmpdir, "transcript.jsonl")
        self.session_id = "test-session-req"
        # Clean flag file
        flag_file = os.path.join(FLAG_DIR, self.session_id)
        if os.path.exists(flag_file):
            os.remove(flag_file)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        flag_file = os.path.join(FLAG_DIR, self.session_id)
        if os.path.exists(flag_file):
            os.remove(flag_file)

    def base_input(self):
        return {
            "session_id": self.session_id,
            "transcript_path": self.transcript_path,
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "cwd": self.tmpdir,
        }

    # --- PASS cases (no output = allow) ---

    def test_pass_with_requirements_update_none(self):
        """Should pass when assistant outputs 'Requirements Update: None'."""
        make_transcript(self.transcript_path, [
            make_user_msg("how does auth work?"),
            make_assistant_msg("Requirements Update: None\n\nHere's how auth works..."),
        ])
        stdout, rc = run_hook(self.base_input())
        self.assertEqual(stdout, "")
        self.assertEqual(rc, 0)

    def test_pass_with_requirements_update_added(self):
        """Should pass when assistant outputs 'Requirements Update: REQ-001 added' and file matches."""
        write_requirements_yaml(self.tmpdir, [{"id": "REQ-001"}])
        make_transcript(self.transcript_path, [
            make_user_msg("add a login button"),
            make_assistant_msg("Requirements Update: REQ-001 added (Add login button)\n\nI'll add the button..."),
        ])
        stdout, rc = run_hook(self.base_input())
        self.assertEqual(stdout, "")
        self.assertEqual(rc, 0)

    def test_pass_subagent_bypass(self):
        """Should pass when agent_id is present (subagent)."""
        make_transcript(self.transcript_path, [
            make_user_msg("do something"),
        ])
        inp = self.base_input()
        inp["agent_id"] = "sub-123"
        stdout, rc = run_hook(inp)
        self.assertEqual(stdout, "")
        self.assertEqual(rc, 0)

    def test_pass_no_transcript(self):
        """Should pass when transcript_path is missing."""
        inp = self.base_input()
        del inp["transcript_path"]
        stdout, rc = run_hook(inp)
        self.assertEqual(stdout, "")
        self.assertEqual(rc, 0)

    def test_pass_no_user_message(self):
        """Should pass when transcript has no user message."""
        make_transcript(self.transcript_path, [
            make_assistant_msg("Hello!"),
        ])
        stdout, rc = run_hook(self.base_input())
        self.assertEqual(stdout, "")
        self.assertEqual(rc, 0)

    def test_pass_no_assistant_response_yet(self):
        """Should pass when assistant hasn't responded yet."""
        make_transcript(self.transcript_path, [
            make_user_msg("add a feature"),
        ])
        stdout, rc = run_hook(self.base_input())
        self.assertEqual(stdout, "")
        self.assertEqual(rc, 0)

    def test_pass_cached_verification(self):
        """Should pass on second call using cached verification."""
        make_transcript(self.transcript_path, [
            make_user_msg("hello"),
            make_assistant_msg("Requirements Update: None\n\nHi!"),
        ])
        # First call: verify and cache
        stdout, rc = run_hook(self.base_input())
        self.assertEqual(stdout, "")
        # Second call: should use cache
        stdout, rc = run_hook(self.base_input())
        self.assertEqual(stdout, "")

    # --- DENY cases ---

    def test_deny_missing_requirements_update(self):
        """Should deny when assistant response has no 'Requirements Update:' prefix."""
        make_transcript(self.transcript_path, [
            make_user_msg("add a feature"),
            make_assistant_msg("Sure, I'll add that feature right away."),
        ])
        stdout, rc = run_hook(self.base_input())
        result = json.loads(stdout)
        self.assertEqual(
            result["hookSpecificOutput"]["permissionDecision"], "deny"
        )

    def test_deny_cross_check_added_but_missing(self):
        """Should deny when 'REQ-001 added' is claimed but REQ-001 not in file."""
        # No requirements.yaml at all
        make_transcript(self.transcript_path, [
            make_user_msg("add a feature"),
            make_assistant_msg("Requirements Update: REQ-001 added (New feature)\n\nImplementing..."),
        ])
        stdout, rc = run_hook(self.base_input())
        result = json.loads(stdout)
        self.assertEqual(
            result["hookSpecificOutput"]["permissionDecision"], "deny"
        )
        self.assertIn("REQ-001 claimed added but not found", result["hookSpecificOutput"]["permissionDecisionReason"])

    def test_deny_cross_check_deleted_but_still_exists(self):
        """Should deny when 'REQ-001 deleted' is claimed but REQ-001 still in file."""
        write_requirements_yaml(self.tmpdir, [{"id": "REQ-001"}])
        make_transcript(self.transcript_path, [
            make_user_msg("remove REQ-001"),
            make_assistant_msg("Requirements Update: REQ-001 deleted (Removed feature)\n\nDone."),
        ])
        stdout, rc = run_hook(self.base_input())
        result = json.loads(stdout)
        self.assertEqual(
            result["hookSpecificOutput"]["permissionDecision"], "deny"
        )
        self.assertIn("REQ-001 claimed deleted but still exists", result["hookSpecificOutput"]["permissionDecisionReason"])

    def test_deny_cross_check_modified_but_missing(self):
        """Should deny when 'REQ-002 modified' is claimed but REQ-002 not in file."""
        write_requirements_yaml(self.tmpdir, [{"id": "REQ-001"}])
        make_transcript(self.transcript_path, [
            make_user_msg("change something"),
            make_assistant_msg("Requirements Update: REQ-002 modified (Updated feature)\n\nDone."),
        ])
        stdout, rc = run_hook(self.base_input())
        result = json.loads(stdout)
        self.assertEqual(
            result["hookSpecificOutput"]["permissionDecision"], "deny"
        )
        self.assertIn("REQ-002 claimed modified but not found", result["hookSpecificOutput"]["permissionDecisionReason"])

    # --- Edge cases ---

    def test_pass_multiple_text_blocks(self):
        """Should find 'Requirements Update:' across multiple text blocks."""
        make_transcript(self.transcript_path, [
            make_user_msg("hello"),
            {"type": "assistant", "message": {"content": [
                {"type": "text", "text": "Requirements Update: None"},
                {"type": "text", "text": "\n\nMore text here."},
            ]}},
        ])
        stdout, rc = run_hook(self.base_input())
        self.assertEqual(stdout, "")

    def test_pass_requirements_update_colon_no_space(self):
        """Should accept 'Requirements Update:' without trailing space."""
        make_transcript(self.transcript_path, [
            make_user_msg("hello"),
            make_assistant_msg("Requirements Update:None\n\nHi!"),
        ])
        # The marker check accepts both "Requirements Update: " and "Requirements Update:"
        stdout, rc = run_hook(self.base_input())
        self.assertEqual(stdout, "")


if __name__ == "__main__":
    unittest.main()
