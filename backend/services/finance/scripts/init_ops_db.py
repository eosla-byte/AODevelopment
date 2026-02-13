
import sys
import os
# Add parent dir to sys.path to resolve 'common'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.database import engine_ops, Base
from common import models

def init_ops_db():
    print("Creating tables in Operations DB (postgres-x8en)...")
    try:
        # Create all tables defined in models.Base metadata using the Operations engine
        Base.metadata.create_all(bind=engine_ops)
        print("✅ Tables created successfully in Operations DB.")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")

if __name__ == "__main__":
    init_ops_db()
