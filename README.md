# Aegis

Aegis is an **autonomous white-hat vulnerability remediation system**. It listens for GitHub commits, uses Semgrep to detect potential security vulnerabilities, automatically writes proof-of-concept exploits using Claude to confirm the vulnerabilities, writes patches to fix them, verifies the fixes using isolated Docker containers, and finally opens a Pull Request with the fix and evidence.

## Getting Started
Follow the step-by-step guide in `docs/Phases.md` to build and test this project.

1. **Copy the Environment File:**
   ```bash
   cp .env.example .env
   ```
   Fill in your actual API keys in `.env`.

2. **Install Dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Start the Server:**
   ```bash
   python main.py
   ```
