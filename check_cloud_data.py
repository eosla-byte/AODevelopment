from backend.common.database import SessionLocal
from backend.common.models import PluginCloudSession

def check_data():
    db = SessionLocal()
    try:
        count = db.query(PluginCloudSession).count()
        print(f"Total Cloud Sessions: {count}")
        
        if count > 0:
            sessions = db.query(PluginCloudSession).all()
            for s in sessions:
                print(f"- Session: {s.project_name} (User: {s.user_email}, Last Update: {s.timestamp})")
    finally:
        db.close()

if __name__ == "__main__":
    check_data()
