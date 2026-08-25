# 🤖 Aegis 2.0 — Multi-Agent Deep Dive & Prompt Workflow

This document explains the inner mechanics of the 4 Aegis AI agents: their prompts, system instructions, error recovery loops, and output validation schemas.

---

## 🔍 Agent 1: Finder Agent

### File Location: `backend/app/agents/finder.py`
### Model: Groq `openai/gpt-oss-120b` (or `llama-3.3-70b-versatile`)
### Role: Triage, Context Fusion & Vulnerability Verification

#### How it works:
1. Receives raw Semgrep rule matches and AST structural outlines.
2. Cross-references whether user input reaches the sink (e.g. database query, system command) or if it was already sanitized upstream.
3. Formulates a structured JSON array.

#### System Prompt Excerpt:
```text
You are the Aegis Lead Security Finder Agent.
Your job is to analyze potential security vulnerabilities discovered in a target codebase and cross-reference them with the full repository architecture.

For each finding:
1. Validate whether it represents a real, exploitable flaw or a false positive based on the surrounding context.
2. Determine exact vulnerability type (SQL Injection, Remote Code Execution, SSRF, Broken Access Control, Path Traversal).
3. Assign strict CVSS v3.1 Severity: CRITICAL, HIGH, MEDIUM, or LOW.
4. Explain the attack vector clearly and concisely.
```

---

## 🛠️ Agent 2: Engineer Agent

### File Location: `backend/app/agents/engineer.py`
### Model: Groq `openai/gpt-oss-120b`
### Role: Minimal Surgical Patch Synthesis & Regression Testing

#### How it works:
1. Takes the exact file content, line number, finding description, and any developer-injected context.
2. Identifies the vulnerable AST node.
3. Rewrites *only* the necessary lines to fix the flaw without breaking business logic.
4. Generates a unified git diff and companion pytest test case.

#### Output Contract:
```json
{
  "patched_file_content": "complete updated file content with patch applied",
  "explanation": "Replaced direct f-string SQL query with parameterized tuple input.",
  "regression_test_code": "def test_sqli_neutralized(): ..."
}
```

---

## 🛡️ Agent 3: Reviewer Agent

### File Location: `backend/app/agents/reviewer.py`
### Model: Groq `openai/gpt-oss-120b`
### Role: AST Syntax Verification & Safety Assurance

#### How it works:
1. Runs `ast.parse()` on the generated code. If a syntax error exists, rejects immediately with exact line numbers.
2. Analyzes the diff to confirm no regressions, credential leaks, or secondary vulnerabilities were introduced.
3. Emits `is_safe: true/false`.

---

## 🚀 Agent 4: PR Creator Agent

### File Location: `backend/app/agents/pr_creator.py`
### Framework: PyGithub REST Client + GitHub App Installation Token
### Role: Branching, Committing & Pull Request Publishing

#### How it works:
1. Checks the default branch of the repository (e.g. `main` or `master`).
2. Creates a unique Git branch: `refs/heads/aegis/fix-<type>-<timestamp>`.
3. Creates or updates the modified file with a descriptive commit message:
   `fix(security): sanitize vulnerability in <file> via Aegis`
4. Opens the GitHub Pull Request with clear vulnerability diagnosis, patch diff, and verification checkboxes.
