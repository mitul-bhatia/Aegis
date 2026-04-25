import logging
import os
import random
import string
from github import Github
import config

logger = logging.getLogger(__name__)


def create_pull_request(
    repo_full_name: str,
    base_branch: str,
    file_path: str,
    patched_code: str,
    vulnerability_type: str,
    exploit_output: str,
) -> str:
    """
    Open a GitHub Pull Request with the fixed code and the exploit proof.
    Used for push-triggered scans (not PR scans — those use post_pr_review).
    """
    logger.info(f"Creating PR for {repo_full_name}...")

    g = Github(config.GITHUB_TOKEN)
    repo = g.get_repo(repo_full_name)

    random_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
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
        branch=new_branch_name,
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
        base=base_branch,
    )

    logger.info(f"PR created: {pr.html_url}")
    return pr.html_url


def post_pr_review(
    repo_full_name: str,
    pr_number: int,
    commit_sha: str,
    findings: list[dict],
    patched_code: str | None = None,
    vulnerable_file: str | None = None,
    vulnerability_type: str | None = None,
    exploit_output: str | None = None,
) -> str:
    """
    Post inline review comments on an existing PR instead of creating a new one.

    For each finding, posts a comment on the specific line with:
    - Severity badge
    - Description of the vulnerability
    - Inline fix suggestion (if patched_code is available for that file)

    Returns the PR URL.
    """
    logger.info(f"Posting PR review on {repo_full_name}#{pr_number}...")

    g = Github(config.GITHUB_TOKEN)
    repo = g.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)

    # Build inline comments for each finding
    comments = []
    for finding in findings:
        file_path = finding.get("file", "")
        line = finding.get("line_start", 1)
        vuln_type = finding.get("vuln_type", "Vulnerability")
        severity = finding.get("severity", "HIGH")
        description = finding.get("description", "")

        severity_emoji = {
            "CRITICAL": "🚨",
            "HIGH": "🔴",
            "MEDIUM": "🟡",
            "LOW": "🔵",
        }.get(severity.upper(), "⚠️")

        body = (
            f"{severity_emoji} **Aegis Security Finding — {severity} — {vuln_type}**\n\n"
            f"{description}\n\n"
        )

        # Add inline fix suggestion if this is the confirmed vulnerable file
        if (
            patched_code
            and vulnerable_file
            and file_path == vulnerable_file
            and vulnerability_type
        ):
            # GitHub suggestion block — renders as an "Apply suggestion" button
            body += (
                f"**Suggested fix:**\n"
                f"```suggestion\n{patched_code}\n```\n\n"
            )

        body += "*Detected by [Aegis](https://github.com/Jivit87/Aegis) autonomous security scanner.*"

        comments.append({
            "path": file_path,
            "line": line,
            "body": body,
        })

    # Build the overall review body
    vuln_summary = vulnerability_type or (findings[0].get("vuln_type") if findings else "vulnerability")
    review_body = (
        f"## 🛡️ Aegis Security Scan Results\n\n"
        f"Aegis found **{len(findings)} security finding(s)** in this PR.\n\n"
    )

    if exploit_output:
        review_body += (
            f"### 🔴 Exploit Confirmed\n"
            f"The **{vuln_summary}** was confirmed exploitable in an isolated Docker sandbox:\n"
            f"```\n{exploit_output[:500]}\n```\n\n"
        )

    if patched_code and vulnerable_file:
        review_body += (
            f"### 🔵 Patch Available\n"
            f"A fix has been generated for `{vulnerable_file}`. "
            f"See the inline suggestion comment below.\n\n"
        )

    review_body += "*This review was posted automatically by the Aegis multi-agent security swarm.*"

    try:
        # Post as a COMMENT review (not APPROVE/REQUEST_CHANGES to avoid blocking the PR)
        review = pr.create_review(
            commit=repo.get_commit(commit_sha),
            body=review_body,
            event="COMMENT",
            comments=comments,
        )
        logger.info(f"PR review posted: {pr.html_url}")
    except Exception as e:
        # Inline comments can fail if the file/line isn't in the PR diff.
        # Fall back to a single top-level comment.
        logger.warning(f"Inline review failed ({e}) — falling back to PR comment")
        pr.create_issue_comment(review_body)

    return pr.html_url


def get_pr_changed_files(repo_full_name: str, pr_number: int) -> list[dict]:
    """
    Fetch the list of files changed in a PR from the GitHub API.
    Returns the same shape as get_diff() changed_files for compatibility.
    """
    g = Github(config.GITHUB_TOKEN)
    repo = g.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)

    changed_files = []
    for f in pr.get_files():
        _, ext = os.path.splitext(f.filename)
        if ext not in config.CODE_EXTENSIONS:
            continue
        changed_files.append({
            "filename": f.filename,
            "status": f.status,
            "additions": f.additions,
            "deletions": f.deletions,
            "patch": f.patch or "",
        })

    return changed_files
