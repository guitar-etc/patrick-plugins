#!/usr/bin/env python3
"""PreToolUse hook: block Write/Edit on code files if any requirement in
requirements.yaml lacks a test annotation (# REQ-NNN) in the project's test files.

Algorithm:
1. If agent_id present → ALLOW (subagent bypass)
2. If no requirements.yaml in cwd → ALLOW (nothing to enforce)
3. If target file is not a code extension → ALLOW
4. If target file matches test pattern → ALLOW
5. Parse requirements.yaml for all REQ-NNN IDs
6. Grep test files for # REQ-NNN annotations
7. If any REQ lacks a test → DENY
8. Cache result keyed on requirements.yaml mtime + test dir mtime
"""

import json
import os
import sys

# Add script directory to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_test_first import (
    is_code_file,
    is_test_file,
    get_requirements,
    find_test_files,
    get_covered_reqs,
)

FLAG_DIR = "/tmp/test-first-verified"


def get_cache_key(cwd):
    """Build cache key from requirements.yaml mtime and test files."""
    req_path = os.path.join(cwd, "requirements.yaml")
    req_mtime = os.path.getmtime(req_path) if os.path.exists(req_path) else 0

    test_files = find_test_files(cwd)
    test_mtime = max(
        (os.path.getmtime(f) for f in test_files),
        default=0,
    )
    return f"{req_mtime}:{test_mtime}"


def flag_path(session_id):
    return os.path.join(FLAG_DIR, session_id)


def main():
    hook_input = json.loads(sys.stdin.read())

    # Subagent bypass
    if "agent_id" in hook_input:
        return

    cwd = hook_input.get("cwd", os.getcwd())

    # No requirements.yaml → nothing to enforce
    req_path = os.path.join(cwd, "requirements.yaml")
    if not os.path.exists(req_path):
        return

    # Check target file
    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path:
        return

    # Allow non-code files
    if not is_code_file(file_path):
        return

    # Allow test files
    if is_test_file(file_path):
        return

    # Check cache
    session_id = hook_input.get("session_id", "default")
    fp = flag_path(session_id)
    cache_key = get_cache_key(cwd)

    if os.path.exists(fp):
        with open(fp) as f:
            try:
                cached = f.read().strip()
                if cached == cache_key:
                    return  # Already verified, all reqs have tests
            except ValueError:
                pass

    # Parse requirements and check coverage
    all_reqs = get_requirements(cwd)
    if not all_reqs:
        return  # No requirements to enforce

    test_files = find_test_files(cwd)
    covered_reqs = get_covered_reqs(test_files)

    missing = all_reqs - covered_reqs
    if missing:
        missing_sorted = sorted(missing)
        reason = (
            f"Write tests for {', '.join(missing_sorted)} before implementing. "
            f"Invoke the test-first skill."
        )
        print(json.dumps({
            "hookSpecificOutput": {
                "permissionDecision": "deny",
                "permissionDecisionReason": reason
            }
        }))
        return

    # All covered — cache result
    os.makedirs(FLAG_DIR, exist_ok=True)
    with open(fp, "w") as f:
        f.write(cache_key)


if __name__ == "__main__":
    main()
