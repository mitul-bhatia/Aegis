#!/bin/bash
set -e

echo "=== Pushing Vulnerable Code to Test Repo ==="
echo ""

# Configuration
REPO_URL="https://github.com/mitu1046/aegis-test-repo.git"
TEMP_DIR="/tmp/aegis-test-push-$$"
GITHUB_TOKEN="${GITHUB_TOKEN}"

if [ -z "$GITHUB_TOKEN" ]; then
    echo "ERROR: GITHUB_TOKEN environment variable not set"
    echo "Please set it with: export GITHUB_TOKEN=your_token"
    exit 1
fi

# Clone the repo
echo "1. Cloning repository..."
git clone "https://${GITHUB_TOKEN}@github.com/mitu1046/aegis-test-repo.git" "$TEMP_DIR"
cd "$TEMP_DIR"

# Create vulnerable Python file
echo "2. Creating vulnerable app.py..."
cat > app.py << 'EOF'
#!/usr/bin/env python3
"""
Vulnerable Flask application with SQL injection
"""

import sqlite3
from flask import Flask, request

app = Flask(__name__)

@app.route('/user')
def get_user():
    """VULNERABLE: SQL Injection"""
    user_id = request.args.get('id', '')
    
    # VULNERABILITY: Direct string concatenation in SQL query
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id = {user_id}"  # SQL Injection here!
    cursor.execute(query)
    result = cursor.fetchone()
    conn.close()
    
    return {"user": result}

@app.route('/search')
def search():
    """VULNERABLE: SQL Injection in LIKE clause"""
    term = request.args.get('q', '')
    
    # VULNERABILITY: Unsanitized input in LIKE clause
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE name LIKE '%" + term + "%'"  # SQL Injection!
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    
    return {"results": results}

if __name__ == '__main__':
    app.run(debug=True)
EOF

# Commit and push
echo "3. Committing changes..."
git config user.name "Aegis Test"
git config user.email "test@aegis.local"
git add app.py
git commit -m "Add vulnerable SQL injection code for testing"

echo "4. Pushing to GitHub..."
git push origin main

# Get the commit SHA
COMMIT_SHA=$(git rev-parse HEAD)
echo ""
echo "=== Push Complete ==="
echo "Commit SHA: $COMMIT_SHA"
echo "Repository: mitu1046/aegis-test-repo"
echo ""
echo "The webhook should trigger automatically."
echo "Check the dashboard at: http://localhost:3000/dashboard"
echo ""

# Cleanup
cd /
rm -rf "$TEMP_DIR"

echo "Done!"
