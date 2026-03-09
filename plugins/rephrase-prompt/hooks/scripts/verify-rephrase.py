#!/usr/bin/env python3
"""PreToolUse hook: verify Claude's first assistant message after the last user message contains 'Rephrase: '.
Caches the verified user message index to avoid re-parsing the transcript on every tool call."""

import json
import os
import sys

FLAG_DIR = "/tmp/claude-rephrase"


def flag_path(session_id):
    return os.path.join(FLAG_DIR, session_id)


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

    # Extract text
    content = first_assistant_after_user.get("message", {}).get("content", [])
    text = ""
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text += block.get("text", "")

    if "Rephrase: " in text or "Rephrase:" in text:
        # Verified — cache so we skip on subsequent tool calls this turn
        os.makedirs(FLAG_DIR, exist_ok=True)
        with open(fp, "w") as f:
            f.write(str(last_user_idx))
        return

    # Missing rephrase — block
    print(json.dumps({
        "hookSpecificOutput": {
            "permissionDecision": "deny",
            "permissionDecisionReason": "Invoke /rephrase"
        }
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({
            "hookSpecificOutput": {
                "permissionDecision": "deny",
                "permissionDecisionReason": f"verify-rephrase.py errored: {type(e).__name__}: {e}"
            }
        }))
