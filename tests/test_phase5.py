import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
config.setup_logging()

from sandbox.docker_runner import run_exploit_in_sandbox

test_exploit_script = """
import sqlite3
import os

conn = sqlite3.connect("/tmp/test.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER, username TEXT, password TEXT)")
cursor.execute("INSERT INTO users VALUES (1, 'admin', 'secret_password')")
cursor.execute("INSERT INTO users VALUES (2, 'alice', 'alice_password')")
conn.commit()

malicious_input = "' OR '1'='1"
query = f"SELECT * FROM users WHERE username = '{malicious_input}'"
print(f"Executing query: {query}")

cursor.execute(query)
results = cursor.fetchall()

if len(results) > 1:
    print(f"VULNERABLE: SQL Injection confirmed!")
    print(f"Leaked {len(results)} rows of user data: {results}")
    exit(0)
else:
    print("NOT_VULNERABLE: Query returned expected number of rows")
    exit(1)
"""

print("Testing Docker sandbox execution...")
print("(Make sure Docker Desktop is running first!)\n")

result = run_exploit_in_sandbox(test_exploit_script, "/tmp")

print(f"\nFull result:")
print(f"  Exit code: {result['exit_code']}")
print(f"  Exploit worked: {result['exploit_succeeded']}")
print(f"  Output: {result['stdout']}")
