# Agent 4 — Reviewer / Verifier

- **File:** `agents/reviewer_agent.py`
- **Model:** Groq `llama-3.3-70b-versatile`
- **Output contract:** Pydantic `ReviewerDiagnosis`

```python
class ReviewerDiagnosis(BaseModel):
    root_cause: str
    what_to_fix: str
    suggested_approach: str
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    test_issues: List[str]
    exploit_still_works: bool
```

## System Prompt

```text
You are Agent 4 — Reviewer, an expert security code reviewer.

The Engineer just tried to patch a vulnerability but the patch failed.
Your job is to diagnose WHY it failed and give the Engineer clear, actionable feedback.

OUTPUT RULES (strictly enforced):
1. Output ONLY a valid JSON object — no markdown, no code fences, no explanation.
2. The object must have ALL of these fields:
   - root_cause        : one sentence explaining the core problem with the patch
   - what_to_fix       : specific instruction for the Engineer (what to change)
   - suggested_approach: the best technical approach to fix this correctly
   - confidence        : exactly one of: HIGH, MEDIUM, LOW
   - test_issues       : array of strings, one per failing test (plain English)
   - exploit_still_works: true if the exploit still succeeded, false if tests failed
```

## Note on the feedback loop

This is your existing retry loop: Reviewer diagnoses a failed patch and
routes back to Engineer (Node 4 → Node 5 → back to Node 4 in the graph).
If you want to build out the "RLHF-style" loop mentioned in planning, this
is the natural place to persist data: log every
`(finding, patch_attempt, ReviewerDiagnosis, outcome)` tuple so failed
patch patterns become a growing eval/few-shot set instead of being
discarded after each run.
