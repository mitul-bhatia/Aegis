"""
Test script to verify the patch works correctly
This is what the Verifier agent runs to confirm the fix.
"""
import sys
import os
import sqlite3

os.chdir('/tmp')
sys.path.insert(0, '/app')

try:
    from patched_app import get_user, setup_database
    
    # Setup the test database
    setup_database()
    print("[*] Database initialized")
    
    # Test 1: Normal query (should still work)
    result = get_user("alice")
    if result and result[1] == "alice":
        print(f"✅ Normal query works: {result}")
    else:
        print(f"❌ Normal query failed: {result}")
        sys.exit(1)
    
    # Test 2: SQL Injection attack (should be blocked)
    malicious_input = "' OR '1'='1"
    result = get_user(malicious_input)
    
    if result is None:
        print(f"✅ SQL Injection blocked successfully!")
        print(f"   Malicious input '{malicious_input}' returned None")
        print("NOT_VULNERABLE: Parameterized query blocked the injection")
        sys.exit(0)  # Exit code 0 = patch works (exploit blocked)
    else:
        print(f"❌ SQL Injection still works: {result}")
        print(f"VULNERABLE: Patch did not fix the vulnerability")
        sys.exit(1)  # Exit code 1 = patch failed
        
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
