---
name: test-first
description: Enforce TDD red-green workflow for requirements. Write failing tests before implementation code. Annotate tests with REQ-NNN comments for traceability. Triggered automatically via hooks.
user-invocable: false
---

# Test-First Enforcement

Write failing tests for every requirement in `requirements.yaml` before writing implementation code. Follow strict TDD red-green: test first (red), implement second (green). Annotate every test with its requirement ID.

## Test Annotation Format

Every test function or test block must include a comment linking it to one or more requirements:

```python
# REQ-001
def test_button_size():
    ...

# REQ-001
def test_button_color():
    ...

# REQ-002
def test_login_page_fields():
    ...
```

For JavaScript/TypeScript:
```typescript
// REQ-001
test('button should be larger', () => { ... });

// REQ-003
it('header stays fixed on scroll', () => { ... });
```

The annotation must appear on the line immediately before the test function definition or test block. Use `# REQ-NNN` for Python and `// REQ-NNN` for JS/TS.

Multiple requirements can share a test, and one requirement can have multiple tests. The annotation links them for traceability.

## Test Framework Selection

Choose the test framework based on what is being tested:

| What to test | Framework | When to use |
|---|---|---|
| Pure logic, utilities, data transforms | **pytest** | Default for Python projects |
| API endpoints, server behavior | **pytest** with HTTP client | Backend testing |
| Webapp UI, user interactions | **Playwright** | Browser-visible behavior |
| Complex workflows, multi-step processes | **Instruction markdown** | Fallback when automation is impractical |

**Framework priority**: pytest > Playwright > instruction markdown

Prefer deterministic frameworks (pytest, Playwright) over instruction markdown. Instruction markdown is a fallback for things that are genuinely hard to automate — not a default.

For JavaScript/TypeScript projects, use the project's existing test framework (Jest, Vitest, etc.) instead of pytest.

## Pending Tests

When a test cannot fail meaningfully yet — for example, a Playwright test when no webapp exists — write the test but mark it as pending:

**Python (pytest)**:
```python
import pytest

# REQ-003
@pytest.mark.skip(reason="Webapp not yet running — pending infrastructure")
def test_sticky_header():
    """Header should remain fixed at top when scrolling."""
    # TODO: Implement when webapp is available
    pass
```

**JavaScript (Jest/Vitest)**:
```typescript
// REQ-003
it.skip('header stays fixed on scroll', () => {
  // TODO: Implement when webapp is available
});
```

The test is still written from the requirement. It serves as documentation and will be unskipped when infrastructure exists. The `# REQ-NNN` annotation is still required.

## The Red-Green Cycle

For each requirement in `requirements.yaml`:

1. **Red**: Write a test that expresses the requirement. Run it — it must fail (or be pending/skipped if infrastructure doesn't exist yet).
2. **Green**: Write the minimum implementation to make the test pass.
3. **Refactor**: Clean up the implementation while keeping the test green.

Do not skip step 1. Do not write implementation code for a requirement before writing its test. The verification hook enforces this — it will block Write/Edit on code files if any requirement lacks a test.

When writing tests for multiple requirements at once, write all tests first, then implement. Do not interleave test-implement-test-implement.

## Output Format

After writing or modifying any test file, output a "Test Update: " paragraph as a separate line:

**When tests were added or modified:**
```
Test Update: REQ-003 test added (test_sticky_header), REQ-001 test modified (test_button_size)
```

**When no test changes were made:**
```
Test Update: None
```

Format each change as: `REQ-NNN test action (test_function_name)`

Actions: `added`, `modified`, `removed`

This output is informational — unlike "Requirements Update: ", it is not gated by a transcript-check hook. However, it maintains consistency with the requirements-capture plugin's pattern and helps the user track test coverage.
