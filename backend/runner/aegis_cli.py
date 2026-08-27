#!/usr/bin/env python3
"""
Aegis CLI — Local DevOps Sandbox Runner
Safely executes and verifies security exploits inside an isolated Docker Desktop container.

Usage:
  python runner/aegis_cli.py verify <scan_id> [--api-url http://localhost:8000]
  python runner/aegis_cli.py test-local <exploit_file.py> <target_repo_dir>
"""

import sys
import os
import argparse
import subprocess
import tempfile
import requests

BANNER = r"""
    ___    ______ _____ _____ _____ 
   /   |  / ____// ___// ___// ___/ 
  / /| | / __/  / / _  \__ \ \__ \  
 / ___ |/ /___ / /_/ / ___/ /___/ / 
/_/  |_/_____/ \____/ /____//____/  
   >> LOCAL DOCKER SANDBOX RUNNER <<
"""


def check_docker_running() -> bool:
    """Verify Docker Desktop daemon is running on the host machine."""
    try:
        res = subprocess.run(["docker", "info"], capture_output=True, text=True, check=False)
        return res.returncode == 0
    except FileNotFoundError:
        return False


def run_in_docker_sandbox(script_content: str, target_dir: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """
    Launch ephemeral Docker container with zero-trust isolation:
    - --network none (no outbound internet egress)
    - --cap-drop ALL (no Linux root capabilities)
    - --memory 512m (RAM quota)
    - --cpus 1.0 (CPU quota)
    - -v target_dir:/app:ro (read-only target codebase mount)
    """
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(script_content)
        temp_script = f.name

    docker_cmd = [
        "docker", "run", "--rm",
        "--name", f"aegis-sandbox-{os.getpid()}",
        "--network", "none",
        "--cap-drop", "ALL",
        "--memory", "512m",
        "--cpus", "1.0",
        "--user", "10001:10001",
        "--tmpfs", "/tmp",
        "-v", f"{os.path.abspath(target_dir)}:/app:ro",
        "-v", f"{temp_script}:/workspace/exploit.py:ro",
        "python:3.11-slim",
        "python", "/workspace/exploit.py"
    ]

    try:
        print("\n[+] Launching isolated container with parameters:")
        print("    • Network: NONE (No egress)")
        print("    • Capabilities: ALL DROPPED")
        print("    • Memory Cap: 512MB")
        print("    • Mount: /app [READ-ONLY]")
        print("    • Scratch Space: /tmp [TMPFS]")
        print("    • Execution User: sandboxuser (UID 10001)\n")
        
        result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=timeout)
        return result
    finally:
        if os.path.exists(temp_script):
            os.remove(temp_script)


def verify_scan(scan_id: int, api_url: str):
    print(BANNER)
    print(f"[*] Fetching scan details for Scan #{scan_id} from {api_url}...")

    api_key = os.getenv("CLI_API_KEY", "aegis-cli-dev-key-123")
    headers = {"X-Aegis-CLI-Key": api_key}
    
    try:
        resp = requests.get(f"{api_url}/api/v1/scans/{scan_id}", headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"[!] Error: Could not find Scan #{scan_id} (HTTP {resp.status_code})")
            return
        scan = resp.json()
    except Exception as e:
        print(f"[!] Failed to connect to Aegis API: {e}")
        return

    print(f"[+] Scan Found: {scan.get('vulnerability_type', 'Vulnerability')} in {scan.get('vulnerable_file', 'unknown')}")
    print(f"[+] Severity: {scan.get('severity', 'UNKNOWN')}")
    
    if not check_docker_running():
        print("[!] Docker Desktop daemon is not running. Please start Docker Desktop and retry.")
        return

    # Real exploit verification script from LLM
    exploit_script = scan.get("exploit_script")
    if not exploit_script:
        print("[!] Error: No exploit script generated for this scan yet.")
        print("[!] The Engineer agent must generate a reproduction script before verification.")
        return

    print("[*] Executing Proof-of-Concept Exploit in Local Docker Sandbox...")
    res = run_in_docker_sandbox(exploit_script, target_dir=".")

    print("\n--- CONTAINER OUTPUT ---")
    if res.stdout:
        print(res.stdout)
    if res.stderr:
        print(res.stderr)
    print("------------------------\n")

    if res.returncode == 0 and "VERIFICATION CONFIRMED" in res.stdout:
        print("[✔] VERIFICATION SUCCESS: Exploit confirmed inside isolated container!")
        print("[✔] No false positive. This issue is ready for autonomous patch generation by Engineer Agent.\n")
    else:
        print("[?] Exploit script execution completed but verification condition failed.")
        print("[?] Expected 'VERIFICATION CONFIRMED' in stdout or exit code 0.")


def main():
    parser = argparse.ArgumentParser(description="Aegis CLI — Local Docker Sandbox Runner")
    subparsers = parser.add_subparsers(dest="command")

    verify_parser = subparsers.add_parser("verify", help="Verify a scan finding locally using Docker")
    verify_parser.add_argument("scan_id", type=int, help="ID of the scan to verify")
    verify_parser.add_argument("--api-url", default="http://localhost:8000", help="Aegis API base URL")

    args = parser.parse_args()

    if args.command == "verify":
        verify_scan(args.scan_id, args.api_url)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
