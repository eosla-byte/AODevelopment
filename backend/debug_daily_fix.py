import sys
import os
import datetime
from sqlalchemy import create_engine, text, inspect

# Add path to finding backend modules
sys.path.append(os.path.abspath("a:\\AO_DEVELOPMENT\\AODevelopment\\backend"))

try:
    from services.daily.common import database
    from services.daily.common import models
except ImportError as e:
    print(f"Import Error: {e}")
    # Fallback/Mock if needed
    pass

def check_db():
    print("--- CHECKING DB ---")
    db = database.SessionOps()
    engine = db.get_bind()
    inspector = inspect(engine)
    columns = [c['name'] for c in inspector.get_columns('daily_comments')]
    print(f"Columns in daily_comments: {columns}")
    
    if 'user_name' in columns:
        print("✅ Column 'user_name' EXISTS.")
    else:
        print("❌ Column 'user_name' MISSING.")

    # Check recent comments
    print("\n--- RECENT COMMENTS ---")
    try:
        # Raw SQL to avoiding model caching/mismatch if python model is old in memory
        result = db.execute(text("SELECT id, user_id, user_name, created_at FROM daily_comments ORDER BY id DESC LIMIT 5"))
        for row in result:
            print(f"ID: {row.id}, UID: {row.user_id}, Name: {row.user_name}, Time: {row.created_at} (Type: {type(row.created_at)})")
    except Exception as e:
        print(f"Error querying comments: {e}")
    
    db.close()

def check_time():
    print("\n--- CHECKING TIME ---")
    gt_tz = datetime.timezone(datetime.timedelta(hours=-6))
    now_gt = datetime.datetime.now(gt_tz)
    print(f"Generated Now (GT): {now_gt}")
    print(f"Formatted: {now_gt.strftime('%b %d, %I:%M %p')}")
    
    # Simulate DB roundtrip (Naive UTC)
    # If DB stored '2026-02-10 03:53:00' (Naive)
    # And we treat as UTC:
    naive_metric = now_gt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    print(f"Simulated DB Value (Naive UTC): {naive_metric}")
    
    # Restore logic
    restored = naive_metric.replace(tzinfo=datetime.timezone.utc).astimezone(gt_tz)
    print(f"Restored Logic: {restored}")
    print(f"Restored Formatted: {restored.strftime('%b %d, %I:%M %p')}")

if __name__ == "__main__":
    check_db()
    check_time()
