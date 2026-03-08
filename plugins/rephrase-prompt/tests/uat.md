# Rephrase Plugin — Interactive UAT

You are testing the `rephrase-prompt@patrick-plugins` plugin. Execute each scenario below one at a time. For each scenario:

1. Read the scenario
2. Perform the action described
3. Observe the result
4. Judge pass/fail against the criteria
5. Record the result in a summary table at the end

If a scenario requires user interaction (e.g., answering a question, rejecting a plan), tell the user what to do and wait for their response before judging.

---

## Scenario 1: Basic Rephrase

Ask the user: "Send me a prompt so I can test if rephrase works. Type anything — e.g., `list files in src/`"

After the user responds, check your own response:
- Does it start with `Rephrase: ` as a separate paragraph?
- Does the rephrase use "I" for the user and "You" for Claude?
- Is the rephrase separate from the main response body?

---

## Scenario 2: Context Weaving

This continues from Scenario 1. Ask the user: "Now send a follow-up prompt that references the previous task — e.g., `also add tests for that`"

After the user responds, check:
- Does the rephrase incorporate context from Scenario 1 (not just the literal follow-up words)?
- Would the rephrase make sense if copied to a brand new session?

---

## Scenario 3: No Self-Rephrase

Perform a multi-step task yourself: read 2-3 files, then summarize findings. Check:
- Is there exactly ONE `Rephrase: ` at the very top?
- Are your intermediate outputs (file contents, analysis) free of `Rephrase: ` prefixes?

---

## Scenario 4: Subagent Bypass

Spawn a subagent (e.g., Explore agent to search for something). Check:
- Did YOUR response (the main agent) include `Rephrase: `?
- Did the subagent operate without being blocked by the rephrase verification hook?

---

## Scenario 5: Flag Caching

After completing Scenario 3 or 4 (which involved multiple tool calls), run:
```bash
ls /tmp/claude-rephrase/
```
And read the flag file contents. Check:
- Does a flag file exist for the current session?
- Does the file contain a number (the last user message index)?

---

## Scenario 6: AskUserQuestion Reminder

Ask the user a clarifying question using AskUserQuestion (e.g., ask about a preference). After the user answers, check:
- Does your response to their answer include a fresh `Rephrase: `?

---

## Scenario 7: Trivial Prompt

Ask the user: "Send a one-word reply like `yes` or `ok`"

After the user responds, check:
- Is `Rephrase: ` still present?
- Does the rephrase explain what the one-word reply means in context?

---

## Scenario 8: Non-English Prompt

Ask the user: "Send a prompt in any non-English language — e.g., `파일 목록 보여줘`"

After the user responds, check:
- Is the rephrase in English?
- Does it accurately capture the intent of the non-English prompt?

---

## Scenario 9: Plugin Isolation

Run these checks:
```bash
python3 -c "
import json
with open('/home/patrick/.claude/settings.json') as f:
    data = json.load(f)
hooks_str = json.dumps(data.get('hooks', {}))
issues = []
if 'verify-rephrase' in hooks_str:
    issues.append('verify-rephrase script found in settings hooks')
if 'Invoke /rephrase' in hooks_str:
    issues.append('Invoke /rephrase echo found in settings hooks')
if issues:
    print('FAIL:', '; '.join(issues))
else:
    print('PASS: No rephrase hooks leaked into settings.json')
"
```

Also verify old files are gone:
```bash
test -d ~/.claude/skills/rephrase && echo "FAIL: old skill dir exists" || echo "PASS: old skill dir removed"
test -f ~/.claude/hooks/verify-rephrase.py && echo "FAIL: old hook script exists" || echo "PASS: old hook script removed"
```

---

## Scenario 10: Plugin Files Intact

Verify the plugin's own files are all present and valid:
```bash
python3 -c "
import json, os, sys
root = '/home/patrick/.claude/plugins/cache/patrick-plugins/rephrase-prompt/0.1.0'
checks = [
    ('.claude-plugin/plugin.json', True),
    ('hooks/hooks.json', True),
    ('hooks/scripts/verify-rephrase.py', True),
    ('skills/rephrase/SKILL.md', True),
]
all_pass = True
for rel, required in checks:
    path = os.path.join(root, rel)
    exists = os.path.exists(path)
    status = 'PASS' if exists == required else 'FAIL'
    if status == 'FAIL': all_pass = False
    print(f'{status}: {rel} ({\"exists\" if exists else \"missing\"})')

# Validate JSON files
for jf in ['hooks/hooks.json', '.claude-plugin/plugin.json']:
    try:
        with open(os.path.join(root, jf)) as f:
            json.load(f)
        print(f'PASS: {jf} is valid JSON')
    except Exception as e:
        print(f'FAIL: {jf} invalid JSON: {e}')
        all_pass = False

# Check verify script is executable
import stat
vp = os.path.join(root, 'hooks/scripts/verify-rephrase.py')
mode = os.stat(vp).st_mode
if mode & stat.S_IXUSR:
    print('PASS: verify-rephrase.py is executable')
else:
    print('FAIL: verify-rephrase.py is not executable')
    all_pass = False

print()
print('OVERALL:', 'ALL PASS' if all_pass else 'HAS FAILURES')
"
```

---

## After All Scenarios

Print a summary table:

```
| #  | Scenario              | Result |
|----|-----------------------|--------|
| 1  | Basic Rephrase        | ?      |
| 2  | Context Weaving       | ?      |
| 3  | No Self-Rephrase      | ?      |
| 4  | Subagent Bypass       | ?      |
| 5  | Flag Caching          | ?      |
| 6  | AskUserQuestion       | ?      |
| 7  | Trivial Prompt        | ?      |
| 8  | Non-English Prompt    | ?      |
| 9  | Plugin Isolation      | ?      |
| 10 | Plugin Files Intact   | ?      |
```

Replace `?` with PASS or FAIL. If any scenario failed, explain what went wrong.
