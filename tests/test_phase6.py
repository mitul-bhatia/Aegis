import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
config.setup_logging()

from agents.engineer import run_engineer_agent

vulnerable_code = """import sqlite3

def get_user(username):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()
"""

exploit_output = """
VULNERABLE: SQL Injection confirmed!
Input used: ' OR '1'='1
Query that ran: SELECT * FROM users WHERE username = '' OR '1'='1'
Leaked 2 rows of user data: [(1, 'admin', 'secret'), (2, 'alice', 'pass')]
"""

print("Running Agent B (The Engineer)...")
print("Note: this requires a valid MISTRAL_API_KEY in your .env file")

if not config.MISTRAL_API_KEY:
    print("Skipping test: MISTRAL_API_KEY is not set in .env")
else:
    result = run_engineer_agent(
        vulnerable_code=vulnerable_code,
        file_path="app.py",
        exploit_output=exploit_output,
        vulnerability_type="SQL Injection"
    )

    print("\n=== PATCHED CODE ===")
    print(result["patched_code"])

    if "?" in result["patched_code"] or "%s" in result["patched_code"]:
        print("\n✅ Patch correctly uses parameterized queries!")
    else:
        print("\n⚠️  Warning: Patch might not be using parameterized queries")
