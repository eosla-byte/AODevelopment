
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath("backend"))

from common.database import SessionCore
from common.models import AccountUser, OrganizationUser, ServicePermission, Organization

def debug_perms():
    db = SessionCore()
    try:
        email = "eosla@somosao.com"
        user = db.query(AccountUser).filter(AccountUser.email == email).first()
        
        if not user:
            print("User not found")
            return

        print(f"--- User: {user.email} (ID: {user.id}) ---")
        print(f"User Global Service Access: {user.services_access}")
        
        memberships = db.query(OrganizationUser).filter(OrganizationUser.user_id == user.id).all()
        
        for m in memberships:
            org = db.query(Organization).get(m.organization_id)
            print(f"\n[Organization: {org.name} (ID: {org.id})]")
            print(f"  User Role: {m.role}")
            print(f"  User Org Permissions (JSON): {m.permissions}")
            
            # List all active services for this org
            services = db.query(ServicePermission).filter(
                ServicePermission.organization_id == org.id,
                ServicePermission.is_active == True
            ).all()
            
            print("  Active Service Permissions (Slugs):")
            for s in services:
                print(f"    - '{s.service_slug}'")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_perms()
