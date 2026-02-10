import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# LEGACY / OPS DB (Where it might be)
# Try OPS_DB_URL first, as that was the default "DATABASE_URL" in monolith
LEGACY_DB_URL = os.getenv("OPS_DB_URL", os.getenv("DATABASE_URL", "sqlite:///./aodev.db"))

def check_legacy_data():
    print(f"🔌 Connecting to Legacy DB: {LEGACY_DB_URL}")
    engine = create_engine(LEGACY_DB_URL)
    
    try:
        with engine.connect() as conn:
            # List all web_ tables
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'web_%';"))
            tables = result.fetchall()
            
            if not tables:
                 print("✅ No 'web_%' tables found.")
            else:
                 for t in tables:
                     t_name = t[0]
                     count = conn.execute(text(f"SELECT COUNT(*) FROM {t_name}")).scalar()
                     print(f"📄 Table '{t_name}': {count} rows")
                     
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_legacy_data()
