#!/usr/bin/env python3
"""PreToolUse hook: verify Claude's first assistant message after the last user message
contains 'Requirements Update: '. Cross-checks mentioned REQ labels against requirements.yaml.
Caches the verified user message index to avoid re-parsing the transcript on every tool call."""

import json
import os
import re
import sys

FLAG_DIR = "/tmp/requirements-capture"


def flag_path(session_id):
    return os.path.join(FLAG_DIR, session_id)


def parse_requirements_yaml(cwd):
    """Read requirements.yaml and return a set of REQ-NNN IDs present in the file."""
    path = os.path.join(cwd, "requirements.yaml")
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        content = f.read()
    return set(re.findall(r"id:\s*(REQ-\d+)", content))


def parse_update_line(text):
    """Extract REQ labels and actions from a 'Requirements Update: ' line.
    Returns list of (req_id, action) tuples, or None if 'None'."""
    # Find the Requirements Update line
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("Requirements Update:"):
            rest = line[len("Requirements Update:"):].strip()
            if rest.lower() == "none":
                return []
            # Parse entries like "REQ-003 added (desc), REQ-001 modified (desc)"
            pattern = r"(REQ-\d+)\s+(added|modified|deleted)"
            return re.findall(pattern, rest)
    return None


def cross_check(updates, reqs_set):
    """Verify that stated updates match the actual requirements.yaml state.
    Returns list of error strings, empty if all checks pass."""
    errors = []
    for req_id, action in updates:
        if action == "added":
            if req_id not in reqs_set:
                errors.append(f"{req_id} claimed added but not found in requirements.yaml")
        elif action == "modified":
            if req_id not in reqs_set:
                errors.append(f"{req_id} claimed modified but not found in requirements.yaml")
        elif action == "deleted":
            if req_id in reqs_set:
                errors.append(f"{req_id} claimed deleted but still exists in requirements.yaml")
    return errors


def main():
    hook_input = json.loads(sys.stdin.read())

    # Skip check inside subagents
    if "agent_id" in hook_input:
        return

    session_id = hook_input.get("session_id", "")
    transcript_path = hook_input.get("transcript_path")
    if not transcript_path:
        return

    # Read transcript to find last user message index
    last_user_idx = -1
    entries = []
    with open(transcript_path) as f:
        for line in f:
            try:
                entries.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue

    for i, entry in enumerate(entries):
        if entry.get("type") == "user":
            last_user_idx = i

    if last_user_idx < 0:
        return

    # Check if we already verified this user message
    fp = flag_path(session_id)
    if os.path.exists(fp):
        with open(fp) as f:
            try:
                verified_idx = int(f.read().strip())
                if verified_idx == last_user_idx:
                    return  # Already verified for this prompt
            except ValueError:
                pass

    # Find first assistant message after last user message
    first_assistant_after_user = None
    for i in range(last_user_idx + 1, len(entries)):
        if entries[i].get("type") == "assistant":
            first_assistant_after_user = entries[i]
            break

    if first_assistant_after_user is None:
        return

    # Extract text from assistant message
    content = first_assistant_after_user.get("message", {}).get("content", [])
    text = ""
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text += block.get("text", "")

    if "Requirements Update: " not in text and "Requirements Update:" not in text:
        # Missing requirements update — block
        print(json.dumps({
            "hookSpecificOutput": {
                "permissionDecision": "deny",
                "permissionDecisionReason": "Invoke the uat-capture skill."
            }
        }))
        return

    # Two-step verification: cross-check stated updates against requirements.yaml
    updates = parse_update_line(text)
    if updates is None:
        # Could not parse the update line
        print(json.dumps({
            "hookSpecificOutput": {
                "permissionDecision": "deny",
                "permissionDecisionReason": "Invoke the uat-capture skill. The Requirements Update line could not be parsed."
            }
        }))
        return

    if updates:  # Non-empty means actual changes were claimed
        cwd = hook_input.get("cwd", os.getcwd())
        reqs_set = parse_requirements_yaml(cwd)
        errors = cross_check(updates, reqs_set)
        if errors:
            reason = "Requirements Update cross-check failed: " + "; ".join(errors)
            print(json.dumps({
                "hookSpecificOutput": {
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason
                }
            }))
            return

    # Verified — cache so we skip on subsequent tool calls this turn
    os.makedirs(FLAG_DIR, exist_ok=True)
    with open(fp, "w") as f:
        f.write(str(last_user_idx))


if __name__ == "__main__":
    main()
