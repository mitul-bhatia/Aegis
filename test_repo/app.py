import sqlite3

# ⚠️  VULNERABILITY 1: SQL Injection in get_user()
# The problem: we're directly inserting the username into the SQL string.
# A hacker can pass: username = "' OR '1'='1"
# And the query becomes: SELECT * FROM users WHERE username = '' OR '1'='1'
# That '1'='1' is always true, so it returns EVERY user in the database!
def get_user(username):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()

# ⚠️  VULNERABILITY 2: SQL Injection in get_product()
def get_product(product_id):
    conn = sqlite3.connect("products.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM products WHERE id = {product_id}")
    return cursor.fetchone()
