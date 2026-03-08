#!/usr/bin/env python3
"""Shared constants and functions for test-first hook scripts."""

import glob
import os
import re

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs",
    ".java", ".html", ".css", ".scss", ".vue", ".svelte",
}

TEST_PATTERNS = [
    r"^test_",       # test_foo.py
    r"_test\.",       # foo_test.py, foo_test.go
    r"\.test\.",      # foo.test.js, foo.test.ts
    r"\.spec\.",      # foo.spec.js, foo.spec.ts
]


def is_code_file(file_path):
    """Check if file has a code extension."""
    _, ext = os.path.splitext(file_path)
    return ext.lower() in CODE_EXTENSIONS


def is_test_file(file_path):
    """Check if file matches test naming patterns."""
    basename = os.path.basename(file_path)
    return any(re.search(pat, basename) for pat in TEST_PATTERNS)


def get_requirements(cwd):
    """Parse requirements.yaml and return set of REQ-NNN IDs."""
    path = os.path.join(cwd, "requirements.yaml")
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        content = f.read()
    return set(re.findall(r"id:\s*(REQ-\d+)", content))


def find_test_files(cwd):
    """Find all test files in the project."""
    test_files = []
    for ext in CODE_EXTENSIONS:
        for path in glob.glob(os.path.join(cwd, "**", f"*{ext}"), recursive=True):
            if is_test_file(path):
                test_files.append(path)
    return test_files


def get_covered_reqs(test_files):
    """Scan test files for # REQ-NNN or // REQ-NNN annotations."""
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
