#!/usr/bin/env python3
"""
Test Aegis with real GitHub repository
"""
import logging
from orchestrator import run_aegis_pipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Simulate a push event to the test repo
push_info = {
    "repo_name": "mitu1046/aegis-test-repo",
    "repo_url": "https://github.com/mitu1046/aegis-test-repo.git",
    "commit_sha": "HEAD",  # Will use latest commit
    "branch": "main",
    "files_changed": [],  # Will be detected by diff_fetcher
}

print("="*70)
print("TESTING AEGIS WITH REAL GITHUB REPO")
print("="*70)
print(f"\nRepo: {push_info['repo_name']}")
print(f"URL: {push_info['repo_url']}")
print("\nStarting pipeline...\n")

try:
    run_aegis_pipeline(push_info)
    print("\n" + "="*70)
    print("PIPELINE COMPLETED")
    print("="*70)
except Exception as e:
    print("\n" + "="*70)
    print(f"PIPELINE FAILED: {e}")
    print("="*70)
    import traceback
    traceback.print_exc()
