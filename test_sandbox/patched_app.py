"""
Patched application - SQL Injection fixed
This demonstrates the fixed version after the Engineer agent patches it.
"""
import sqlite3

def get_user(name):
    """Fixed function - uses parameterized queries"""
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    # FIXED: Use parameterized query to prevent SQL injection
    cur.execute("SELECT * FROM users WHERE name = ?", (name,))
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
