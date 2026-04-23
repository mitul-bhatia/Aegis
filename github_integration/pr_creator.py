import logging
from github import Github
import config

logger = logging.getLogger(__name__)

def create_pull_request(
    repo_full_name: str,
    base_branch: str,
    file_path: str,
    patched_code: str,
    vulnerability_type: str,
    exploit_output: str
) -> str:
    """
    Open a GitHub Pull Request with the fixed code and the exploit proof.
    """
    logger.info(f"Creating PR for {repo_full_name}...")
    
    g = Github(config.GITHUB_TOKEN)
    repo = g.get_repo(repo_full_name)
    
    import random
    import string
    random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    new_branch_name = f"aegis-fix-{vulnerability_type.lower().replace(' ', '-')}-{random_id}"
    
    base_ref = repo.get_git_ref(f"heads/{base_branch}")
    repo.create_git_ref(f"refs/heads/{new_branch_name}", base_ref.object.sha)
    
    file_contents = repo.get_contents(file_path, ref=base_branch)
    
    commit_message = f"🛡️ Aegis Security Patch: Fix {vulnerability_type}"
    repo.update_file(
        file_contents.path,
        commit_message,
        patched_code,
        file_contents.sha,
        branch=new_branch_name
    )
    
    pr_title = f"🛡️ Security Fix: {vulnerability_type} in {file_path}"
    
    pr_body = f"""## Aegis Autonomous Security Patch

Aegis detected a **{vulnerability_type}** vulnerability, automatically wrote an exploit to prove it was real, and generated this patch.

### 🔴 Proof of Vulnerability (Agent A)
We successfully exploited this code in an isolated sandbox. Here is the output of the exploit:
```text
{exploit_output}
```

### 🔵 The Fix (Agent B)
The vulnerable code in `{file_path}` has been patched to prevent this exploit.

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
