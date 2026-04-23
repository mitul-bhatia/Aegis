#!/usr/bin/env python3
"""
Create a test repository with an intentional SQL injection vulnerability
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
REPO_NAME = "aegis-test-repo"

if not GITHUB_TOKEN:
    print("❌ GITHUB_TOKEN not found in .env")
    exit(1)

print(f"🔧 Creating test repository: {REPO_NAME}\n")

# Create repository
response = requests.post(
    "https://api.github.com/user/repos",
    headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    },
    json={
        "name": REPO_NAME,
        "description": "Test repository for Aegis vulnerability scanner",
        "private": False,
        "auto_init": True,  # Initialize with README
    }
)

if response.status_code == 201:
    repo = response.json()
    print(f"✅ Repository created successfully!")
    print(f"   Name: {repo['full_name']}")
    print(f"   URL: {repo['html_url']}")
    print(f"   Clone URL: {repo['clone_url']}")
    
    print("\n📝 Next steps:")
    print(f"1. Add this repo to Aegis: {repo['full_name']}")
    print(f"2. Clone it locally: git clone {repo['clone_url']}")
    print(f"3. Add vulnerable code (see test_repo/app.py for example)")
    print(f"4. Push changes to trigger Aegis scan")
    
elif response.status_code == 422:
    error = response.json()
    if "already exists" in error.get("message", "").lower():
        print(f"✅ Repository '{REPO_NAME}' already exists!")
        print(f"   URL: https://github.com/mitu1046/{REPO_NAME}")
        print(f"\n   You can use: mitu1046/{REPO_NAME}")
    else:
        print(f"❌ Error: {error.get('message', 'Unknown error')}")
        print(response.json())
else:
    print(f"❌ Failed to create repository: {response.status_code}")
    print(response.json())
