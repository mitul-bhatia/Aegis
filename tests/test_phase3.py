import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rag.indexer import index_repository
from rag.retriever import retrieve_relevant_context

print("Step 1: Indexing the test repo...")
count = index_repository("./test_repo", "test/vulnerable-app")
print(f"Indexed {count} files\n")

print("Step 2: Retrieving relevant context for a simulated commit...")

diff = {
    "changed_files": [{
        "filename": "app.py",
        "patch": '+def get_user(username):\n+    query = f"SELECT * FROM users WHERE username = \'{username}\'"'
    }]
}
semgrep_findings = [{"message": "SQL injection in formatted query string"}]

context = retrieve_relevant_context("test/vulnerable-app", diff, semgrep_findings)
print(context)
print("✅ RAG retrieval working!")
