#!/usr/bin/env python3
"""Stop hook: verify all requirements in requirements.yaml have test annotations.
Blocks session stop if any requirement lacks coverage."""

import glob
import json
import os
import re
import sys

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs",
    ".java", ".html", ".css", ".scss", ".vue", ".svelte",
}

TEST_PATTERNS = [
    r"^test_",
    r"_test\.",
    r"\.test\.",
    r"\.spec\.",
]


def is_test_file(file_path):
    basename = os.path.basename(file_path)
    return any(re.search(pat, basename) for pat in TEST_PATTERNS)


def find_test_files(cwd):
    test_files = []
    for ext in CODE_EXTENSIONS:
        for path in glob.glob(os.path.join(cwd, "**", f"*{ext}"), recursive=True):
            if is_test_file(path):
                test_files.append(path)
    return test_files


def get_covered_reqs(test_files):
    covered = set()
    pattern = re.compile(r"[#/]+\s*REQ-\d+")
    for path in test_files:
        try:
            with open(path) as f:
                for line in f:
                    if pattern.search(line):
                        covered.update(re.findall(r"REQ-\d+", line))
        except (OSError, UnicodeDecodeError):
            continue
    return covered


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
