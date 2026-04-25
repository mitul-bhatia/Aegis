"""
Test vulnerable application - SQL Injection example
This is intentionally vulnerable for testing the sandbox.
"""
import sqlite3

def get_user(name):
    """Vulnerable function - uses string concatenation in SQL query"""
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    # VULNERABLE: String concatenation allows SQL injection
    query = f"SELECT * FROM users WHERE name='{name}'"
    cur.execute(query)
    result = cur.fetchone()
    conn.close()
    return result

def setup_database():
    """Create test database with sample data"""
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER, name TEXT, role TEXT)")
    cur.execute("DELETE FROM users")  # Clear existing data
    cur.execute("INSERT INTO users VALUES (1, 'admin', 'administrator')")
    cur.execute("INSERT INTO users VALUES (2, 'alice', 'user')")
    cur.execute("INSERT INTO users VALUES (3, 'bob', 'user')")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    setup_database()
    print("Database initialized")
