# rephrase-prompt

A Claude Code plugin that rephrases every user prompt before responding. This reduces misunderstandings from ambiguous natural language and gives you a chance to correct Claude's interpretation before it acts.

## How it works

Every time you send a message, Claude prepends a `Rephrase:` line showing how it understood your request:

```
Rephrase: I want you to refactor the auth module and add unit tests for JWT validation.

[Claude's actual response]
```

The rephrase is self-contained — it weaves in conversation context so it makes sense even if copied to a new session.

### Three-layer enforcement

1. **UserPromptSubmit hook** — reminds Claude to rephrase on every prompt
2. **PreToolUse verification** — blocks tool calls if Claude forgot to rephrase
3. **PreCompact hook** — preserves rephrases during context compaction

## Install

```bash
/plugin marketplace add guitar-etc/patrick-plugins
/plugin install rephrase-prompt@patrick-plugins
```

## Example

User says: "also add tests for that"

Mid-conversation about an auth refactor, Claude responds:

```
Rephrase: I'm working on refactoring the authentication module.
I want you to add tests for the auth changes we just discussed
— specifically for the JWT token validation and session management.
```

The rephrase captures intent and context, not just the literal words.
