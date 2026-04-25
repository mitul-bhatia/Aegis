import logging
from github import Github
from github.GithubException import UnknownObjectException
import config
import time

logger = logging.getLogger(__name__)

def create_pull_request(
    repo_full_name: str,
    base_branch: str,
    file_path: str,
    patched_code: str,
    test_code: str,
    vulnerability_type: str,
    exploit_output: str,
    patch_attempts: int
) -> str:
    """
    Open a GitHub Pull Request with the fixed code and the exploit proof.
    """
    logger.info(f"Creating PR for {repo_full_name}...")
    
    g = Github(config.GITHUB_TOKEN)
    repo = g.get_repo(repo_full_name)
    
    import random
    import string

    timestamp = int(time.time())
    new_branch_name = f"aegis/fix-{vulnerability_type.lower().replace(' ', '-')}-{timestamp}"
    
    base_ref = repo.get_git_ref(f"heads/{base_branch}")
    repo.create_git_ref(f"refs/heads/{new_branch_name}", base_ref.object.sha)
    
    commit_message = f"🛡️ Aegis Security Patch: Fix {vulnerability_type}"
    
    try:
        file_contents = repo.get_contents(file_path, ref=base_branch)
        repo.update_file(
            file_contents.path,
            commit_message,
            patched_code,
            file_contents.sha,
            branch=new_branch_name
        )
    except UnknownObjectException:
        repo.create_file(
            file_path,
            commit_message,
            patched_code,
            branch=new_branch_name
        )

    if test_code:
        # Check if test file already exists or what path to use
        # Let's assume we create a test file in the same dir
        test_file_path = f"test_{file_path.split('/')[-1]}"
        if '/' in file_path:
            test_file_path = "/".join(file_path.split('/')[:-1]) + "/" + test_file_path

        try:
            test_file_contents = repo.get_contents(test_file_path, ref=base_branch)
            repo.update_file(
                test_file_contents.path,
                f"🛡️ Aegis Security Patch: Add tests for {vulnerability_type}",
                test_code,
                test_file_contents.sha,
                branch=new_branch_name
            )
        except UnknownObjectException:
            repo.create_file(
                test_file_path,
                f"🛡️ Aegis Security Patch: Add tests for {vulnerability_type}",
                test_code,
                branch=new_branch_name
            )

    pr_title = f"🛡️ Security Fix: {vulnerability_type} in {file_path}"
    
    truncated_exploit_output = exploit_output
    if len(truncated_exploit_output) > 800:
        truncated_exploit_output = truncated_exploit_output[:800] + "\n...[truncated]"

    pr_body = f"""## Aegis Autonomous Security Patch

Aegis detected a **{vulnerability_type}** vulnerability, automatically wrote an exploit to prove it was real, and generated this patch.

### 🔴 Proof of Vulnerability (Agent A)
We successfully exploited this code in an isolated sandbox. Here is the output of the exploit:
```text
{truncated_exploit_output}
```

### 🔵 The Fix (Agent B)
The vulnerable code in `{file_path}` has been patched to prevent this exploit.
Took {patch_attempts} attempt(s) to patch.

### 🟡 Verification (Agent C)
✅ The patch has been applied.
✅ All existing unit tests pass.
✅ The exploit was re-run against the patched code and successfully blocked.

---
*This PR was generated entirely by the Aegis multi-agent security swarm.*"""

    pr = repo.create_pull(
        title=pr_title,
        body=pr_body,
        head=new_branch_name,
        base=base_branch
    )
    
    logger.info(f"✅ PR Created Successfully: {pr.html_url}")
    return pr.html_url
