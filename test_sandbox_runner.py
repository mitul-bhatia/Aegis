#!/usr/bin/env python3
"""
Test script to verify the Docker sandbox is working correctly.
This simulates what the Aegis pipeline does when testing exploits.
"""
import os
import sys

# Add current directory to path so we can import sandbox module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sandbox.docker_runner import run_exploit_in_sandbox, get_docker_client

def test_docker_connection():
    """Test if Docker daemon is accessible"""
    print("=" * 60)
    print("TEST 1: Docker Connection")
    print("=" * 60)
    
    client = get_docker_client()
    if client:
        print("✅ Docker daemon is running")
        print(f"   Docker version: {client.version()['Version']}")
        return True
    else:
        print("❌ Docker daemon is not running")
        return False

def test_exploit_sandbox():
    """Test running an exploit in the sandbox"""
    print("\n" + "=" * 60)
    print("TEST 2: Exploit Sandbox Execution")
    print("=" * 60)
    
    # Read the exploit script
    exploit_path = "test_sandbox/exploit.py"
    if not os.path.exists(exploit_path):
        print(f"❌ Exploit script not found: {exploit_path}")
        return False
    
    with open(exploit_path, 'r') as f:
        exploit_script = f.read()
    
    # Path to the vulnerable app
    repo_path = os.path.abspath("test_sandbox")
    
    print(f"📁 Repo path: {repo_path}")
    print(f"📜 Exploit script: {len(exploit_script)} characters")
    print("\n🚀 Running exploit in Docker sandbox...")
    print("-" * 60)
    
    # Run the exploit
    result = run_exploit_in_sandbox(exploit_script, repo_path, timeout=30)
    
    print("\n📊 RESULTS:")
    print("-" * 60)
    print(f"Exit Code: {result['exit_code']}")
    print(f"Exploit Succeeded: {result['exploit_succeeded']}")
    print(f"Vulnerability Confirmed: {result['vulnerability_confirmed']}")
    
    print("\n📤 STDOUT:")
    print("-" * 60)
    print(result['stdout'])
    
    if result['stderr']:
        print("\n📥 STDERR:")
        print("-" * 60)
        print(result['stderr'])
    
    print("\n" + "=" * 60)
    if result['exploit_succeeded']:
        print("✅ TEST PASSED: Exploit successfully confirmed vulnerability")
        print("   The sandbox correctly executed the exploit and detected")
        print("   the SQL injection vulnerability.")
        return True
    else:
        print("❌ TEST FAILED: Exploit did not confirm vulnerability")
        return False

def test_sandbox_security():
    """Test that sandbox security features are working"""
    print("\n" + "=" * 60)
    print("TEST 3: Sandbox Security Features")
    print("=" * 60)
    
    # Test script that tries to access network (should fail)
    network_test = """
import urllib.request
import sys

try:
    urllib.request.urlopen('https://google.com', timeout=5)
    print("SECURITY_BREACH: Network access allowed!")
    sys.exit(1)
except Exception as e:
    print(f"✅ Network access blocked: {e}")
    sys.exit(0)
"""
    
    repo_path = os.path.abspath("test_sandbox")
    print("🔒 Testing network isolation...")
    result = run_exploit_in_sandbox(network_test, repo_path, timeout=10)
    
    if "Network access blocked" in result['stdout']:
        print("✅ Network isolation working correctly")
        return True
    else:
        print("❌ Network isolation may not be working")
        print(f"   Output: {result['stdout']}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("AEGIS DOCKER SANDBOX TEST SUITE")
    print("=" * 60)
    
    results = []
    
    # Test 1: Docker connection
    results.append(("Docker Connection", test_docker_connection()))
    
    if not results[0][1]:
        print("\n❌ Docker is not running. Please start Docker Desktop and try again.")
        return
    
    # Test 2: Exploit execution
    results.append(("Exploit Sandbox", test_exploit_sandbox()))
    
    # Test 3: Security features
    results.append(("Security Features", test_sandbox_security()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("   The Docker sandbox is working correctly and ready to use.")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("   Please review the output above for details.")
    print("=" * 60)

if __name__ == "__main__":
    main()
