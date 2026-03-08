#!/usr/bin/env python3
"""Stop hook: verify all requirements in requirements.yaml have test annotations.
Blocks session stop if any requirement lacks coverage."""

import json
import os
import re
import sys

# Add script directory to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_test_first import find_test_files, get_covered_reqs


def main():
    hook_input = json.loads(sys.stdin.read())
    cwd = hook_input.get("cwd", os.getcwd())

    req_path = os.path.join(cwd, "requirements.yaml")
    if not os.path.exists(req_path):
        return  # No requirements — nothing to check

    with open(req_path) as f:
        content = f.read()

    all_reqs = set(re.findall(r"id:\s*(REQ-\d+)", content))
    if not all_reqs:
        return

    test_files = find_test_files(cwd)
    covered_reqs = get_covered_reqs(test_files)

    missing = all_reqs - covered_reqs
    if missing:
        missing_sorted = sorted(missing)
        total = len(all_reqs)
        covered_count = total - len(missing)
        reason = (
            f"Coverage: {covered_count}/{total} requirements have tests. "
            f"Missing: {', '.join(missing_sorted)}"
        )
        print(json.dumps({
            "decision": "block",
            "reason": reason
        }))
    # If all covered, output nothing (allow)


if __name__ == "__main__":
    main()
