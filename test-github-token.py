#!/usr/bin/env python3
"""
Test GitHub Token Permissions
Checks if your GITHUB_TOKEN has the required scopes for Aegis
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

if not GITHUB_TOKEN:
    print("❌ GITHUB_TOKEN not found in .env file")
    exit(1)

print("🔍 Testing GitHub token permissions...\n")

# Test token validity and get scopes
response = requests.get(
    "https://api.github.com/user",
    headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
)

if response.status_code != 200:
    print(f"❌ Token is invalid or expired")
    print(f"   Status: {response.status_code}")
    print(f"   Error: {response.json().get('message', 'Unknown error')}")
    exit(1)

user = response.json()
scopes = response.headers.get("X-OAuth-Scopes", "").split(", ")

print(f"✅ Token is valid")
print(f"   User: {user['login']}")
print(f"   Scopes: {', '.join(scopes) if scopes else 'None'}\n")

# Check required scopes
required_scopes = ["repo", "admin:repo_hook"]
missing_scopes = []

for scope in required_scopes:
    if scope in scopes or "repo" in scopes and scope.startswith("repo"):
        print(f"✅ {scope}")
    else:
        print(f"❌ {scope} - MISSING")
        missing_scopes.append(scope)

if missing_scopes:
    print(f"\n⚠️  Missing required scopes: {', '.join(missing_scopes)}")
    print("\n📝 To fix this:")
    print("   1. Go to: https://github.com/settings/tokens")
    print("   2. Create a new token with these scopes:")
    print("      - repo (Full control of private repositories)")
    print("      - admin:repo_hook (Full control of repository hooks)")
    print("   3. Update GITHUB_TOKEN in your .env file")
    exit(1)
else:
    print("\n✅ All required permissions are present!")
    print("   Your token is ready to use with Aegis.")
