# Create harness-dev meta-skill plugin

## Context

Claude frequently forgets rules from CLAUDE.md as context grows. The rephrase-prompt plugin solved this for one specific rule using a 5-layer enforcement pattern. This pattern is proven and generalizable but undocumented — building a new enforcement rule requires reverse-engineering the rephrase plugin.

The harness-dev plugin is a **meta-skill** that teaches Claude how to design and build rule-enforcement systems. It extracts the pattern from the rephrase implementation into teachable, reusable knowledge.

## Plugin structure

```
~/.claude/plugins/marketplaces/patrick-plugins/plugins/harness-dev/
├── .claude-plugin/
│   └── plugin.json
└── skills/
    └── harness-dev/
        ├── SKILL.md
        └── references/
            ├── enforcement-layers.md
            └── rephrase-case-study.md
```

## Files to create (4 files)

### 1. `.claude-plugin/plugin.json`

```json
{
  "name": "harness-dev",
  "version": "0.1.0",
  "description": "Meta-skill for building rule-enforcement systems in Claude Code",
  "author": { "name": "Patrick" },
  "keywords": ["harness", "rule-enforcement", "meta-skill", "compliance", "hooks"]
}
```

### 2. `skills/harness-dev/SKILL.md` (~1,800 words)

**Frontmatter:**
```yaml
name: harness-dev
description: >
  This skill should be used when the user asks to "create a rule",
  "enforce a rule", "add enforcement", "build a harness",
  "make Claude follow a rule", "rule enforcement", "compliance hook",
  "verification hook", "Claude keeps forgetting", "Claude ignores my rule",
  or wants to ensure Claude reliably follows a specific behavior.
  Teaches the 5-layer enforcement pattern for building rule-enforcement
  plugins in Claude Code.
```

**Body sections (~1,800 words, imperative form):**
1. **Overview** — The problem (Claude forgets rules as context grows) and the solution (3-layer enforcement: Skill, Reminder, Verification)
2. **The 3 Layers** — Summary table:
   - **Skill** — The rule definition itself (SKILL.md). Foundation layer: what the rule is, why it matters, how to follow it. Reminders just point back here.
   - **Reminder** — Any mechanism that nudges Claude to follow the rule: CLAUDE.md entries, hook echoes on any event (UserPromptSubmit, PostToolUse, PostToolUseFailure, etc.). Multiple reminders can target different moments (prompt submission, after user-input tools like AskUserQuestion, after plan transitions).
   - **Verification** — Any hook that checks compliance and blocks if not met. Can use any hook event (PreToolUse, Stop, PostToolUse, etc.) — whichever fires soonest after the rule should have been followed.
3. **Minimum viable enforcement** — Verification alone is the minimum. A PreToolUse deny hook can enforce a rule without a skill or reminder. But adding Skill + Reminders improves compliance rate and reduces wasted tool-call denials.
4. **Design Workflow** — 6-step process:
   - Define the rule (what, when, how to detect compliance)
   - Decide which layers are needed (verification minimum; add skill + reminders for efficiency)
   - Create plugin structure
   - Implement each layer
   - Test with `claude --debug`
   - Iterate based on compliance rate
5. **Verification Strategies** — Three patterns: transcript-check (scan assistant text for marker), output-check (validate tool output), file-check (verify file state)
6. **Flag Caching Pattern** — Cache verified state in `/tmp/` keyed by `(session_id, last_user_idx)` to avoid re-parsing on every tool call
7. **Optional: Preservation** — PreCompact hook to instruct compact subagent to preserve rule-related content. Rare; only needed for rules producing artifacts that must survive compaction.
8. **Best Practices** — DO/DON'T list
9. **Reference Files** — Pointers to `references/enforcement-layers.md` and `references/rephrase-case-study.md`

### 3. `references/enforcement-layers.md` (~2,500 words)

Deep implementation guide for each layer with generic templates and examples:

- **Layer 1: Skill** — How to write a rule-definition skill: SKILL.md structure, `user-invocable: false`, defining the rule clearly with format/examples so Claude knows what compliance looks like. Template SKILL.md included.
- **Layer 2: Reminder** — All reminder mechanisms available:
  - CLAUDE.md entries (always in context, cheapest)
  - SessionStart hook (once per session)
  - UserPromptSubmit hook (on every user message)
  - PostToolUse hooks with matchers for user-input tools (AskUserQuestion, EnterPlanMode, etc.) — catch moments where user provides new input
  - PostToolUseFailure hooks (e.g., after ExitPlanMode rejection)
  - How to choose which reminders to use and combine them
- **Layer 3: Verification** — How to build compliance-checking hooks:
  - Choose the right hook event (PreToolUse fires before every tool — catches non-compliance earliest; Stop fires before session ends; PostToolUse fires after specific tools)
  - Script template: stdin JSON parsing, transcript JSONL reading, deny/allow JSON output
  - Flag caching pattern for performance
  - Subagent bypass (`agent_id` check)
  - Verification strategies: transcript-check, output-check, file-check
- **Optional: Preservation** — PreCompact echo for long sessions where rule artifacts must survive compaction. Include when to use and when to skip.

Each layer section includes: purpose, implementation template, customization points, and decision criteria for when to include.

### 4. `references/rephrase-case-study.md` (~1,500 words)

Annotated walkthrough of the rephrase-prompt plugin:

- Maps each file to its enforcement layer
- Explains key design decisions: why flag caching, why subagent bypass, why those specific PostToolUse matchers
- Shows the complete hooks.json with annotations
- Shows the verify script structure with annotations
- "How to adapt" section: what to change for a different rule (marker string, skill content, matchers, compaction message)
- File paths pointing to actual rephrase-prompt plugin files for reference

## Post-creation steps

1. Copy to cache: `~/.claude/plugins/cache/patrick-plugins/harness-dev/0.1.0/`
2. Register in `~/.claude/plugins/installed_plugins.json` (user scope)
3. Enable in `~/.claude/settings.json` enabledPlugins
4. Git commit + push to GitHub

## Verification

- Trigger phrases: "how do I enforce a rule", "Claude keeps forgetting X", "create an enforcement system"
- Check SKILL.md loads with pattern overview + workflow
- Check references load on demand with detailed templates
- Run skill-reviewer agent for quality check
