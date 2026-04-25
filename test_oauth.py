#!/usr/bin/env python3
"""Test GitHub OAuth credentials"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

print(f"Testing OAuth app: {CLIENT_ID}")
print(f"Client secret: {CLIENT_SECRET[:10]}...")

# Test with a dummy code - should get "bad_verification_code" if credentials are valid
response = requests.post(
    "https://github.com/login/oauth/access_token",
    json={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": "dummy_test_code",
        "redirect_uri": "http://localhost:3000/auth/callback"
    },
    headers={"Accept": "application/json"},
    timeout=10
)

print(f"\nGitHub response status: {response.status_code}")
print(f"Response: {response.json()}")

data = response.json()
if "error" in data:
    if data["error"] == "bad_verification_code":
        print("\n✅ OAuth credentials are VALID (GitHub recognizes the app)")
    elif data["error"] == "incorrect_client_credentials":
        print("\n❌ OAuth credentials are INVALID (wrong client_id or client_secret)")
    elif data["error"] == "redirect_uri_mismatch":
        print("\n❌ Callback URL mismatch in GitHub OAuth app settings")
    else:
        print(f"\n⚠️  Unexpected error: {data['error']}")
