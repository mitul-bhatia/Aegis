#!/usr/bin/env python3
"""
Initialize the Aegis database with all required tables.
This script creates all tables defined in database/models.py.
"""

from database.db import engine, Base
from database.models import User, Repo, Scan, VulnSignature

def init_database():
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
    
    # Verify tables were created
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\nCreated tables: {', '.join(tables)}")

if __name__ == "__main__":
    init_database()
