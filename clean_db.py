import sqlite3
conn = sqlite3.connect('aegis.db')
c = conn.cursor()
c.execute("DELETE FROM repos;")
conn.commit()
conn.close()
print("Repos cleaned")
