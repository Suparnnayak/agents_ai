"""
Script to create the hospital_forecast database.

Run this before running Alembic migrations.
"""

from sqlalchemy import create_engine, text
import sys

# Connect to default 'postgres' database to create our database
DATABASE_URL = "postgresql://postgres:Suparn%40123@localhost:5432/postgres"

try:
    print("Connecting to PostgreSQL server...")
    engine = create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
    
    with engine.connect() as conn:
        # Check if database exists
        result = conn.execute(text(
            "SELECT 1 FROM pg_database WHERE datname = 'hospital_forecast'"
        ))
        exists = result.fetchone()
        
        if exists:
            print("Database 'hospital_forecast' already exists!")
        else:
            print("Creating database 'hospital_forecast'...")
            conn.execute(text("CREATE DATABASE hospital_forecast"))
            print("Database 'hospital_forecast' created successfully!")
    
    print("\nYou can now run Alembic migrations:")
    print("  alembic revision --autogenerate -m 'Initial migration'")
    print("  alembic upgrade head")
    
except Exception as e:
    print(f"Error: {e}")
    print("\nMake sure:")
    print("  1. PostgreSQL is running")
    print("  2. User 'postgres' has the correct password")
    print("  3. You have permission to create databases")
    sys.exit(1)

