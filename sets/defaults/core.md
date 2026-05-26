# Agent Instructions

These instructions describe how AI coding agents should work in this repository.

## Clarify Before Acting
- Ask questions when the request, current behavior, or desired behavior is unclear.
- State assumptions before implementation.
- If a simpler approach exists, mention it before choosing a larger one.

## Planning First
- Do not implement code changes until the user explicitly asks with words like "implement", "build it", "go ahead", or similar.
- When the user asks a question, answer the question only. Do not make code changes unless explicitly asked.
- For multi-step work, give a short plan with verification steps before editing.

## Simplicity
- Make the smallest change that solves the stated problem.
- Do not add speculative features, unused abstractions, or configurability that was not requested.
- Keep every changed line traceable to the user request.

## Surgical Changes
- Touch only the files needed for the task.
- Match the existing style even if you would normally write it differently.
- Do not refactor adjacent code or delete unrelated dead code unless asked.
- Preserve user changes and never revert work you did not make without explicit approval.

## Code Safety
- Fix root causes. Do not hide errors with broad try/catch, sleeps, ignored type errors, or placeholder returns.
- Do not submit TODO, FIXME, placeholder comments, mock implementations, or incomplete code unless the user explicitly asks for a draft.
- Before creating a new helper, schema, builder, or utility, search for an existing implementation and reuse it when appropriate.

## Verification
- Define success criteria before changing code.
- Run the smallest relevant validation command after changes.
- If validation cannot be run, explain why and describe the remaining risk.
