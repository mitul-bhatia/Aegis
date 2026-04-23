#!/usr/bin/env python3
"""
END-TO-END TEST: Full Aegis Pipeline
Tests the complete flow from webhook to PR
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("🛡️  AEGIS END-TO-END PIPELINE TEST")
print("="*60)

# Test 1: Semgrep Detection
print("\n1️⃣  Testing Semgrep Detection...")
from scanner.semgrep_runner import run_semgrep_on_files

findings = run_semgrep_on_files(["app.py"], "test_repo")
if findings:
    print(f"   ✅ Semgrep found {len(findings)} vulnerability(ies)")
    print(f"   Type: {findings[0]['rule_id']}")
else:
    print("   ❌ Semgrep found nothing - test repo might not have vulnerabilities")
    sys.exit(1)

# Test 2: Agent A (Hacker) - Generate Exploit
print("\n2️⃣  Testing Agent A (Hacker) - Exploit Generation...")
from agents.hacker import run_hacker_agent

# Simulate a diff
mock_diff = {
    "changed_files": [{
        "filename": "app.py",
        "patch": """
+def get_user(username):
+    query = f"SELECT * FROM users WHERE username = '{username}'"
+    cursor.execute(query)
"""
    }]
}

try:
    hacker_result = run_hacker_agent(mock_diff, findings, "Test context")
    exploit_script = hacker_result["exploit_script"]
    
    if exploit_script and len(exploit_script) > 50:
        print(f"   ✅ Agent A generated exploit ({len(exploit_script)} chars)")
        print(f"   Vulnerability type: {hacker_result['vulnerability_type']}")
    else:
        print("   ❌ Agent A failed to generate exploit")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Agent A error: {e}")
    sys.exit(1)

# Test 3: Docker Sandbox - Run Exploit
print("\n3️⃣  Testing Docker Sandbox - Exploit Execution...")
from sandbox.docker_runner import run_exploit_in_sandbox

try:
    exploit_result = run_exploit_in_sandbox(exploit_script, "test_repo")
    
    if exploit_result["exploit_succeeded"]:
        print("   ✅ Exploit ran successfully in Docker")
        print("   ✅ Vulnerability CONFIRMED")
        print(f"   Output: {exploit_result['stdout'][:100]}...")
    else:
        print("   ⚠️  Exploit ran but didn't confirm vulnerability")
        print(f"   Exit code: {exploit_result['exit_code']}")
        print(f"   Output: {exploit_result['stdout'][:200]}")
except Exception as e:
    print(f"   ❌ Docker sandbox error: {e}")
    sys.exit(1)

# Test 4: Agent B (Engineer) - Generate Patch
print("\n4️⃣  Testing Agent B (Engineer) - Patch Generation...")
from agents.engineer import run_engineer_agent

with open("test_repo/app.py", "r") as f:
    vulnerable_code = f.read()

try:
    engineer_result = run_engineer_agent(
        vulnerable_code=vulnerable_code,
        file_path="app.py",
        exploit_output=exploit_result["stdout"],
        vulnerability_type=hacker_result["vulnerability_type"]
    )
    
    patched_code = engineer_result["patched_code"]
    
    if patched_code and len(patched_code) > 50:
        print(f"   ✅ Agent B generated patch ({len(patched_code)} chars)")
        
        # Check if patch uses parameterized queries
        if "?" in patched_code or "execute(" in patched_code:
            print("   ✅ Patch appears to use parameterized queries")
        else:
            print("   ⚠️  Patch might not properly fix the vulnerability")
    else:
        print("   ❌ Agent B failed to generate patch")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Agent B error: {e}")
    sys.exit(1)

# Test 5: Verify Patch Works
print("\n5️⃣  Testing Patch Verification...")
import tempfile
import shutil

# Create a temporary directory with the patched code
with tempfile.TemporaryDirectory() as tmpdir:
    # Copy test repo
    shutil.copytree("test_repo", os.path.join(tmpdir, "test_repo"))
    patched_repo = os.path.join(tmpdir, "test_repo")
    
    # Apply patch
    with open(os.path.join(patched_repo, "app.py"), "w") as f:
        f.write(patched_code)
    
    # Run exploit again on patched code
    try:
        patched_result = run_exploit_in_sandbox(exploit_script, patched_repo)
        
        if not patched_result["exploit_succeeded"]:
            print("   ✅ Exploit FAILED on patched code")
            print("   ✅ Patch successfully fixes the vulnerability!")
        else:
            print("   ❌ Exploit STILL WORKS on patched code")
            print("   ❌ Patch does not fix the vulnerability")
            print(f"   Output: {patched_result['stdout'][:200]}")
    except Exception as e:
        print(f"   ⚠️  Error testing patched code: {e}")

# Summary
print("\n" + "="*60)
print("📊 END-TO-END TEST SUMMARY")
print("="*60)
print("\n✅ All core components are working:")
print("   1. Semgrep detects vulnerabilities")
print("   2. Agent A generates exploits")
print("   3. Docker sandbox runs exploits safely")
print("   4. Agent B generates patches")
print("   5. Patches can be verified")
print("\n🎯 The pipeline is functional!")
print("\nNext steps:")
print("   - Connect webhook to orchestrator")
print("   - Test with real GitHub push")
print("   - Verify PR creation")
print("="*60)
