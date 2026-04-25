import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
config.setup_logging()

from agents.exploiter import run_exploiter_agent

diff = {
    "changed_files": [{
        "filename": "app.py",
        "patch": """+def get_user(username):
+    import sqlite3
+    conn = sqlite3.connect("users.db")
+    cursor = conn.cursor()
+    # BUG: username is inserted directly — SQL injection possible
+    query = f"SELECT * FROM users WHERE username = '{username}'"
+    cursor.execute(query)
+    return cursor.fetchone()"""
    }]
}

semgrep_findings = [{
    "rule_id": "python.lang.security.audit.formatted-sql-query",
    "severity": "WARNING",
    "message": "Formatted SQL query. Possible SQL injection.",
    "line_start": 6,
    "category": "security"
}]

rag_context = "=== RELATED CODEBASE CONTEXT ===\nThis function is called by POST /login endpoint."

print("Running Agent 2 (The Exploiter)...")
print("Note: this requires a valid GROQ_API_KEY in your .env file")

if not config.GROQ_API_KEY:
    print("Skipping test: GROQ_API_KEY is not set in .env")
else:
    result = run_exploiter_agent(semgrep_findings[0], diff, rag_context)

    print("\n=== GENERATED EXPLOIT SCRIPT ===")
    print(result["exploit_script"])
    print(f"\nVulnerability type: {result['vulnerability_type']}")

