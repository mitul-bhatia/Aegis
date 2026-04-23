#!/usr/bin/env python3
"""
Complete Aegis System Test
Tests all components: Backend API, Database, Sandbox, GitHub integration
"""

import sys
import os
import requests
import time

print("🛡️  AEGIS COMPLETE SYSTEM TEST")
print("="*60)

# Test 1: Backend Health
print("\n1️⃣  Testing Backend Health...")
try:
    response = requests.get("http://localhost:8000/health", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Backend is running: {data['status']}")
        print(f"   Version: {data['version']}")
    else:
        print(f"   ❌ Backend returned status {response.status_code}")
        sys.exit(1)
except requests.exceptions.ConnectionError:
    print("   ❌ Backend is not running on port 8000")
    print("   Run: ./start-backend.sh")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 2: Frontend
print("\n2️⃣  Testing Frontend...")
try:
    response = requests.get("http://localhost:3000", timeout=5)
    if response.status_code == 200:
        print("   ✅ Frontend is running on port 3000")
    else:
        print(f"   ⚠️  Frontend returned status {response.status_code}")
except requests.exceptions.ConnectionError:
    print("   ❌ Frontend is not running on port 3000")
    print("   Run: ./start-frontend.sh")
except Exception as e:
    print(f"   ⚠️  Frontend check failed: {e}")

# Test 3: Database
print("\n3️⃣  Testing Database...")
if os.path.exists("aegis.db"):
    print("   ✅ Database file exists: aegis.db")
    size = os.path.getsize("aegis.db")
    print(f"   Size: {size:,} bytes")
else:
    print("   ❌ Database file not found")

# Test 4: Vector DB
print("\n4️⃣  Testing Vector Database...")
if os.path.exists("aegis_vector_db"):
    print("   ✅ Vector DB directory exists")
    files = os.listdir("aegis_vector_db")
    print(f"   Files: {len(files)}")
else:
    print("   ⚠️  Vector DB directory not found (will be created on first repo index)")

# Test 5: Docker
print("\n5️⃣  Testing Docker...")
try:
    import docker
    client = docker.from_env()
    client.ping()
    print("   ✅ Docker daemon is running")
    
    # Check for sandbox image
    try:
        image = client.images.get("aegis-sandbox:latest")
        print(f"   ✅ Sandbox image exists: {image.short_id}")
        print(f"   Size: {image.attrs['Size'] / (1024*1024):.1f} MB")
    except docker.errors.ImageNotFound:
        print("   ❌ Sandbox image not found")
        print("   Run: ./build-sandbox.sh")
        
except Exception as e:
    print(f"   ❌ Docker error: {e}")

# Test 6: Environment Variables
print("\n6️⃣  Testing Environment Variables...")
from dotenv import load_dotenv
load_dotenv()

required_vars = [
    "MISTRAL_API_KEY",
    "GITHUB_TOKEN",
    "GITHUB_CLIENT_ID",
    "GITHUB_CLIENT_SECRET",
    "GITHUB_WEBHOOK_SECRET"
]

all_set = True
for var in required_vars:
    value = os.getenv(var, "")
    if value:
        masked = value[:8] + "..." if len(value) > 8 else "***"
        print(f"   ✅ {var}: {masked}")
    else:
        print(f"   ❌ {var}: NOT SET")
        all_set = False

if not all_set:
    print("\n   ⚠️  Some environment variables are missing!")
    print("   Check your .env file")

# Test 7: API Endpoints
print("\n7️⃣  Testing API Endpoints...")
endpoints = [
    "/health",
    "/api/repos",
    "/api/scans",
]

for endpoint in endpoints:
    try:
        response = requests.get(f"http://localhost:8000{endpoint}", timeout=3)
        if response.status_code in [200, 422]:  # 422 is expected for some endpoints without params
            print(f"   ✅ {endpoint}")
        else:
            print(f"   ⚠️  {endpoint} - Status {response.status_code}")
    except Exception as e:
        print(f"   ❌ {endpoint} - {e}")

# Test 8: Sandbox Execution
print("\n8️⃣  Testing Sandbox Execution...")
sys.path.insert(0, os.path.dirname(__file__))
try:
    from sandbox.docker_runner import run_exploit_in_sandbox
    import tempfile
    
    test_script = """
import sys
print("Sandbox test successful")
print("VULNERABLE: Test")
sys.exit(0)
"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_exploit_in_sandbox(test_script, tmpdir, timeout=5)
        if result["exploit_succeeded"]:
            print("   ✅ Sandbox execution works")
        else:
            print(f"   ❌ Sandbox test failed: {result.get('stderr', 'Unknown error')}")
except Exception as e:
    print(f"   ❌ Sandbox test error: {e}")

# Summary
print("\n" + "="*60)
print("📊 SYSTEM STATUS SUMMARY")
print("="*60)
print("\nIf all tests passed, your Aegis system is ready!")
print("\nNext steps:")
print("1. Open http://localhost:3000 in your browser")
print("2. Sign in with GitHub")
print("3. Add a repository to monitor")
print("4. Push a commit with a vulnerability to test the pipeline")
print("\n" + "="*60)
