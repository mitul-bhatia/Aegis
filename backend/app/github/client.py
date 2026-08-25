import logging
from typing import List, Dict, Any, Optional
import requests
from github import Github, Auth
from backend.app.config import settings
from backend.app.github.auth import get_installation_access_token
from backend.app.schemas.dtos import AvailableRepo

logger = logging.getLogger("aegis.github.client")


class GitHubClient:
    def __init__(self, token: Optional[str] = None, installation_id: Optional[int] = None):
        self.installation_id = installation_id
        if token:
            self.token = token
        elif installation_id:
            try:
                self.token = get_installation_access_token(installation_id)
            except Exception as e:
                logger.warning(f"Could not get installation access token for {installation_id}: {e}")
                self.token = None
        else:
            self.token = None

        if self.token:
            self.gh = Github(auth=Auth.Token(self.token))
        else:
            self.gh = None

    def list_installation_repos(self) -> List[AvailableRepo]:
        """Fetch all repositories accessible by this installation."""
        if not self.token:
            return []

        url = "https://api.github.com/installation/repositories"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        repos: List[AvailableRepo] = []
        page = 1
        while True:
            resp = requests.get(f"{url}?per_page=100&page={page}", headers=headers, timeout=15)
            if resp.status_code != 200:
                logger.error(f"Failed to fetch installation repositories: {resp.text}")
                break
            data = resp.json()
            raw_repos = data.get("repositories", [])
            for r in raw_repos:
                repos.append(
                    AvailableRepo(
                        id=r["id"],
                        name=r["name"],
                        full_name=r["full_name"],
                        private=r["private"],
                        html_url=r["html_url"],
                        description=r.get("description"),
                        default_branch=r.get("default_branch", "main"),
                    )
                )
            if len(raw_repos) < 100:
                break
            page += 1

        return repos

    def get_commit_diff(self, repo_full_name: str, commit_sha: str) -> Dict[str, Any]:
        """Get commit details including changed files and patch diffs."""
        if not self.gh:
            raise ValueError("GitHub client not authenticated")

        repo = self.gh.get_repo(repo_full_name)
        if commit_sha == "HEAD":
            branch = repo.get_branch(repo.default_branch)
            commit = branch.commit
        else:
            commit = repo.get_commit(commit_sha)

        files = []
        combined_diff = []
        for f in commit.files:
            files.append(f.filename)
            if f.patch:
                combined_diff.append(f"--- a/{f.filename}\n+++ b/{f.filename}\n{f.patch}")

        return {
            "sha": commit.sha,
            "message": commit.commit.message,
            "files": files,
            "diff": "\n\n".join(combined_diff),
            "html_url": commit.html_url,
        }

    def get_file_content(self, repo_full_name: str, file_path: str, ref: str = "main") -> Optional[str]:
        """Fetch raw content of a specific file from GitHub."""
        if not self.gh:
            return None
        try:
            repo = self.gh.get_repo(repo_full_name)
            content_file = repo.get_contents(file_path, ref=ref)
            if isinstance(content_file, list):
                return None
            return content_file.decoded_content.decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Could not fetch {file_path} from {repo_full_name} at {ref}: {e}")
            return None

    def create_pull_request(
        self,
        repo_full_name: str,
        title: str,
        body: str,
        branch_name: str,
        files_to_update: Dict[str, str],
        base_branch: str = "main",
    ) -> str:
        """
        Create a new branch, commit file changes, and open a Pull Request.
        Returns the HTML URL of the created PR.
        """
        if not self.gh:
            raise ValueError("GitHub client not authenticated")

        repo = self.gh.get_repo(repo_full_name)
        
        # 1. Get base branch SHA
        try:
            base_ref = repo.get_git_ref(f"heads/{base_branch}")
            base_sha = base_ref.object.sha
        except Exception:
            base_branch = repo.default_branch
            base_ref = repo.get_git_ref(f"heads/{base_branch}")
            base_sha = base_ref.object.sha

        # 2. Create new branch ref
        try:
            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)
        except Exception as e:
            logger.warning(f"Branch {branch_name} may already exist: {e}")

        # 3. Commit changes
        for file_path, new_content in files_to_update.items():
            try:
                existing = repo.get_contents(file_path, ref=branch_name)
                repo.update_file(
                    path=file_path,
                    message=f"fix(security): sanitize vulnerability in {file_path} via Aegis",
                    content=new_content,
                    sha=existing.sha,
                    branch=branch_name,
                )
            except Exception:
                repo.create_file(
                    path=file_path,
                    message=f"fix(security): create patched file {file_path} via Aegis",
                    content=new_content,
                    branch=branch_name,
                )

        # 4. Open PR via repo.create_pull
        pr = repo.create_pull(
            title=title,
            body=body,
            head=branch_name,
            base=base_branch,
        )
        return pr.html_url
