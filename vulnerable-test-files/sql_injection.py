"""
Vulnerable SQL Injection Example
This file contains a SQL injection vulnerability for testing Aegis
"""
import sqlite3

def get_user(username):
    """
    Fetch user by username
    VULNERABLE: String concatenation in SQL query
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # VULNERABLE: Direct string concatenation
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    
    result = cursor.fetchone()
    conn.close()
    return result

def search_users(search_term):
    """
    Search users by name
    VULNERABLE: String formatting in SQL query
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # VULNERABLE: String formatting
    query = "SELECT * FROM users WHERE name LIKE '%" + search_term + "%'"
    cursor.execute(query)
    
    results = cursor.fetchall()
    conn.close()
    return results

if __name__ == "__main__":
    # Test the functions
    print(get_user("admin"))
    print(search_users("john"))
