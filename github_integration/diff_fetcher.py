import os
import subprocess
import logging
from github import Github

import config

logger = logging.getLogger(__name__)

def clone_or_pull_repo(repo_url: str, local_path: str) -> str:
    """
    Download the repository to our server so we can scan it.
    """
    if os.path.exists(local_path):
        logger.info(f"Pulling latest changes into {local_path}")
        subprocess.run(["git", "-C", local_path, "pull"], capture_output=True)
    else:
        logger.info(f"Cloning {repo_url} into {local_path}")
        subprocess.run(["git", "clone", repo_url, local_path], capture_output=True)
    
    return local_path

def get_diff(repo_full_name: str, commit_sha: str) -> dict:
    """
    Get the list of files changed in a specific commit, with the actual diffs.
    """
    g = Github(config.GITHUB_TOKEN)
    repo = g.get_repo(repo_full_name)
    commit = repo.get_commit(commit_sha)
    
    changed_files = []
    for file in commit.files:
        _, ext = os.path.splitext(file.filename)
        
        if ext not in config.CODE_EXTENSIONS:
            continue
            
        changed_files.append({
            "filename": file.filename,
            "status": file.status,
            "additions": file.additions,
            "deletions": file.deletions,
            "patch": file.patch or "",
        })
        
    return {
        "commit_sha": commit_sha,
        "commit_message": commit.commit.message,
        "changed_files": changed_files,
        "total_changes": sum(f["additions"] + f["deletions"] for f in changed_files)
    }
