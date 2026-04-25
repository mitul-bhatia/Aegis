import config
from orchestrator import run_aegis_pipeline

push_info = {
    "repo_name": "Jivit87/aegis-pr-test",
    "commit_sha": "ad8dd8e499252164f8accf21fd16910ec6837545",
    "branch": "main",
    "files_changed": ["app.py"],
    "is_pr": False,
}

run_aegis_pipeline(push_info)
print("Pipeline run finished.")
