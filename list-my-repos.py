#!/usr/bin/env python3
"""
List all GitHub repositories accessible by your token
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

if not GITHUB_TOKEN:
    print("❌ GITHUB_TOKEN not found in .env")
    exit(1)

print("🔍 Fetching your GitHub repositories...\n")

response = requests.get(
    "https://api.github.com/user/repos",
    headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    },
    params={"per_page": 100, "sort": "updated"}
)

if response.status_code != 200:
    print(f"❌ Error: {response.status_code}")
    print(response.json())
    exit(1)

repos = response.json()

print(f"Found {len(repos)} repositories:\n")
print("="*80)

for i, repo in enumerate(repos, 1):
    private = "🔒" if repo["private"] else "🌐"
    print(f"{i:3}. {private} {repo['full_name']}")
    print(f"     URL: {repo['html_url']}")
    print(f"     Updated: {repo['updated_at']}")
    if repo.get('description'):
        print(f"     Description: {repo['description'][:60]}")
    print()

print("="*80)
print("\n💡 To add a repo to Aegis, use the full name (e.g., 'mitu1046/Animation-Nation')")
print("   or the full URL (e.g., 'https://github.com/mitu1046/Animation-Nation')")
