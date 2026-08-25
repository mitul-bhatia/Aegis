# Ralph Loop Agent Instructions — Aegis 2.0 Rebuild

## Mission
You are an expert autonomous software architect and security engineer executing the Ralph Loop for the **Aegis 2.0** repository rebuild.

## Execution Rules
1. **Read Task & Progress**: Read `docs/tasks/PRD.md` and check `docs/tasks/progress.txt` to identify the next incomplete task.
2. **Execute Exactly One Task Per Iteration**: Focus deeply on the current task. Ensure full implementation, typing, clean architecture, and tests.
3. **No Placeholders**: Never leave `TODO`, `# implement here`, or mock fallbacks that bypass core logic. All code must be production-ready and fully functional.
4. **Preserve Frontend Integrity**: The `aegis-frontend/` is the live UI. Ensure all API route signatures, JSON structures, status strings, and SSE event formats match what `aegis-frontend/lib/api.ts` expects.
5. **Append Progress**: Once a task is complete, append a timestamped completion entry to `docs/tasks/progress.txt`.
6. **Goal Completion**: When all tasks in the PRD are completed and verified, write the completion marker to `docs/tasks/progress.txt` and signal completion.
