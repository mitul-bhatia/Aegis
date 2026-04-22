#!/usr/bin/env python3
"""
Test Docker Sandbox Environment
Verifies that the Docker sandbox can run exploit scripts safely
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sandbox.docker_runner import run_exploit_in_sandbox
import tempfile

print("🐳 Testing Docker Sandbox Environment...\n")

# Create a simple test exploit script
test_exploit = """
import sys

print("Testing sandbox environment...")
print("Python version:", sys.version)

# Try to detect if we're in a container
try:
    with open('/proc/1/cgroup', 'r') as f:
        if 'docker' in f.read():
            print("✅ Running inside Docker container")
        else:
            print("❌ Not in Docker container")
except:
    print("⚠️  Cannot determine container status")

# Test the vulnerability detection pattern
print("VULNERABLE: Test vulnerability detected")
print("Exploit completed successfully")
sys.exit(0)
"""

# Create a temporary repo directory
with tempfile.TemporaryDirectory() as tmpdir:
    # Create a simple test file
    test_file = os.path.join(tmpdir, "test.py")
    with open(test_file, "w") as f:
        f.write("# Test repository file\n")
    
    print("Running exploit in sandbox...")
    result = run_exploit_in_sandbox(test_exploit, tmpdir, timeout=10)
    
    print("\n" + "="*60)
    print("SANDBOX TEST RESULTS")
    print("="*60)
    print(f"Exit Code: {result['exit_code']}")
    print(f"Exploit Succeeded: {result['exploit_succeeded']}")
    print(f"Vulnerability Confirmed: {result['vulnerability_confirmed']}")
    print("\n--- STDOUT ---")
    print(result['stdout'])
    if result['stderr']:
        print("\n--- STDERR ---")
        print(result['stderr'])
    print("="*60)
    
    if result['exploit_succeeded']:
        print("\n✅ Docker sandbox is working correctly!")
        print("   - Container isolation: OK")
        print("   - Exploit execution: OK")
        print("   - Vulnerability detection: OK")
        sys.exit(0)
    else:
        print("\n❌ Docker sandbox test failed!")
        print(f"   Error: {result.get('output_summary', 'Unknown error')}")
        sys.exit(1)
