"""
Script to check database tables.
"""

from sqlalchemy import create_engine, text
import os

DATABASE_URL = "postgresql://postgres:Suparn%40123@localhost:5432/hospital_forecast"

try:
    print("Connecting to database...")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Get list of tables
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """))
        
        tables = [row[0] for row in result]
        
        print(f"\nFound {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")
        
        # Check if expected tables exist
        expected = ['users', 'hospitals', 'admission_history', 'forecast_runs', 'forecasts', 'external_signals', 'alembic_version']
        missing = [t for t in expected if t not in tables]
        
        if missing:
            print(f"\nMissing tables: {missing}")
        else:
            print("\nAll expected tables exist!")
            
except Exception as e:
    print(f"Error: {e}")

