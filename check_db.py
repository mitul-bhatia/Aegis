from database.db import SessionLocal
from database.models import User

db = SessionLocal()
try:
    users = db.query(User).all()
    print(f"Total users: {len(users)}")
    for u in users:
        print(f"User {u.id}: {u.github_username}, Installation ID: {u.github_installation_id}")
finally:
    db.close()
