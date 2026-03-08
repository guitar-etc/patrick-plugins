---
name: rephrase
description: Rephrase user prompts into clear instructions to reduce misunderstandings. Shows how Claude interpreted the request. Use on every user prompt — triggered automatically via UserPromptSubmit hook.
user-invocable: false
---

# Rephrase User Prompt

Before responding to any user message, rephrase their prompt to demonstrate your understanding. This reduces misunderstandings from natural language and gives the user a chance to correct your interpretation before you act.

## Format

Prepend a "Rephrase: " line as a separate paragraph before your main response:

```
Rephrase: [Your rephrased understanding here]

[Your main response]
```

## Rules

1. Use "I" to refer to the user and "You" to refer to Claude
2. Only rephrase the **user's prompt** — never prefix your own analysis, findings, or status updates with "Rephrase: "
3. Write the rephrase as self-contained — it should make sense if copied to a new session without any prior conversation
4. The rephrase serves as both a comprehension check and a running summary of the conversation
5. Capture the user's intent and desired outcome, not just their literal words
6. If the conversation has prior context, weave it into the rephrase so it stands alone
7. Keep it concise but complete

## Example

User says: "make the button bigger and change color"

```
Rephrase: I want you to increase the size of the button and change its color in the UI.
```

User says (mid-conversation about auth refactor): "also add tests for that"

```
Rephrase: I'm working on refactoring the authentication module. I want you to add tests for the auth changes we just discussed — specifically for the JWT token validation and session management.
```

Notice how the second example incorporates conversation context so it stands alone.
