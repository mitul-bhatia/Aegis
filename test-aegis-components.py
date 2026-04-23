#!/usr/bin/env python3
"""
Comprehensive Aegis Component Testing Script
Tests each component individually before integration
"""
import os
import sys
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_section(title):
    """Print a nice section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def test_semgrep():
    """Test 1: Check if Semgrep works"""
    print_section("TEST 1: Semgrep Scanner")
    
    try:
        from scanner.semgrep_runner import run_semgrep_on_files
        
        # Test on our vulnerable test repo
        test_files = ["app.py"]
        findings = run_semgrep_on_files(test_files, "test_repo")
        
        if findings:
            logger.info(f"✅ Semgrep WORKS - Found {len(findings)} vulnerabilities")
            for i, f in enumerate(findings, 1):
                logger.info(f"  {i}. {f['severity']} - {f['rule_id']}")
                logger.info(f"     File: {f['file']} (line {f['line_start']})")
            return True, findings
        else:
            logger.warning("⚠️  Semgrep ran but found no vulnerabilities (unexpected)")
            return False, []
            
    except Exception as e:
        logger.error(f"❌ Semgrep FAILED: {e}")
        return False, []

def test_rag_system():
    """Test 2: RAG Indexing and Retrieval"""
    print_section("TEST 2: RAG System (Indexing + Retrieval)")
    
    try:
        from rag.indexer import index_repository
        from rag.retriever import retrieve_relevant_context
        
        # Index the test repo
        logger.info("Indexing test_repo...")
        count = index_repository("test_repo", "test/repo")
        
        if count > 0:
            logger.info(f"✅ RAG Indexer WORKS - Indexed {count} files")
        else:
            logger.warning("⚠️  RAG Indexer ran but indexed 0 files")
            return False
        
        # Test retrieval
        logger.info("Testing retrieval...")
        mock_diff = {
            "changed_files": [{
                "filename": "app.py",
                "patch": "def get_user(username):\n    query = f\"SELECT * FROM users WHERE username = '{username}'\""
            }]
        }
        
        mock_findings = [{
            "rule_id": "python.lang.security.audit.formatted-sql-query",
            "message": "SQL injection vulnerability",
            "severity": "ERROR"
        }]
        
        context = retrieve_relevant_context("test/repo", mock_diff, mock_findings)
        
        if context and "No related context" not in context:
            logger.info(f"✅ RAG Retriever WORKS - Retrieved {len(context)} chars of context")
            logger.info(f"   Preview: {context[:200]}...")
            return True
        else:
            logger.warning("⚠️  RAG Retriever returned no context")
            return False
            
    except Exception as e:
        logger.error(f"❌ RAG System FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_a(semgrep_findings):
    """Test 3: Agent A (Hacker) - Exploit Generation"""
    print_section("TEST 3: Agent A (Hacker) - Exploit Generation")
    
    if not semgrep_findings:
        logger.warning("⚠️  Skipping Agent A test - no Semgrep findings available")
        return False, None
    
    try:
        from agents.hacker import run_hacker_agent
        
        mock_diff = {
            "changed_files": [{
                "filename": "app.py",
                "patch": """
@@ -1,10 +1,10 @@
 import sqlite3
 
 def get_user(username):
     conn = sqlite3.connect("users.db")
     cursor = conn.cursor()
-    query = f"SELECT * FROM users WHERE username = '{username}'"
+    query = f"SELECT * FROM users WHERE username = '{username}'"
     cursor.execute(query)
     return cursor.fetchone()
"""
            }]
        }
        
        rag_context = "This is a Flask app with SQLite database. The get_user function queries the users table."
        
        logger.info("Calling Agent A to generate exploit...")
        result = run_hacker_agent(mock_diff, semgrep_findings, rag_context)
        
        exploit_script = result["exploit_script"]
        vuln_type = result["vulnerability_type"]
        
        if exploit_script and len(exploit_script) > 50:
            logger.info(f"✅ Agent A WORKS - Generated {len(exploit_script)} char exploit")
            logger.info(f"   Vulnerability Type: {vuln_type}")
            logger.info(f"   Script preview:\n{exploit_script[:300]}...")
            return True, exploit_script
        else:
            logger.warning("⚠️  Agent A returned empty or very short exploit")
            return False, None
            
    except Exception as e:
        logger.error(f"❌ Agent A FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_docker_sandbox(exploit_script):
    """Test 4: Docker Sandbox - Run Exploit"""
    print_section("TEST 4: Docker Sandbox - Run Exploit")
    
    if not exploit_script:
        logger.warning("⚠️  Skipping Docker test - no exploit script available")
        return False, None
    
    try:
        from sandbox.docker_runner import run_exploit_in_sandbox
        
        logger.info("Running exploit in Docker sandbox...")
        result = run_exploit_in_sandbox(exploit_script, "test_repo")
        
        logger.info(f"   Exit code: {result['exit_code']}")
        logger.info(f"   Exploit succeeded: {result['exploit_succeeded']}")
        logger.info(f"   Output:\n{result['stdout'][:500]}")
        
        if result['stderr']:
            logger.info(f"   Stderr:\n{result['stderr'][:500]}")
        
        if result['exploit_succeeded']:
            logger.info("✅ Docker Sandbox WORKS - Exploit ran and succeeded")
            return True, result
        else:
            logger.warning("⚠️  Exploit ran but did not succeed (might be false positive)")
            return False, result
            
    except Exception as e:
        logger.error(f"❌ Docker Sandbox FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_agent_b(exploit_output):
    """Test 5: Agent B (Engineer) - Patch Generation"""
    print_section("TEST 5: Agent B (Engineer) - Patch Generation")
    
    if not exploit_output:
        logger.warning("⚠️  Skipping Agent B test - no exploit output available")
        return False, None
    
    try:
        from agents.engineer import run_engineer_agent
        
        # Read the vulnerable code
        with open("test_repo/app.py", "r") as f:
            vulnerable_code = f.read()
        
        logger.info("Calling Agent B to generate patch...")
        result = run_engineer_agent(
            vulnerable_code=vulnerable_code,
            file_path="app.py",
            exploit_output=exploit_output["stdout"],
            vulnerability_type="SQL Injection"
        )
        
        patched_code = result["patched_code"]
        
        if patched_code and len(patched_code) > 50:
            logger.info(f"✅ Agent B WORKS - Generated {len(patched_code)} char patch")
            logger.info(f"   Patch preview:\n{patched_code[:300]}...")
            
            # Check if patch uses parameterized queries
            if "cursor.execute(" in patched_code and "?" in patched_code:
                logger.info("   ✅ Patch appears to use parameterized queries")
            
            return True, patched_code
        else:
            logger.warning("⚠️  Agent B returned empty or very short patch")
            return False, None
            
    except Exception as e:
        logger.error(f"❌ Agent B FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_agent_c(exploit_script, patched_code):
    """Test 6: Agent C (Reviewer) - Verification Loop"""
    print_section("TEST 6: Agent C (Reviewer) - Verification Loop")
    
    if not exploit_script or not patched_code:
        logger.warning("⚠️  Skipping Agent C test - missing exploit or patch")
        return False
    
    try:
        from agents.reviewer import run_remediation_loop
        
        # Read the vulnerable code
        with open("test_repo/app.py", "r") as f:
            vulnerable_code = f.read()
        
        # Backup original
        backup_path = "test_repo/app.py.backup"
        with open(backup_path, "w") as f:
            f.write(vulnerable_code)
        
        logger.info("Running full remediation loop...")
        result = run_remediation_loop(
            vulnerable_code=vulnerable_code,
            file_path="app.py",
            exploit_script=exploit_script,
            exploit_output="VULNERABLE: SQL injection confirmed",
            vulnerability_type="SQL Injection",
            repo_path="test_repo"
        )
        
        # Restore original
        with open("test_repo/app.py", "w") as f:
            f.write(vulnerable_code)
        os.remove(backup_path)
        
        if result["success"]:
            logger.info(f"✅ Agent C WORKS - Patch verified in {result['attempts']} attempts")
            return True
        else:
            logger.warning(f"⚠️  Agent C failed after {result['attempts']} attempts")
            return False
            
    except Exception as e:
        logger.error(f"❌ Agent C FAILED: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to restore backup
        try:
            if os.path.exists("test_repo/app.py.backup"):
                with open("test_repo/app.py.backup", "r") as f:
                    original = f.read()
                with open("test_repo/app.py", "w") as f:
                    f.write(original)
                os.remove("test_repo/app.py.backup")
        except:
            pass
        
        return False

def main():
    """Run all tests in sequence"""
    print("\n" + "🔍 AEGIS COMPONENT TESTING SUITE" + "\n")
    print("This will test each component individually to see what works.\n")
    
    results = {}
    
    # Test 1: Semgrep
    semgrep_works, semgrep_findings = test_semgrep()
    results["semgrep"] = semgrep_works
    
    # Test 2: RAG System
    rag_works = test_rag_system()
    results["rag"] = rag_works
    
    # Test 3: Agent A
    agent_a_works, exploit_script = test_agent_a(semgrep_findings if semgrep_works else [])
    results["agent_a"] = agent_a_works
    
    # Test 4: Docker Sandbox
    docker_works, exploit_output = test_docker_sandbox(exploit_script if agent_a_works else None)
    results["docker"] = docker_works
    
    # Test 5: Agent B
    agent_b_works, patched_code = test_agent_b(exploit_output if docker_works else None)
    results["agent_b"] = agent_b_works
    
    # Test 6: Agent C (full loop)
    agent_c_works = test_agent_c(
        exploit_script if agent_a_works else None,
        patched_code if agent_b_works else None
    )
    results["agent_c"] = agent_c_works
    
    # Final Summary
    print_section("FINAL RESULTS")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print(f"Component Test Results ({passed}/{total} passed):\n")
    print(f"  1. Semgrep Scanner:        {'✅ WORKS' if results['semgrep'] else '❌ BROKEN'}")
    print(f"  2. RAG System:             {'✅ WORKS' if results['rag'] else '❌ BROKEN'}")
    print(f"  3. Agent A (Hacker):       {'✅ WORKS' if results['agent_a'] else '❌ BROKEN'}")
    print(f"  4. Docker Sandbox:         {'✅ WORKS' if results['docker'] else '❌ BROKEN'}")
    print(f"  5. Agent B (Engineer):     {'✅ WORKS' if results['agent_b'] else '❌ BROKEN'}")
    print(f"  6. Agent C (Reviewer):     {'✅ WORKS' if results['agent_c'] else '❌ BROKEN'}")
    
    print("\n" + "-"*70)
    
    if passed == total:
        print("🎉 ALL COMPONENTS WORKING! Ready for integration.")
        return 0
    elif passed >= 4:
        print("⚠️  Most components work. Fix the broken ones before integration.")
        return 1
    else:
        print("❌ Multiple components broken. Need significant fixes.")
        return 2

if __name__ == "__main__":
    sys.exit(main())
