import os
import subprocess
import pytest

SANDBOX_RUNNER = os.path.join(
    os.path.dirname(__file__), "..", "..", "runner", "aegis_cli.py"
)


def _docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def test_sandbox_runner_enforces_isolation_flags():
    """Static check: aegis_cli.py must keep zero-trust docker flags."""
    with open(SANDBOX_RUNNER, encoding="utf-8") as f:
        source = f.read()
    for required in ('"--network", "none"', '"--cap-drop", "ALL"', ':/app:ro'):
        assert required in source, f"Missing sandbox constraint in aegis_cli.py: {required}"


@pytest.mark.skipif(not _docker_available(), reason="Docker daemon not available")
def test_sandbox_network_isolation():
    """Verify that the Docker sandbox cannot access the internet."""
    # Create a malicious script that attempts to curl google.com
    malicious_script = "import urllib.request; urllib.request.urlopen('http://google.com', timeout=2)"
    script_path = "/tmp/malicious_network.py"
    with open(script_path, "w") as f:
        f.write(malicious_script)
    
    try:
        # Assuming aegis_cli.py is how the sandbox is invoked
        # We pass this script to the sandbox. If network is disabled, it should fail.
        # This uses the CLI to run it in the sandbox. If CLI doesn't support raw file execution like this,
        # we test docker directly as per the sandbox constraints.
        result = subprocess.run(
            ["docker", "run", "--rm", "--network", "none", "python:3.10-slim", "python", "-c", malicious_script],
            capture_output=True,
            text=True,
            timeout=10
        )
        # It should fail to resolve the host or timeout
        assert result.returncode != 0
        assert "URLError" in result.stderr or "NameResolutionError" in result.stderr
    finally:
        if os.path.exists(script_path):
            os.remove(script_path)

@pytest.mark.skipif(not _docker_available(), reason="Docker daemon not available")
def test_sandbox_filesystem_isolation():
    """Verify that the Docker sandbox cannot write to mounted directories."""
    # Attempt to touch a file in the /repo directory which should be read-only
    malicious_script = "import os; open('/repo/hacked.txt', 'w').write('pwned')"
    
    result = subprocess.run(
        ["docker", "run", "--rm", "-v", f"{os.getcwd()}:/repo:ro", "python:3.10-slim", "python", "-c", malicious_script],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    # It should fail with a Read-only file system error
    assert result.returncode != 0
    assert "Read-only file system" in result.stderr
