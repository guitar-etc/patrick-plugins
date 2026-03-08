---
name: uat-capture
description: Capture and track user-reviewed requirements for TDD traceability. Evaluates every user message for requirement changes and maintains requirements.yaml. Triggered automatically via hooks.
user-invocable: false
---

# Capture User-Reviewed Requirements

Evaluate every user message for requirement changes. Maintain a `requirements.yaml` manifest that tracks all user-reviewed requirements with their original prompts and rephrases. Always output a "Requirements Update: " paragraph summarizing what changed.

## When Changes Apply

Evaluate the user's message against these criteria:

**Capture as requirement** when the user:
- Requests a new feature or behavior ("add a login button", "make it responsive")
- Reports a bug that implies expected behavior ("the button should be blue but it's red")
- Modifies an existing requirement ("change the button color from blue to red")
- Explicitly deletes or removes a requirement ("remove the login button requirement")

**Skip capture** (output "Requirements Update: None") when the user:
- Asks exploratory questions ("how does the auth module work?")
- Requests debugging without specifying new behavior ("why is this failing?")
- Provides conversational responses ("yes", "looks good", "thanks")
- Gives implementation guidance without new requirements ("use React for this")
- Reviews or approves plans without adding new requirements

When in doubt, lean toward capturing. A requirement can always be removed later, but a missed requirement breaks traceability.

## Capture Workflow

Follow these steps for every user message:

1. Read `requirements.yaml` in the current working directory. If the file does not exist, start with an empty requirements list.
2. Determine the next sequential ID. If requirements exist, increment from the highest REQ-NNN. If none exist, start with REQ-001.
3. For each new requirement identified:
   - Extract the verbatim user prompt (the raw text the user typed)
   - Extract the verbatim rephrase (from the "Rephrase: " paragraph you produced)
   - Assign the next sequential REQ-NNN ID
   - Set status to `reviewed`
4. Write the updated `requirements.yaml` file with all entries.

A single user message may introduce multiple requirements. Capture each as a separate entry.

## Modification and Deletion

**Modifying a requirement**: When the user changes an existing requirement, update the matching REQ-NNN entry in `requirements.yaml`. Preserve the original ID. Update the `prompt` and `rephrase` fields with the new text. If the requirement already had tests, keep the `tests` field but note the requirement changed — tests may need updating.

**Deleting a requirement**: When the user explicitly removes a requirement, delete the entire entry from `requirements.yaml`. Do not reuse the ID — the next new requirement still gets the next sequential number.

## Plan-to-Requirements

When the user triggers requirement capture after reviewing a plan (via the ExitPlanMode reminder):

1. Read the approved plan content
2. Parse individual deliverables, features, or behaviors from the plan
3. Create one REQ-NNN entry per distinct requirement
4. Set prompt to the user's original request that led to the plan
5. Set rephrase to the specific plan item being captured
6. Write all entries to `requirements.yaml`

Do not automatically capture plan requirements — only capture when the user explicitly triggers it (e.g., by saying `/uat-capture` after plan approval).

## Approved-Without-Review

Some plans are approved without the user reading them in detail (trusted approval). These do not become requirements.

When a plan is approved without explicit review, log it to `approveds.md` in the current working directory:

```markdown
## Approved Without Review

- **Date**: 2026-03-09 KST
- **Context**: [Brief description of the plan]
- **Reason**: Approved without detailed review
```

Append each new entry. Do not overwrite previous entries.

## Output Format

After processing every user message, output a "Requirements Update: " paragraph as a separate line. This is mandatory — the verification hook checks for it.

**When requirements changed:**
```
Requirements Update: REQ-003 added (Add login button to header), REQ-001 modified (Changed button color from blue to red)
```

**When requirements were deleted:**
```
Requirements Update: REQ-002 deleted (Remove responsive layout requirement)
```

**When no changes apply:**
```
Requirements Update: None
```

Format each change as: `REQ-NNN action (brief description)`

Actions: `added`, `modified`, `deleted`

Place the "Requirements Update: " paragraph early in your response, before any code or detailed analysis. The verification hook looks for this in the first assistant message after each user prompt.

## Invocation Logging

Log every invocation to `requirements-log.jsonl` in the current working directory. Each line is a JSON object:

```json
{"id": "inv-001", "timestamp": "2026-03-09T14:30:00+09:00", "action": "add", "reqs": ["REQ-003"]}
{"id": "inv-002", "timestamp": "2026-03-09T14:35:00+09:00", "action": "none", "reqs": []}
{"id": "inv-003", "timestamp": "2026-03-09T14:40:00+09:00", "action": "modify", "reqs": ["REQ-001"]}
{"id": "inv-004", "timestamp": "2026-03-09T14:45:00+09:00", "action": "delete", "reqs": ["REQ-002"]}
```

Fields:
- `id`: Sequential invocation ID (`inv-NNN`), incrementing from the last entry in the log
- `timestamp`: ISO 8601 with KST timezone offset
- `action`: One of `add`, `modify`, `delete`, `none`
- `reqs`: Array of REQ-NNN IDs affected (empty array for `none`)

If multiple actions occur in one invocation (e.g., add and modify), use the most significant action: `add` > `modify` > `delete` > `none`.

## Reference

See `references/requirement-format.md` for the full YAML schema, example entries, status values, and log format details.
