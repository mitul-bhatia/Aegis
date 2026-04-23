"""
Vulnerable Command Injection Example
This file contains a command injection vulnerability for testing Aegis
"""
import subprocess
import os

def ping_host(hostname):
    """
    Ping a hostname
    VULNERABLE: Unsanitized user input in subprocess
    """
    # VULNERABLE: Direct command execution with user input
    command = f"ping -c 1 {hostname}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout

def list_directory(path):
    """
    List files in a directory
    VULNERABLE: Unsanitized path in os.system
    """
    # VULNERABLE: os.system with user input
    os.system(f"ls -la {path}")

def run_command(cmd):
    """
    Run arbitrary command
    VULNERABLE: Direct command execution
    """
    # VULNERABLE: No input validation
    return subprocess.check_output(cmd, shell=True, text=True)

if __name__ == "__main__":
    # Test the functions
    print(ping_host("localhost"))
    list_directory("/tmp")
