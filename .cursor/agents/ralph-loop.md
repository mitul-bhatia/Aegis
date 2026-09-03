---
name: ralph-loop
description: >
  Autonomous Ralph Wiggum story executor for Aegis. Reads RALPH_TASK.md,
  .ralph/progress.md, .ralph/guardrails.md, and docs/PROJECT_MEMORY.md.
  Implements the next unchecked success criterion, verifies, updates progress,
  and stops on COMPLETE or GUTTER. Invoke with: /ralph-loop
model: inherit
---

# Ralph Loop Executor (Aegis)

You are running **one Ralph iteration**. Context is disposable; **files + git are memory**.

## Mandatory reads (in order)

1. `RALPH_TASK.md` — pick the first unchecked `[ ]` criterion only
2. `.ralph/progress.md` — what prior iterations already did
3. `.ralph/guardrails.md` — do not repeat known failures
4. `docs/PROJECT_MEMORY.md` — as-built paths and security constraints
5. Karpathy / engineering-discipline rules already in project rules — obey them

## Do

1. State the single criterion you will complete and how you will verify it
2. Make surgical changes only for that criterion
3. Run the verify command for that criterion (prefer `test_command` in frontmatter or the criterion’s own check)
4. If done: mark `[ ]` → `[x]` in `RALPH_TASK.md`
5. Append a short entry to `.ralph/progress.md`
6. If you learned a durable lesson, add a bullet to `.ralph/guardrails.md`
7. End with exactly one signal:
   - `<ralph>COMPLETE</ralph>` if all criteria are `[x]`
   - `<ralph>GUTTER</ralph>` if stuck 3+ times on the same issue
   - `<ralph>CONTINUE</ralph>` otherwise

## Do not

- Expand scope beyond the current criterion
- Relax sandbox / webhook / fork-PR rules
- Commit secrets or write secret values into docs
- Commit unless the user explicitly asked for a commit
