#!/usr/bin/env python3
"""PostToolUse hook: remind Claude to invoke the test-first skill
when requirements.yaml was modified."""

import json
import sys


def main():
    hook_input = json.loads(sys.stdin.read())

    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # Only remind when requirements.yaml was the modified file
    if file_path.endswith("requirements.yaml"):
        print("Invoke the test-first skill.")


if __name__ == "__main__":
    main()
