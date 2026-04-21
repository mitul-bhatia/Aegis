import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scanner.semgrep_runner import run_semgrep_on_files, format_findings_for_llm

print("Testing Semgrep scanner...")

with tempfile.TemporaryDirectory() as tmpdir:
    vuln_file = os.path.join(tmpdir, "test.py")
    with open(vuln_file, "w") as f:
        f.write("""
import sqlite3
def get_user(name):
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")
    return cursor.fetchone()
""")
        
    findings = run_semgrep_on_files(["test.py"], tmpdir)
    
    print(f"✅ Semgrep found {len(findings)} finding(s)")
    
    if findings:
        print(f"   Rule triggered: {findings[0]['rule_id']}")
        print(f"   Severity: {findings[0]['severity']}")
        print(f"\nFormatted output for AI:\n")
        print(format_findings_for_llm(findings))
    else:
        print("   ⚠️ Expected to find SQL injection but didn't.")
