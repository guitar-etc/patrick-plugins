# UAT Generation System — Requirements (Batch 1)

## Overview

An automatic UAT generation system that produces tests from user-reviewed requirements. Follows strict TDD red-green: tests are generated before implementation and must fail first.

## Requirements

### Requirement Sources

- REQ-001: All user-reviewed requirements must have an automatic UAT.
- REQ-002: "User-reviewed" means the user explicitly read and reviewed the material. Approval alone does not count as reviewed — sometimes plans are approved without review (trusted).
- REQ-003: Only explicitly reviewed inputs become requirements. Approved-without-review items are logged in a separate `approveds.md` for reference but do not generate tests.
- REQ-004: User input includes both the raw User Prompt and the User Prompt Rephrase.

### Requirements Document

- REQ-005: The raw prompt and the rephrase must be written to the requirements document verbatim as the source.
- REQ-006: Each requirement entry must have the user input (prompt + rephrase) directly adjacent to it, not in a separate section.
- REQ-007: Requirements are stored in a structured manifest file (YAML/JSON).
- REQ-008: Requirements are labeled with auto-generated sequential IDs (REQ-001, REQ-002, ...).
- REQ-009: User inputs and reviews are documented and labeled.

### Test Generation

- REQ-010: Tests are generated continuously as requirements arrive (TDD red-green flow).
- REQ-011: Strict red-green: tests are generated BEFORE implementation. They must fail first (red), then pass after implementation (green).
- REQ-012: If a test can't fail meaningfully yet (e.g., no running app for Playwright), mark it as pending/skip until infrastructure exists. The test is still written first from the requirement.
- REQ-013: Each test must be commented or annotated with its requirement label (e.g., `# REQ-001`).
- REQ-014: Prefer deterministic test frameworks (pytest, Playwright) over instruction markdown for speed. Instruction markdown is a fallback for things hard to automate.
- REQ-015: Webapp functionality must be tested using browser automation (Playwright or agent browser).
- REQ-016: The automatic UAT may be pytest tests, instruction markdown for Claude to execute, or a mix — but deterministic framework is preferred.

## Requirement Entry Format

```yaml
requirements:
  - id: REQ-001
    prompt: "make the button bigger and change color"
    rephrase: "I want you to increase the size of the button and change its color in the UI."
    status: reviewed
    tests: [test_button_size, test_button_color]
```

## Lifecycle

```
User Prompt + Rephrase
        |
    Was it reviewed?
    |-- Yes --> requirements.yaml (REQ-NNN) --> generate failing test --> implement --> green
    |-- No  --> approveds.md (logged, no tests)
```

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| When to generate UATs | Continuously (TDD red-green) | Tests validate requirements before implementation |
| Requirement labeling | Auto-generated sequential IDs | Simple, unambiguous |
| Requirements storage | Structured manifest file | Traceability, machine-readable |
| TDD strictness | Strict red-green | Validates tests themselves; catches requirement drift |
| Approved-without-review | Separate approveds.md, no tests | Not a requirement; logged for reference only |
