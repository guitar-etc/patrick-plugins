#!/usr/bin/env python3
"""Tests for verify-rephrase.py hook script.
Run: python3 test-verify-rephrase.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "hooks", "scripts", "verify-rephrase.py"
)
FLAG_DIR = "/tmp/claude-rephrase"


def run_hook(hook_input: dict) -> tuple[str, int]:
    """Run verify-rephrase.py with given hook_input via stdin. Returns (stdout, returncode)."""
    result = subprocess.run(
        [sys.executable, SCRIPT_PATH],
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.returncode


def make_transcript(entries: list[dict], path: str):
    """Write JSONL transcript file."""
    with open(path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def make_assistant_msg(text: str) -> dict:
    return {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": text}]},
    }


def make_user_msg(text: str = "hello") -> dict:
    return {
        "type": "user",
        "message": {"content": [{"type": "text", "text": text}]},
    }


class TestVerifyRephrase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.transcript_path = os.path.join(self.tmpdir, "transcript.jsonl")
        self.session_id = f"test-session-{id(self)}"
        # Clean up any cached flag from previous runs
        flag = os.path.join(FLAG_DIR, self.session_id)
        if os.path.exists(flag):
            os.remove(flag)

    def tearDown(self):
        # Clean up flag file
        flag = os.path.join(FLAG_DIR, self.session_id)
        if os.path.exists(flag):
            os.remove(flag)
        # Clean up transcript
        if os.path.exists(self.transcript_path):
            os.remove(self.transcript_path)
        os.rmdir(self.tmpdir)

    def base_input(self) -> dict:
        return {
            "session_id": self.session_id,
            "transcript_path": self.transcript_path,
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
        }

    # --- PASS cases (no output = allow) ---

    def test_pass_when_rephrase_present(self):
        """Should allow when first assistant message contains 'Rephrase: '."""
        make_transcript(
            [
                make_user_msg("do something"),
                make_assistant_msg("Rephrase: I want you to do something.\n\nOkay, doing it."),
            ],
            self.transcript_path,
        )
        stdout, rc = run_hook(self.base_input())
        self.assertEqual(stdout, "", "Should produce no output (allow)")
        self.assertEqual(rc, 0)

    def test_pass_when_rephrase_colon_no_space(self):
        """Should allow 'Rephrase:' without trailing space too."""
        make_transcript(
            [
                make_user_msg(),
                make_assistant_msg("Rephrase: something\n\nrest"),
            ],
            self.transcript_path,
        )
        stdout, _ = run_hook(self.base_input())
        self.assertEqual(stdout, "")

    def test_pass_skips_subagents(self):
        """Should skip verification inside subagents."""
        make_transcript(
            [make_user_msg(), make_assistant_msg("no rephrase here")],
            self.transcript_path,
        )
        hook_input = self.base_input()
        hook_input["agent_id"] = "some-subagent-id"
        stdout, _ = run_hook(hook_input)
        self.assertEqual(stdout, "", "Subagents should be skipped")

    def test_pass_no_assistant_yet(self):
        """Should allow when there's no assistant message yet (first response pending)."""
        make_transcript([make_user_msg()], self.transcript_path)
        stdout, _ = run_hook(self.base_input())
        self.assertEqual(stdout, "", "No assistant message yet = allow")

    def test_pass_no_transcript(self):
        """Should allow when transcript_path is missing."""
        hook_input = self.base_input()
        del hook_input["transcript_path"]
        stdout, _ = run_hook(hook_input)
        self.assertEqual(stdout, "")

    def test_pass_empty_transcript(self):
        """Should allow on empty transcript."""
        make_transcript([], self.transcript_path)
        stdout, _ = run_hook(self.base_input())
        self.assertEqual(stdout, "")

    # --- BLOCK cases (deny output) ---

    def test_block_when_rephrase_missing(self):
        """Should block when first assistant message lacks rephrase."""
        make_transcript(
            [
                make_user_msg("do something"),
                make_assistant_msg("Sure, I'll do that right away."),
            ],
            self.transcript_path,
        )
        stdout, rc = run_hook(self.base_input())
        self.assertEqual(rc, 0)
        output = json.loads(stdout)
        self.assertEqual(
            output["hookSpecificOutput"]["permissionDecision"], "deny"
        )
        self.assertEqual(
            output["hookSpecificOutput"]["permissionDecisionReason"],
            "Invoke /rephrase",
        )

    def test_block_rephrase_in_second_assistant_not_first(self):
        """Should block if rephrase only appears in second assistant message."""
        make_transcript(
            [
                make_user_msg(),
                make_assistant_msg("I'll help with that."),
                make_assistant_msg("Rephrase: I want you to help."),
            ],
            self.transcript_path,
        )
        stdout, _ = run_hook(self.base_input())
        output = json.loads(stdout)
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    # --- Flag caching ---

    def test_flag_caching_skips_recheck(self):
        """After verification passes, cached flag should skip re-parsing."""
        make_transcript(
            [make_user_msg(), make_assistant_msg("Rephrase: ok\n\ndone")],
            self.transcript_path,
        )
        # First call: verifies and caches
        stdout1, _ = run_hook(self.base_input())
        self.assertEqual(stdout1, "")

        # Verify flag file exists
        flag = os.path.join(FLAG_DIR, self.session_id)
        self.assertTrue(os.path.exists(flag), "Flag file should be created")

        # Second call: should return immediately from cache
        stdout2, _ = run_hook(self.base_input())
        self.assertEqual(stdout2, "")

    def test_flag_resets_on_new_user_message(self):
        """Flag should not match when a new user message appears (higher index)."""
        make_transcript(
            [make_user_msg(), make_assistant_msg("Rephrase: ok\n\ndone")],
            self.transcript_path,
        )
        # First call caches for user_idx=0
        run_hook(self.base_input())

        # Add new user message + assistant without rephrase
        make_transcript(
            [
                make_user_msg(),
                make_assistant_msg("Rephrase: ok\n\ndone"),
                make_user_msg("next task"),
                make_assistant_msg("Sure, doing it."),
            ],
            self.transcript_path,
        )
        stdout, _ = run_hook(self.base_input())
        output = json.loads(stdout)
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    # --- Edge cases ---

    def test_tool_result_as_user_resets_index(self):
        """Tool results appear as type:user entries, so they shift last_user_idx."""
        tool_result_user = {
            "type": "user",
            "message": {
                "content": [
                    {"type": "tool_result", "tool_use_id": "x", "content": "result"}
                ]
            },
        }
        make_transcript(
            [
                make_user_msg(),
                make_assistant_msg("Rephrase: ok\n\nLet me read the file."),
                tool_result_user,  # This becomes the new "last user"
                make_assistant_msg("Rephrase: continuing\n\nHere's what I found."),
            ],
            self.transcript_path,
        )
        stdout, _ = run_hook(self.base_input())
        # The "last user" is the tool_result at idx 2, first assistant after is idx 3 which has Rephrase
        self.assertEqual(stdout, "")

    def test_multiple_text_blocks(self):
        """Should find Rephrase: across multiple text blocks."""
        make_transcript(
            [
                make_user_msg(),
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {"type": "text", "text": "Rephrase: "},
                            {"type": "text", "text": "I want help.\n\nOk."},
                        ]
                    },
                },
            ],
            self.transcript_path,
        )
        stdout, _ = run_hook(self.base_input())
        self.assertEqual(stdout, "")


if __name__ == "__main__":
    unittest.main()
