
import sys
import os
import uuid

# Add parent directory to path to allow importing backend modules
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../"))

from backend.common.database import SessionLocal
from backend.common.models import AppUser, AccountUser

def migrate_users():
    db = SessionLocal()
    try:
        legacy_users = db.query(AppUser).all()
        print(f"Found {len(legacy_users)} legacy users.")
        
        migrated_count = 0
        for legacy in legacy_users:
            # Check if exists in new system
            exists = db.query(AccountUser).filter(AccountUser.email == legacy.email).first()
            if exists:
                print(f"Skipping {legacy.email} (already exists)")
                continue
            
            # Create new user
            new_user = AccountUser(
                id=str(uuid.uuid4()),
                email=legacy.email,
                hashed_password=legacy.hashed_password,
                full_name=legacy.full_name,
                role=legacy.role if legacy.role in ["Admin", "Member"] else "Member",
                status="Active" if legacy.is_active else "Inactive",
                company="AO Development", # Default
                # Grant access to AOdev by default for migrated users
                services_access={
                    "AOdev": True,
                    "AO HR & Finance": (legacy.role == "Admin"),
                    "AO Projects": True,
                    "AO Clients": True,
                    "AODailyWork": True,
                    "AOPlanSystem": True,
                    "AOBuild": True
                }
            )
            db.add(new_user)
            print(f"Migrating {legacy.email}...")
            migrated_count += 1
            
        db.commit()
        print(f"Migration complete. Migrated {migrated_count} new users.")
        
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_users()
