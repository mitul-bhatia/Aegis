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

def get_diff(repo_full_name: str, commit_sha: str, github_token: str = None, all_changed_files: list = None) -> dict:
    """
    Get the list of files changed in a specific commit, with the actual diffs.
    If all_changed_files is provided (from the push webhook payload), it is used
    to ensure files changed in earlier commits of the same push are also included.
    """
    token = github_token if github_token else config.GITHUB_TOKEN
    g = Github(token)
    repo = g.get_repo(repo_full_name)
    commit = repo.get_commit(commit_sha)
    
    # Build a set of filenames to include — start with HEAD commit files
    head_files = {
        file.filename
        for file in commit.files
        if os.path.splitext(file.filename)[1] in config.CODE_EXTENSIONS
    }

    # Merge in any additional files from earlier commits in the same push
    extra_files: set = set()
    if all_changed_files:
        for f in all_changed_files:
            _, ext = os.path.splitext(f)
            if ext in config.CODE_EXTENSIONS and f not in head_files:
                extra_files.add(f)

    changed_files = []

    # Add HEAD commit diffs (have full patch info)
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

    # For files from earlier commits, fetch their content as a synthetic diff
    for filename in extra_files:
        try:
            contents = repo.get_contents(filename, ref=commit_sha)
            file_content = contents.decoded_content.decode("utf-8", errors="ignore")
            # Represent as a synthetic patch (full file as additions)
            patch_lines = "\n".join(f"+{line}" for line in file_content.splitlines())
            changed_files.append({
                "filename": filename,
                "status": "modified",
                "additions": file_content.count("\n"),
                "deletions": 0,
                "patch": patch_lines,
            })
            logger.info(f"Added earlier-commit file to diff: {filename}")
        except Exception as e:
            logger.warning(f"Could not fetch content for earlier-commit file {filename}: {e}")

    return {
        "commit_sha": commit_sha,
        "commit_message": commit.commit.message,
        "changed_files": changed_files,
        "total_changes": sum(f["additions"] + f["deletions"] for f in changed_files)
    }
