# rephrase-prompt

LLMs often misinterpret natural language — a vague "fix that" or "add tests for it" can send Claude down the wrong path, wasting time and context window. This plugin forces Claude to prove it understood you before it does anything.

Every response starts with a `Rephrase:` line — Claude's interpretation of what you asked, written in plain language. If the rephrase is wrong, you correct it. If it's right, Claude proceeds. No more guessing whether the LLM got it.

## How it works

On every message you send, Claude prepends a rephrase showing how it understood your request:

```
Rephrase: I want you to refactor the auth module and add unit tests for JWT validation.

[Claude's actual response]
```

The rephrase is self-contained — it weaves in conversation context so it makes sense even if copied to a new session.

### Five-hook enforcement

| Hook | Purpose |
|---|---|
| **UserPromptSubmit** | Reminds Claude to rephrase on every prompt |
| **PreToolUse** | Blocks tool calls if Claude forgot to rephrase |
| **PostToolUse** | Re-triggers rephrase after `AskUserQuestion` or `EnterPlanMode` |
| **PostToolUseFailure** | Re-triggers rephrase after rejected `ExitPlanMode` |
| **PreCompact** | Preserves rephrase paragraphs during context compaction |

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
