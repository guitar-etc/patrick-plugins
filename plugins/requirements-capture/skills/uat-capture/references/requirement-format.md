# Requirement Format Reference

## YAML Schema — `requirements.yaml`

The requirements manifest uses the following structure:

```yaml
requirements:
  - id: REQ-001
    prompt: "the verbatim user prompt text"
    rephrase: "the verbatim rephrase text"
    status: reviewed
    tests: []

  - id: REQ-002
    prompt: "another user prompt"
    rephrase: "another rephrase"
    status: test-written
    tests: [test_feature_name]
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Sequential ID in format `REQ-NNN` (zero-padded to 3 digits) |
| `prompt` | string | yes | Verbatim user prompt text, exactly as typed |
| `rephrase` | string | yes | Verbatim rephrase text from the "Rephrase: " paragraph |
| `status` | string | yes | Current status (see Status Values below) |
| `tests` | list | no | Test function names covering this requirement |

### ID Format

- Pattern: `REQ-` followed by a zero-padded 3-digit number
- Sequential: IDs are assigned in order and never reused
- Examples: `REQ-001`, `REQ-002`, `REQ-042`
- After deletion, the next ID continues from the highest ever assigned

### Status Values

| Status | Meaning |
|--------|---------|
| `reviewed` | User reviewed and requirement captured; no test yet |
| `test-written` | A failing test has been written for this requirement |
| `implemented` | Implementation complete and test passes |

Status progresses: `reviewed` → `test-written` → `implemented`

## Example Entries

### Single Requirement

```yaml
requirements:
  - id: REQ-001
    prompt: "make the button bigger and change color"
    rephrase: "I want you to increase the size of the button and change its color in the UI."
    status: reviewed
    tests: []
```

### Multiple Requirements with Tests

```yaml
requirements:
  - id: REQ-001
    prompt: "make the button bigger and change color"
    rephrase: "I want you to increase the size of the button and change its color in the UI."
    status: test-written
    tests: [test_button_size, test_button_color]

  - id: REQ-002
    prompt: "add login page with email and password"
    rephrase: "I want you to create a login page with email and password fields."
    status: reviewed
    tests: []

  - id: REQ-003
    prompt: "the header should be fixed when scrolling"
    rephrase: "I want the page header to remain fixed at the top of the viewport when the user scrolls down."
    status: implemented
    tests: [test_sticky_header]
```

## Invocation Log Format — `requirements-log.jsonl`

Each line is a JSON object with the following fields:

```json
{"id": "inv-001", "timestamp": "2026-03-09T14:30:00+09:00", "action": "add", "reqs": ["REQ-001"]}
{"id": "inv-002", "timestamp": "2026-03-09T14:35:00+09:00", "action": "none", "reqs": []}
{"id": "inv-003", "timestamp": "2026-03-09T14:40:00+09:00", "action": "modify", "reqs": ["REQ-001"]}
```

### Log Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Sequential invocation ID: `inv-NNN` |
| `timestamp` | string | ISO 8601 with KST timezone (`+09:00`) |
| `action` | string | One of: `add`, `modify`, `delete`, `none` |
| `reqs` | array | REQ-NNN IDs affected (empty for `none`) |

### Log ID Assignment

- Start at `inv-001` if log file doesn't exist
- Read the last line to determine the next ID
- Increment sequentially: `inv-001`, `inv-002`, `inv-003`, ...

## Approved-Without-Review Format — `approveds.md`

Plans approved without detailed user review are logged here:

```markdown
## Approved Without Review

- **Date**: 2026-03-09 KST
- **Context**: Refactoring the authentication module
- **Reason**: Approved without detailed review

---

- **Date**: 2026-03-09 KST
- **Context**: Database migration plan
- **Reason**: Approved without detailed review
```

Each entry is appended with a `---` separator between entries. This file is append-only — never delete existing entries.
